import pandas as pd
import pytest

from img2catalog.inputs.csv_reader import filter_by_unique_individuals, read_csv


def test_read_csv_returns_dataframe_on_success(xds_csv_example):
    # Arrange
    expected_columns = 8
    expected_rows = 4

    # Act
    result = read_csv(xds_csv_example)

    # Assert
    assert not result.empty
    assert len(result) == expected_rows
    assert len(result.columns) == expected_columns


def test_read_csv_returns_empty_dataframe_on_error():
    # Arrange
    invalid_path = "non_existent_file.csv"

    # Act
    result = read_csv(invalid_path)

    # Assert
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_filter_by_unique_individuals_drops_rows_below_threshold(xds_csv_example):
    # Arrange
    df = read_csv(xds_csv_example)
    config = {"xds": {"minimum_unique_individuals": 5000}}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert len(result) == 3
    assert (pd.to_numeric(result["numberOfUniqueIndividuals"]) >= 5000).all()


def test_filter_by_unique_individuals_keeps_rows_equal_to_threshold(xds_csv_example):
    # Arrange
    df = read_csv(xds_csv_example)
    config = {"xds": {"minimum_unique_individuals": 5041}}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert "5041" in result["numberOfUniqueIndividuals"].values


def test_filter_by_unique_individuals_keeps_all_when_key_missing(xds_csv_example):
    # Arrange
    df = read_csv(xds_csv_example)
    config = {"xds": {}}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert len(result) == len(df)


def test_filter_by_unique_individuals_keeps_all_when_section_missing(xds_csv_example):
    # Arrange
    df = read_csv(xds_csv_example)
    config = {}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert len(result) == len(df)


def test_filter_by_unique_individuals_returns_empty_dataframe_unchanged():
    # Arrange
    df = pd.DataFrame()
    config = {"xds": {"minimum_unique_individuals": 5000}}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert result.empty


def test_filter_by_unique_individuals_falls_back_to_default_on_invalid_config(xds_csv_example, caplog):
    # Arrange
    df = read_csv(xds_csv_example)
    config = {"xds": {"minimum_unique_individuals": "not-a-number"}}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert len(result) == len(df)
    assert "falling back to default" in caplog.text


def test_filter_by_unique_individuals_raises_on_non_numeric_row_value(xds_csv_example):
    # Arrange
    df = read_csv(xds_csv_example)
    df["numberOfUniqueIndividuals"] = df["numberOfUniqueIndividuals"].astype(object)
    df.loc[0, "numberOfUniqueIndividuals"] = "not-a-number"
    config = {"xds": {"minimum_unique_individuals": 5000}}

    # Act & Assert
    with pytest.raises(ValueError, match="non-numeric value"):
        filter_by_unique_individuals(df, config)


def test_read_csv_keeps_the_text_of_cells(tmp_path):
    # Arrange
    csv_path = tmp_path / "text.csv"
    csv_path.write_text("id,remark,empty\n007,NA,\n1.50,null,x\n")

    # Act
    result = read_csv(csv_path)

    # Assert
    assert result["id"].tolist() == ["007", "1.50"]
    assert result["remark"].tolist() == ["NA", "null"]
    assert result["empty"].tolist() == ["", "x"]


def test_filter_by_unique_individuals_uses_the_column_mapped_to_the_property():
    # Arrange
    df = pd.DataFrame({"Persons": ["20", "5"], "numberOfUniqueIndividuals": ["1", "100"]})
    config = {"xds": {"minimum_unique_individuals": 10, "column_mapping": {"Persons": "number_of_unique_individuals"}}}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert result["Persons"].tolist() == ["20"]
