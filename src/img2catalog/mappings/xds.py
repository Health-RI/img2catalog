from datetime import datetime
from pathlib import Path
from typing import Dict

from sempyro.time import PeriodOfTime

from img2catalog.configmanager import load_img2catalog_configuration
from pandas import Series
from rdflib import URIRef
from sempyro.hri_dcat import HRIAgent, HRIVCard, HRIDataset

from img2catalog.inputs.csv_reader import read_csv

def format_temporal_coverage(temporal_coverage: str) -> PeriodOfTime:
    """Format 'DD-MM-YYYY to DD-MM-YYYY' into a PeriodOfTime object."""
    start_str, end_str = temporal_coverage.split("to")

    date_fmt = "%d-%m-%Y"
    start_date = datetime.strptime(start_str.strip(), date_fmt)
    end_date = datetime.strptime(end_str.strip(), date_fmt)

    return PeriodOfTime(
        start_date=start_date.strftime(date_fmt),
        end_date=end_date.strftime(date_fmt)
    )

def format_title(data) -> str:
    """ Format dataset title with instituteName, modality, start- and end date requirements."""
    try:
        modality = data["modality"]
        institute = data["instituteName"]
        period = format_temporal_coverage(data["temporalCoverage"])
    except KeyError as e:
        raise KeyError(f"Missing required field in data: {e}")

    return f"{institute}_{modality}_{period.start_date.value}_{period.end_date.value}"

def map_xds_to_healthri_dcat_dataset(rows: Series, config: Dict) -> HRIDataset:
    _, data = rows
    agentConfig = config.get("agent")
    vCardConfig = config.get("v_card")
    datasetConfig = config.get("dataset")

    # formatting
    dataset_formatted_title = format_title(data)

    agent = HRIAgent(
        name=[{"value": data["instituteName"], "lang": "en"}],
        identifier=[{"value": agentConfig["identifier"]}],
        mbox = agentConfig["mbox"],
        homepage = agentConfig["homepage"],
    )

    vCard = HRIVCard(
        hasEmail = vCardConfig["has_email"],
        formatted_name = vCardConfig["formatted_name"],
    )

    dataset = HRIDataset(
        # MANDATORY DCAT FIELDS
        identifier = datasetConfig["identifier"],
        title=[{"value": dataset_formatted_title, "language": "en"}],
        description=[{"value": datasetConfig["description"], "lang": "en"}],
        publisher = agent,
        contact_point = vCard,
        theme = [URIRef(url) for url in datasetConfig["theme"]] if datasetConfig.get("theme") else [],
        keyword=[{"value": k} for k in datasetConfig["keyword"]],
        access_rights = URIRef(datasetConfig["access_rights"]),
        creator = [agent],
        applicable_legislation=[URIRef(url) for url in datasetConfig["applicable_legislation"]] if datasetConfig.get("applicable_legislation") else [],

        # CSV FIELDS
        number_of_unique_individuals = int(data['numberOfUniqueIndividuals']),
        number_of_records = int(data['numberOfRecords']),
        minimum_typical_age = int(data['minTypicalAge']),
        maximum_typical_age = int(data['maxTypicalAge']),
    )

    return dataset

if __name__ == '__main__':
    dataframe = read_csv("../../../examples/xds_input.csv")
    config_path = Path("../../../examples/xds_example_config.toml")
    config = load_img2catalog_configuration(config_path)

    datasets = []
    for row in dataframe.iterrows():
        dataset = map_xds_to_healthri_dcat_dataset(row, config)
        datasets.append(dataset)
        print(dataset.title)