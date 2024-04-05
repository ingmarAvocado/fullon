"""
The idea of the module is to read from a .conf file and load them into
global variables accesible by all programs.
"""
from libs.settings_config import settings_loader
settings = settings_loader.SettingsLoader()
settings.load_conf_file(filename='fullon.conf')
settings.get_all_settings()
settings.add_encrypted_settings()
del settings
