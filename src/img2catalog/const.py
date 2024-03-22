"""This file contains constants used by img2catalog"""

from pathlib import Path

from rdflib import Namespace

CONFIG_HOME_PATH = Path.home() / ".img2catalog" / "config.toml"

XNAT_HOST_ENV = "XNAT_HOST"
XNATPY_HOST_ENV = "XNATPY_HOST"
XNAT_USER_ENV = "XNAT_USER"
XNAT_PASS_ENV = "XNAT_PASS"

FDP_SERVER_ENV = "IMG2CATALOG_FDP"
FDP_USER_ENV = "IMG2CATALOG_FDP_USER"
FDP_PASS_ENV = "IMG2CATALOG_FDP_PASS"

VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
