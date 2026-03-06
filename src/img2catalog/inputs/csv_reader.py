import pandas as pd
from pandas import DataFrame


def read_csv(csv_path: str) -> DataFrame:
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        print(f"error reading .csv file: {e}")
        return pd.DataFrame()
