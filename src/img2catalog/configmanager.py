import logging
from pathlib import Path
from typing import Dict

# Python < 3.11 does not have tomllib, but tomli provides same functionality
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from img2catalog.const import CONFIG_HOME_PATH

logger = logging.getLogger(__name__)


def example_standard_config() -> str:
    """This function returns a serialized version of the example configuration file.

    While not the cleanest solution, it does allow for easy packaging.
    In the future, this could be replaced by a configuration migration function.

    Returns
    -------
    str
        String of a toml-serialized configuration file.
    """
    standard_config = """[img2catalog]
# optin = "include_catalog"
# optout = "exclude_catalog"

[dataset]
# Theme should be Health, according to the EU Data Theme vocabulary
theme = "http://publications.europa.eu/resource/authority/data-theme/HEAL"
applicable_legislation = ["http://data.europa.eu/eli/reg/2025/327/oj"]
access_rights = "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC"

[dataset.contact_point]
# override = true
formatted_name = "Example Data Management office"
email = "datamanager@example.com"

[dataset.publisher]
name = ["Example publisher list",]
identifier = ["http://example.com"]
mbox = "mailto:publisher@example.com"
homepage = "http://www.example.com"

[dataset.creator]
identifier = ['http://example.com']
mbox = "mailto:example@example.com"
homepage = "http://www.example.com"

[catalog]
title = "Example XNAT catalog"
description = "This is an example XNAT catalog description"

[catalog.publisher]
name = ["Example publishing institution",]
identifier = ["http://www.example.com/institution#example"]
mbox = "mailto:publisher@example.com"
homepage = "http://www.example.com"

[catalog.contact_point]
# override = true
formatted_name = "Example Data Management office"
email = "mailto:datamanager@example.com"

[distribution.default]
title = "XNAT imaging distribution"
description = "Link to XNAT instance where the imaging data can be accessed."
"""
    return standard_config


def load_img2catalog_configuration(config_path: Path = None) -> Dict:
    """Loads a configuration file for img2catalog

    First, it checks if config_path is given. If not, it will look for ~/.img2catalog/config.toml,
    if that file also doesn't exist it will load an example configuration from the project rootfolder.

    Parameters
    ----------
    config_path : Path, optional
        Path to configuration file to load, by default None

    Returns
    -------
    Dict
        Dictionary with loaded configuration properties

    Raises
    ------
    FileNotFoundError
        If config_path is specified yet does not exist
    """
    if config_path:
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file does not exist at {config_path}")
    elif (config_path := CONFIG_HOME_PATH).exists():
        pass
    else:
        logger.warning("No configuration file found or specified! Using example configuration")
        config = tomllib.loads(example_standard_config())
        return config

    logger.info("Using configuration file %s", config_path)

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config
