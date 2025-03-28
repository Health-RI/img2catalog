from typing import Dict, List

from rdflib import URIRef
from sempyro.foaf import Agent
from sempyro.hri_dcat import HRICatalog, HRIDataset
from sempyro.vcard import VCard


def map_xnat_to_healthriv1(unmapped_objects: Dict[str, List[Dict]]) -> Dict[str, List]:
    """ Map XNAT metadata dictionaries to Health-RI concept objects

    Parameters
    ----------
    unmapped_objects: Dict[str, List[Dict]]
        Dictionary containing a list of metadata dictionaries per concept type.

    Returns
    -------
    Dict[str, List]
        Dictionary with a list of Health-RI concept objects per concept type
    """

    xnat_catalog = unmapped_objects['catalog'][0]
    xnat_datasets = unmapped_objects['dataset']


    if xnat_catalog.get('publisher') and not isinstance(xnat_catalog['publisher'], list):
        xnat_catalog['publisher'] = [xnat_catalog['publisher']]

    catalog_obj = {
        'uri': URIRef(xnat_catalog['uri']),
        'model_object': HRICatalog(
            title=[xnat_catalog.get('title', None)],
            description=[xnat_catalog.get('description', None)],
            publisher=[Agent(**publisher_dict) for publisher_dict in xnat_catalog['publisher']] \
                if 'publisher' in xnat_catalog else None,
            dataset=xnat_catalog.get('dataset', None)
        )
    }

    datasets = []
    for dataset in xnat_datasets:
        if dataset.get('publisher') and not isinstance(dataset['publisher'], list):
            dataset['publisher'] = [dataset['publisher']]
        datasets.append({
            'uri': URIRef(dataset['uri']),
            'model_object': HRIDataset(
                title=dataset.get('title', [None]),
                description=dataset.get('description', None),
                creator=[Agent(**creator_dict) for creator_dict in dataset.get('creator', [{}])],
                keyword=dataset.get('keyword', None),
                identifier=dataset.get('identifier', None),
                issued=dataset.get('issued', None),
                modified=dataset.get('modified', None),
                publisher=[Agent(**publisher_dict) for publisher_dict in dataset['publisher']] \
                    if 'publisher' in xnat_catalog else None,
                theme=[URIRef(dataset['theme'])] if 'theme' in dataset else None,
                contact_point=[VCard(
                    full_name=[dataset['contact_point']['full_name']] \
                        if 'contact_point' in dataset and 'full_name' in dataset['contact_point'] else None,
                    hasEmail=[URIRef(dataset['contact_point']['email'])] \
                        if 'contact_point' in dataset and 'email' in dataset['contact_point'] else None,
                    hasUID=URIRef(dataset['contact_point']['identifier']) \
                        if 'contact_point' in dataset and 'identifier' in dataset['contact_point'] else None,
                )],
                license=dataset.get('license', None)
            ),
        })

    mapped_objects = {
        'catalog': [catalog_obj],
        'dataset': datasets
    }
    return mapped_objects
