"""
The idea of the module is to read from a .conf file and load them into
global variables accesible by all programs.
"""
import sys
from os import getenv, path, makedirs
import configparser
import logging
from shutil import copy2
from munch import DefaultMunch
from libs import settings, secret

logger = logging.getLogger(__name__)


class SettingsLoader():
    """
    main class for settings module
    """
    config: configparser.ConfigParser

    def load_conf_file(self, filename: str = "fullon.conf"):
        """
        loads conf file from one of three locations
        """
        config = configparser.ConfigParser()
        file_locations = [
            f"/etc/fullon/{filename}",
            f"conf/{filename}",
            f"fullon/conf/{filename}"
        ]
        for file_location in file_locations:
            try:
                with open(file_location, encoding='ascii') as fileo:
                    contents = fileo.read()
                config.read_string(contents)
                logger.info("loading settings from %s", file_location)
                break
            except FileNotFoundError:
                pass
        else:
            logger.error("No fullon.conf file found in /etc/fullon/, conf/, or fullon/conf/")
            answer = input(f"Do you want me to create a basic structure in conf/ (YES/NO)\n")
            if answer.upper() == "YES":
                self.create_etc_conf()
                sys.exit()
            logger.info("Please fix your configuration files")
            sys.exit()
        self.config = config

    def create_etc_conf(self):
        """ auto magically creates an /etc/fullon, usefull for deployments"""
        folder = getenv("HOME")+"/fullon_conf/"
        if not path.exists(folder):
            makedirs(folder)
        copy2('conf/fullon.conf', folder)
        copy2('conf/fullon_ctl.conf', folder)
        print("Please attempt to start fullon again")

    def get_all_settings(self):
        """
        Gets all settings into a single object.
        """
        for section in self.config.sections():
            for key, value in self.config.items(section):
                try:
                    setattr(settings, str(key).upper(), int(value))
                except ValueError:
                    try:
                        setattr(settings, str(key).upper(), float(value))
                    except ValueError:
                        try:
                            if value.lower() == "none":
                                value = None
                            if value.lower() == "false":
                                value = False
                            if value.lower() == "true":
                                value = True
                            setattr(settings, str(key).upper(), str(value))
                        except AttributeError:
                            setattr(settings, str(key).upper(), value)

    def get_section(self, section: str, filename: str = 'fullon_ctl.conf') -> DefaultMunch:
        """ gets only one section from the config file and returns as munch"""
        self.load_conf_file(filename=filename)
        if section in self.config.sections():
            setts = {}
            for key, value in self.config.items(section):
                try:
                    setts.update({str(key).upper(): int(value)})
                except ValueError:
                    try:
                        setts.update({str(key).upper(): float(value)})
                    except ValueError:
                        try:
                            if value.lower() == "none":
                                value = None
                            if value.lower() == "false":
                                value = False
                            if value.lower() == "true":
                                value = True
                            setts.update({str(key).upper(): str(value)})
                        except AttributeError:
                            setts.update({str(key).upper(): value})
        return DefaultMunch.fromDict(setts)

    def add_encrypted_settings(self):
        """comments"""
        hush = secret.SecretManager()
        if hush.secrets:
            setattr(settings, "GOOGLE_CREDENTIALS", hush.credentials)
            for key in hush.secrets:
                name = "".join(key.name.split("/")[-1:])
                payload = hush.access_secret_version(secret_id=name)
                setattr(settings, str(name).upper(), str(payload))
