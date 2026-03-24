from unittest.mock import patch

import pytest

from img2catalog.inputs.xnat import split_keywords, check_optin_optout


@pytest.mark.parametrize(
    "test_str, expected",
    [
        # Various type of whitespace and variations
        ("", []),
        ("        ", []),
        (" .  , ;  .. .,;:", []),
        # Keywords with different amounts of space inbetween
        ("xnat python", ["xnat", "python"]),
        ("  xnat      python ", ["xnat", "python"]),
        # Below is real example. The official XNAT specification is not followed by the writer
        ("artificial intelligence, radiomics", ["artificial", "intelligence", "radiomics"]),
        # Some random punctuations and stuff
        ("artificial;intelligence.   radiomics", ["artificial", "intelligence", "radiomics"]),
        ("artificial ; intelligence.,.,.,radiomics", ["artificial", "intelligence", "radiomics"]),
    ],
)
def test_keyword_splitter(test_str, expected):
    output_list = split_keywords(test_str)

    # We compare it as a set as we do not care about the order (the RDF serializer mangles it anyways)
    assert set(expected) == set(output_list)


@patch("xnat.core.XNATBaseObject")
def test_no_optin_optout(project):
    project.keywords = "test demo optout_keyword"
    config = {"img2catalog": {}}

    # First test no config
    assert check_optin_optout(project, config)


@patch("xnat.core.XNATBaseObject")
def test_optout(project):
    # project without keywords
    config = {"img2catalog": {"optout": "optout_keyword"}}
    assert check_optin_optout(project, config)

    project.keywords = "test demo optout_keyword"
    assert not check_optin_optout(project, config)


@patch("xnat.core.XNATBaseObject")
def test_optin(project):
    config = {"img2catalog": {"optin": "optin_keyword"}}
    project.keywords = "test demo optin_keyword"

    assert check_optin_optout(project, config)

    project.keywords = "test demo"
    assert not check_optin_optout(project, config)


@patch("xnat.core.XNATBaseObject")
def test_optin_noconfig(project):
    config = {}
    project.keywords = "test demo"

    assert check_optin_optout(project, config)
