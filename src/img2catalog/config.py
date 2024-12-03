"""This file contains constants used by img2catalog"""

from pathlib import Path
import os

CONFIG_HOME_PATH = Path.home() / ".img2catalog" / "config.toml"

XNAT_HOST = os.getenv("XNAT_HOST")
XNATPY_HOST = os.getenv("XNATPY_HOST")
XNAT_USER = os.getenv("XNAT_USER")
XNAT_PASS = os.getenv("XNAT_PASS")

FDP_SERVER = os.getenv("IMG2CATALOG_FDP")
FDP_USER = os.getenv("IMG2CATALOG_FDP_USER")
FDP_PASS = os.getenv("IMG2CATALOG_FDP_PASS")

SPARQL_ENDPOINT = os.getenv("IMG2CATALOG_SPARQL_ENDPOINT")