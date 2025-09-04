import logging
from typing import Dict, List

from rdflib import URIRef
from sempyro.dcat import Attribution, Relationship
from sempyro.hri_dcat import HRICatalog, HRIDataset, HRIVCard, HRIAgent
from sempyro.adms import Identifier
from sempyro.dqv import QualityCertificate
from sempyro.time import PeriodOfTime

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

        # Build HRIDataset kwargs excluding None values
        dataset_kwargs = {}
        
        # Required fields
        dataset_kwargs['title'] = dataset.get('title', [None])
        dataset_kwargs['description'] = dataset.get('description', None)
        dataset_kwargs['creator'] = [HRIAgent(**creator_dict) for creator_dict in dataset.get('creator', [{}])]
        dataset_kwargs['keyword'] = dataset.get('keyword', None)
        dataset_kwargs['identifier'] = dataset.get('identifier', None)
        if 'publisher' in dataset:
            dataset_kwargs['publisher'] = HRIAgent(**dataset['publisher'])
        if 'theme' in dataset:
            dataset_kwargs['theme'] = [URIRef(theme) for theme in dataset['theme']]

        # Optional fields - only include if present
        simple_assignment = ['license', 'minimum_typical_age', 'maximum_typical_age', 'number_of_records',
                             'number_of_unique_individuals', 'population_coverage']
        uri_assignment = ['access_rights', 'frequency', 'status']
        list_uri_assignment = ['applicable_legislation', 'health_theme', 'personal_data', 'purpose',
                               'legal_basis', 'analytics', 'code_values', 'conforms_to', 'documentation',
                               'in_series', 'is_referenced_by', 'sample', 'source', 'type', 'distribution',
                               'coding_system']
        for field in simple_assignment:
            if field in dataset:
                dataset_kwargs[field] = dataset[field]
        for field in uri_assignment:
            if field in dataset:
                dataset_kwargs[field] = URIRef(dataset[field])
        for field in list_uri_assignment:
            if field in dataset:
                dataset_kwargs[field] = [URIRef(item) for item in dataset[field]]

        if 'retention_period' in dataset:
            dataset_kwargs['retention_period'] = PeriodOfTime(**dataset['retention_period'])

        nested_structures = [('other_identifier', Identifier),
                             ('qualified_attribution', Attribution),
                             ('qualified_relation', Relationship),
                             ('quality_annotation', QualityCertificate)]
        for struct in nested_structures:
            if struct[0] in dataset:
                orig_list = dataset[struct[0]]
                result_list = []
                for item in orig_list:
                    if isinstance(item, dict):
                        result_list.append(struct[1](**item))
                    else:
                        result_list.append(item)
                dataset_kwargs[struct[0]] = result_list

        # Contact point is special - build VCard
        contact_point = HRIVCard(
            formatted_name=get_dict_double_depth(dataset, "contact_point", "formatted_name"),
            hasEmail=get_dict_double_depth_uriref(dataset, "contact_point", "email"),
        )
        dataset_kwargs['contact_point'] = contact_point

        datasets.append({
            'uri': URIRef(dataset['uri']),
            'model_object': HRIDataset(**dataset_kwargs),
        })

    mapped_objects = {
        'catalog': [catalog_obj],
        'dataset': datasets
    }
    return mapped_objects
