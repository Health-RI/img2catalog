"""This file contains constants used by img2catalog"""

from pathlib import Path

CONFIG_HOME_PATH = Path.home() / ".img2catalog" / "config.toml"

XNAT_HOST_ENV = "XNAT_HOST"
XNATPY_HOST_ENV = "XNATPY_HOST"
XNAT_USER_ENV = "XNAT_USER"
XNAT_PASS_ENV = "XNAT_PASS"

FDP_SERVER_ENV = "IMG2CATALOG_FDP"
FDP_USER_ENV = "IMG2CATALOG_FDP_USER"
FDP_PASS_ENV = "IMG2CATALOG_FDP_PASS"

SPARQL_ENV = "IMG2CATALOG_SPARQL_ENDPOINT"

# Default setting
REMOVE_OPTIN_KEYWORD = True
