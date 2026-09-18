import pandas as pd
from img2catalog.inputs.csv_reader import read_csv, filter_by_unique_individuals

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
    assert (result["numberOfUniqueIndividuals"] >= 5000).all()


def test_filter_by_unique_individuals_keeps_rows_equal_to_threshold(xds_csv_example):
    # Arrange
    df = read_csv(xds_csv_example)
    config = {"xds": {"minimum_unique_individuals": 5041}}

    # Act
    result = filter_by_unique_individuals(df, config)

    # Assert
    assert 5041 in result["numberOfUniqueIndividuals"].values

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