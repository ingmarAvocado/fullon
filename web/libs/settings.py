"""
description
"""
import sys
from os import path, getcwd
import configparser

import configparser

section_list = [
    'logger',
    'postgresql',
    'redis',
    'xmlserver']

cwd = getcwd()

config = configparser.ConfigParser()
if path.exists("/etc/fullon/fullon.conf"):
    settings = config.read('/etc/fullon/fullon.conf')
elif path.exists("conf/fullon.conf"):
    settings = config.read('conf/fullon.conf')
else:
    sys.exit(
        f"settings._load_1: No configuration file found in \
        /etc/fullon/fullon.conf or {cwd}/conf/fullon.conf")
if len(settings) == 0:
    sys.exit(
        f"settings._load_2: No configuration file found in \
        /etc/fullon/fullon.conf or {cwd}/conf/fullon.conf")
sections = config.sections()
for section in sections:
    if section in section_list:
        section_list.remove(section)
    for key, value in config.items(section):
        try:
            globals()[f"{str(key).upper()}"] = int(value)
        except ValueError:
            try:
                globals()[f"{str(key).upper()}"] = float(value)
            except ValueError:
                if value == "None":
                    value = ''
                if value == "False":
                    value = 0
                if value == "True":
                    value = 1
                globals()[f"{str(key).upper()}"] = value
if len(section_list) != 0:
    sys.exit(
        f"_load: Configuration file missing or not complete {section_list}")
del config
del section_list
del cwd
del sections
