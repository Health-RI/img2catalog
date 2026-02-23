import pathlib
import sys

import pytest
from rdflib import Graph, DCAT, DCTERMS
from sempyro.dcat.dcat_catalog import DCATCatalog
from sempyro.dcat.dcat_dataset import DCATDataset
from sempyro.vcard import VCARD

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


TEST_CONFIG = pathlib.Path(__file__).parent / "example-config.toml"
pytest_plugins = "tests.xnatpy_fixtures"


@pytest.fixture()
def config():
    """Loads the default configuration TOML"""
    config_path = TEST_CONFIG

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    return config


@pytest.fixture()
def mock_catalog():
    catalog = DCATCatalog(title=["Example XNAT catalog"], description=["This is an example XNAT catalog description"])
    return catalog


@pytest.fixture()
def mock_dataset():
    dataset = DCATDataset(title=["test project"], description=["test description"])
    return dataset


@pytest.fixture()
def empty_graph():
    graph = Graph()
    graph.bind("dcat", DCAT)
    graph.bind("dcterms", DCTERMS)
    graph.bind("v", VCARD)
    return graph


@pytest.fixture()
def second_empty_graph():
    graph = Graph()
    graph.bind("dcat", DCAT)
    graph.bind("dcterms", DCTERMS)
    graph.bind("v", VCARD)
    return graph


@pytest.fixture()
def toml_patch_target():
    # Python 3.11 and up has tomllib built-in, for 3.10 and lower we use tomli which provides
    # the same functonality. We check if it's Python 3.10 or lower to patch the correct target.
    if sys.version_info < (3, 11):
        return "tomli.load"
    else:
        return "tomllib.load"


def pytest_addoption(parser):
    parser.addoption(
        "--runint", action="store_true", default=False, help="Run integration tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "int: Mark tests as integration tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runint"):
        # --runint given in cli: do not skip integration tests
        return
    skip_int = pytest.mark.skip(reason="Integration test: needs --runint option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_int)
