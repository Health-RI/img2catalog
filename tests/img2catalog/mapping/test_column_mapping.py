import pandas as pd
import pytest
from rdflib import URIRef
from sempyro import LiteralField
from sempyro.hri_dcat import DatasetTheme, HRIDataset

from img2catalog.mappings.column_mapping import (
    ColumnMappingError,
    map_columns_to_properties,
    validate_column_mapping,
)

HEAL = "http://publications.europa.eu/resource/authority/data-theme/HEAL"


def test_scalar_property_gets_the_text_of_the_cell():
    row = pd.Series({"Version": " 1.2 "})

    result = map_columns_to_properties(row, {"Version": "version"}, HRIDataset)

    assert result == {"version": "1.2"}


def test_list_property_is_split_on_the_default_separator():
    row = pd.Series({"Keywords": "ct; radiology ;thorax;"})

    result = map_columns_to_properties(row, {"Keywords": "keyword"}, HRIDataset)

    assert result == {"keyword": [LiteralField(value=v) for v in ("ct", "radiology", "thorax")]}


def test_list_property_is_split_on_the_given_separator():
    row = pd.Series({"Keywords": "ct, radiology|thorax"})

    result = map_columns_to_properties(row, {"Keywords": "keyword"}, HRIDataset, list_separator="|")

    assert result == {"keyword": [LiteralField(value="ct, radiology"), LiteralField(value="thorax")]}


def test_single_value_in_list_property_becomes_a_list():
    row = pd.Series({"Page": "https://example.com/page"})

    result = map_columns_to_properties(row, {"Page": "landing_page"}, HRIDataset)

    assert result == {"landing_page": ["https://example.com/page"]}


def test_vocabulary_values_are_looked_up():
    row = pd.Series({"Theme": f"{HEAL};{HEAL}"})

    result = map_columns_to_properties(row, {"Theme": "theme"}, HRIDataset)

    assert result["theme"] == [DatasetTheme(URIRef(HEAL)), DatasetTheme(URIRef(HEAL))]


def test_value_outside_vocabulary_is_refused_with_column_and_property():
    row = pd.Series({"Theme": "http://example.com/not-a-theme"})

    expected = r"Column 'Theme' \(property 'theme'\): 'http://example.com/not-a-theme' is not one of"
    with pytest.raises(ValueError, match=expected):
        map_columns_to_properties(row, {"Theme": "theme"}, HRIDataset)


def test_absent_and_empty_cells_are_left_out():
    row = pd.Series({"Empty": "", "Blank": "  ", "Missing": float("nan"), "Filled": "x"})
    mapping = {
        "Empty": "version",
        "Blank": "population_coverage",
        "Missing": "temporal_resolution",
        "Absent": "license",
        "Filled": "rights",
    }

    result = map_columns_to_properties(row, mapping, HRIDataset)

    assert result == {"rights": LiteralField(value="x")}


def test_validate_accepts_scalar_list_and_vocabulary_properties():
    validate_column_mapping({"a": "version", "b": "keyword", "c": "theme", "d": "identifier"}, HRIDataset)


def test_validate_refuses_unknown_property_and_lists_the_properties():
    with pytest.raises(ColumnMappingError, match=r"'Column A' is mapped to 'descriptoin'.*description") as error:
        validate_column_mapping({"Column A": "descriptoin"}, HRIDataset)

    assert "keyword" in str(error.value)


def test_validate_refuses_property_that_consists_of_other_properties():
    with pytest.raises(ColumnMappingError, match="cannot be filled from one column"):
        validate_column_mapping({"Retention": "retention_period"}, HRIDataset)


def test_validate_refuses_two_columns_for_one_property():
    with pytest.raises(ColumnMappingError, match="'First' and 'Second' are both mapped to 'description'"):
        validate_column_mapping({"First": "description", "Second": "description"}, HRIDataset)


def test_validate_accepts_empty_mapping():
    validate_column_mapping({}, HRIDataset)


def test_property_with_literal_or_url_gets_a_literal_for_text():
    row = pd.Series({"Rights": "Research use only"})

    result = map_columns_to_properties(row, {"Rights": "rights"}, HRIDataset)

    assert result == {"rights": LiteralField(value="Research use only")}


def test_property_with_literal_or_url_keeps_a_url_as_a_url():
    row = pd.Series({"Rights": "https://example.com/license"})

    result = map_columns_to_properties(row, {"Rights": "rights"}, HRIDataset)

    assert result == {"rights": "https://example.com/license"}


def test_property_with_number_or_literal_still_refuses_text():
    """A number property must not take any text as a literal."""
    row = pd.Series({"Records": "many"})

    result = map_columns_to_properties(row, {"Records": "number_of_records"}, HRIDataset)

    assert result == {"number_of_records": "many"}  # refused by the dataset, which names the line (see test_xds)
