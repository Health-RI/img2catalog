import logging
from typing import Dict, List

from pydantic import ValidationError
from rdflib import URIRef
from sempyro.hri_dcat import HRICatalog, HRIDataset, HRIVCard, HRIAgent

logger = logging.getLogger(__name__)


def get_dict_double_depth(dictionary, first_key, second_key):
    return dictionary[first_key][second_key] \
        if first_key in dictionary and second_key in dictionary[first_key] \
        else None


def get_dict_double_depth_uriref(dictionary, first_key, second_key):
    return URIRef(dictionary[first_key][second_key]) \
        if first_key in dictionary and second_key in dictionary[first_key] \
        else None


def map_xnat_to_healthriv2(unmapped_objects: Dict[str, List[Dict]]) -> Dict[str, List]:
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


    if xnat_catalog.get('publisher') and isinstance(xnat_catalog['publisher'], list):
        xnat_catalog['publisher'] = xnat_catalog['publisher'][0]

    catalog_obj = {
        'uri': URIRef(xnat_catalog['uri']),
        'model_object': HRICatalog(
            title=[xnat_catalog.get('title', None)],
            description=[xnat_catalog.get('description', None)],
            publisher=HRIAgent(**xnat_catalog['publisher']) if 'publisher' in xnat_catalog else None,
            dataset=xnat_catalog.get('dataset', None),
            contact_point=HRIVCard(
                formatted_name=get_dict_double_depth(xnat_catalog, "contact_point", "formatted_name"),
                hasEmail=get_dict_double_depth_uriref(xnat_catalog, "contact_point", "email")
            ),
        )
    }

    datasets = []
    for dataset in xnat_datasets:
        if dataset.get('publisher') and isinstance(dataset['publisher'], list):
            dataset['publisher'] = dataset['publisher'][0]
        if dataset.get('theme') and not isinstance(dataset['theme'], list):
            dataset['theme'] = [dataset['theme']]

        datasets.append({
            'uri': URIRef(dataset['uri']),
            'model_object': HRIDataset(
                title=dataset.get('title', [None]),
                description=dataset.get('description', None),
                creator=[HRIAgent(**creator_dict) for creator_dict in dataset.get('creator', [{}])],
                keyword=dataset.get('keyword', None),
                identifier=dataset.get('identifier', None),
                publisher=HRIAgent(**dataset['publisher']) if 'publisher' in dataset else None,
                theme=[URIRef(theme) for theme in dataset['theme']] if 'theme' in dataset else None,
                contact_point=HRIVCard(
                    formatted_name=get_dict_double_depth(dataset, "contact_point", "formatted_name"),
                    hasEmail=get_dict_double_depth_uriref(dataset, "contact_point", "email"),
                ),
                license=dataset.get('license', None),
                access_rights=URIRef(dataset['access_rights']) if 'access_rights' in dataset else None,
                applicable_legislation=[URIRef(app_leg) for app_leg in dataset['applicable_legislation']] if
                    'applicable_legislation' in dataset else None
            ),
        })

    mapped_objects = {
        'catalog': [catalog_obj],
        'dataset': datasets
    }
    return mapped_objects
