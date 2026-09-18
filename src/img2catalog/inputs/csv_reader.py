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
    minimum = config.get("xds", {}).get("minimum_unique_individuals", XDS_MIN_UNIQUE_INDIVIDUALS_DEFAULT)

    filtered_df = df[df["numberOfUniqueIndividuals"].astype(int) >= int(minimum)]

    logger.info(
        "Filtered out %d of %d dataset(s) with fewer than %s unique individuals",
        len(df) - len(filtered_df), len(df), minimum,
    )

    return filtered_df
