import pandas as pd
from img2catalog.inputs.csv_reader import read_csv

def test_read_csv_returns_dataframe_on_success():
    # Arrange
    filepath = "../examples/xds_input.csv"
    expected_columns = 8
    expected_rows = 4

    # Act
    result = read_csv(filepath)

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