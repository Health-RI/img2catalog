import logging
from typing import Dict

import pandas as pd
from pandas import DataFrame

from img2catalog.const import XDS_MIN_UNIQUE_INDIVIDUALS_DEFAULT

logger = logging.getLogger(__name__)


def read_csv(csv_path: str) -> DataFrame:
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        print(f"error reading .csv file: {e}")
        return pd.DataFrame()


def filter_by_unique_individuals(df: DataFrame, config: Dict) -> DataFrame:
    """Filter out dataset rows with too few unique individuals.

    The minimum is read from the `[xds] minimum_unique_individuals` configuration
    key. If not configured, no rows are filtered out.

    Parameters
    ----------
    df : DataFrame
        Dataframe of XDS dataset rows, must contain a "numberOfUniqueIndividuals" column.
    config : Dict
        Configuration dictionary, may contain an `xds.minimum_unique_individuals` key.

    Returns
    -------
    DataFrame
        Dataframe containing only rows that meet the configured minimum.
    """
    if df.empty or "numberOfUniqueIndividuals" not in df.columns:
        return df

    minimum = config.get("xds", {}).get("minimum_unique_individuals", XDS_MIN_UNIQUE_INDIVIDUALS_DEFAULT)
    numeric_minimum = pd.to_numeric(minimum, errors="coerce")
    if pd.isna(numeric_minimum):
        logger.warning(
            "Configured xds.minimum_unique_individuals %r is not numeric, falling back to default %s",
            minimum,
            XDS_MIN_UNIQUE_INDIVIDUALS_DEFAULT,
        )
        numeric_minimum = XDS_MIN_UNIQUE_INDIVIDUALS_DEFAULT

    unique_individuals = pd.to_numeric(df["numberOfUniqueIndividuals"], errors="coerce")
    invalid_rows = df.loc[unique_individuals.isna(), "numberOfUniqueIndividuals"]
    if not invalid_rows.empty:
        raise ValueError(
            f"Column 'numberOfUniqueIndividuals' contains non-numeric value(s) at row(s) "
            f"{invalid_rows.index.tolist()}: {invalid_rows.tolist()}"
        )

    filtered_df = df[unique_individuals >= numeric_minimum]

    logger.info(
        "Filtered out %d of %d dataset(s) with fewer than %s unique individuals",
        len(df) - len(filtered_df), len(df), numeric_minimum,
    )

    return filtered_df
