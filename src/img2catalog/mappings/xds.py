from pathlib import Path
from typing import Dict

from pydantic import AnyUrl, AnyHttpUrl

from img2catalog.configmanager import load_img2catalog_configuration
from pandas import Series
from rdflib import URIRef
from sempyro.hri_dcat import HRIAgent, HRIVCard, HRIDataset

from img2catalog.inputs.csv import read_csv


def map_xds_to_healthri_dcat_dataset(row: Series, config: Dict) -> HRIDataset:
    _, data = row
    agentConfig = config.get("agent")
    vCardConfig = config.get("v_card")
    datasetConfig = config.get("dataset")

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
        title=[{"value": datasetConfig["title"], "lang": "en"}],
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
    dataframe = read_csv("../inputs/xds_input.csv")

    config_path = Path("../../../examples/xds_example_config.toml")
    config = load_img2catalog_configuration(config_path)

    datasets = []
    for row in dataframe.iterrows():
        dataset = map_xds_to_healthri_dcat_dataset(row, config)
        datasets.append(dataset)
        print(dataset)