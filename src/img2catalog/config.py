"""This file contains constants used by img2catalog"""

from pathlib import Path
import os

CONFIG_HOME_PATH = Path.home() / ".img2catalog" / "config.toml"

XNAT_HOST_ENV = os.getenv("XNAT_HOST")
XNATPY_HOST_ENV = os.getenv("XNATPY_HOST")
XNAT_USER_ENV = os.getenv("XNAT_USER")
XNAT_PASS_ENV = os.getenv("XNAT_PASS")

FDP_SERVER_ENV = os.getenv("IMG2CATALOG_FDP")
FDP_USER_ENV = os.getenv("IMG2CATALOG_FDP_USER")
FDP_PASS_ENV = os.getenv("IMG2CATALOG_FDP_PASS")

SPARQL_ENV = os.getenv("IMG2CATALOG_SPARQL_ENDPOINT")
