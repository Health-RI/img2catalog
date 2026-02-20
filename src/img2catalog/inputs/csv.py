import pandas as pd
from pandas.core.interchange.dataframe_protocol import DataFrame

def read_csv(csv_path: str) -> DataFrame:
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        print(f"error reading .csv file: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    results = read_csv("xds_input.csv")

    if results:
        print(results[0].model_dump_json(indent=2, exclude_none=True))