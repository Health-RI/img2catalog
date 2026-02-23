import pandas as pd
from pandas.core.interchange.dataframe_protocol import DataFrame

def read_csv(csv_path: str) -> DataFrame:
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        print(f"error reading .csv file: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    results = read_csv("../../../examples/xds_input.csv")

    if not results.empty:
        print(results.to_json(orient='records', indent=2))
    else:
        print("No data found or file is empty.")