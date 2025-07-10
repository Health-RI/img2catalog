import logging
from typing import Dict, List

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

        # Build HRIDataset kwargs excluding None values
        dataset_kwargs = {}
        
        # Required fields
        dataset_kwargs['title'] = dataset.get('title', [None])
        dataset_kwargs['description'] = dataset.get('description', None)
        dataset_kwargs['creator'] = [HRIAgent(**creator_dict) for creator_dict in dataset.get('creator', [{}])]
        dataset_kwargs['keyword'] = dataset.get('keyword', None)
        dataset_kwargs['identifier'] = dataset.get('identifier', None)
        
        # Optional fields - only include if present
        if 'publisher' in dataset:
            dataset_kwargs['publisher'] = HRIAgent(**dataset['publisher'])
        if 'theme' in dataset:
            dataset_kwargs['theme'] = [URIRef(theme) for theme in dataset['theme']]
        if 'access_rights' in dataset:
            dataset_kwargs['access_rights'] = URIRef(dataset['access_rights'])
        if 'applicable_legislation' in dataset:
            dataset_kwargs['applicable_legislation'] = [URIRef(app_leg) for app_leg in dataset['applicable_legislation']]
        if 'license' in dataset:
            dataset_kwargs['license'] = dataset['license']
        if 'maximum_typical_age' in dataset:
            dataset_kwargs['maximum_typical_age'] = dataset['maximum_typical_age']
        if 'minimum_typical_age' in dataset:
            dataset_kwargs['minimum_typical_age'] = dataset['minimum_typical_age']
        if 'number_of_records' in dataset:
            dataset_kwargs['number_of_records'] = dataset['number_of_records']
        if 'number_of_unique_individuals' in dataset:
            dataset_kwargs['number_of_unique_individuals'] = dataset['number_of_unique_individuals']
        if 'population_coverage' in dataset:
            dataset_kwargs['population_coverage'] = dataset['population_coverage']
        if 'health_theme' in dataset:
            dataset_kwargs['health_theme'] = [URIRef(theme) for theme in dataset['health_theme']]
        if 'personal_data' in dataset:
            dataset_kwargs['personal_data'] = [URIRef(pd) for pd in dataset['personal_data']]
        if 'purpose' in dataset:
            dataset_kwargs['purpose'] = [URIRef(purpose) for purpose in dataset['purpose']]
        if 'legal_basis' in dataset:
            dataset_kwargs['legal_basis'] = [URIRef(lb) for lb in dataset['legal_basis']]
        if 'analytics' in dataset:
            dataset_kwargs['analytics'] = [URIRef(analytics) for analytics in dataset['analytics']]
        if 'code_values' in dataset:
            dataset_kwargs['code_values'] = [URIRef(cv) for cv in dataset['code_values']]
        if 'coding_system' in dataset:
            dataset_kwargs['coding_system'] = [URIRef(cs) for cs in dataset['coding_system']]
        if 'conforms_to' in dataset:
            dataset_kwargs['conforms_to'] = [URIRef(ct) for ct in dataset['conforms_to']]
        if 'documentation' in dataset:
            dataset_kwargs['documentation'] = [URIRef(doc) for doc in dataset['documentation']]
        if 'frequency' in dataset:
            dataset_kwargs['frequency'] = URIRef(dataset['frequency'])
        if 'in_series' in dataset:
            dataset_kwargs['in_series'] = [URIRef(series) for series in dataset['in_series']]
        if 'is_referenced_by' in dataset:
            dataset_kwargs['is_referenced_by'] = [URIRef(ref) for ref in dataset['is_referenced_by']]
        if 'qualified_attribution' in dataset:
            dataset_kwargs['qualified_attribution'] = dataset['qualified_attribution']
        if 'qualified_relation' in dataset:
            dataset_kwargs['qualified_relation'] = dataset['qualified_relation']
        if 'quality_annotation' in dataset:
            dataset_kwargs['quality_annotation'] = dataset['quality_annotation']
        if 'retention_period' in dataset:
            dataset_kwargs['retention_period'] = dataset['retention_period']
        if 'sample' in dataset:
            dataset_kwargs['sample'] = [URIRef(sample) for sample in dataset['sample']]
        if 'source' in dataset:
            dataset_kwargs['source'] = [URIRef(source) for source in dataset['source']]
        if 'status' in dataset:
            dataset_kwargs['status'] = URIRef(dataset['status'])
        if 'type' in dataset:
            dataset_kwargs['type'] = [URIRef(dtype) for dtype in dataset['type']]
        if 'distribution' in dataset:
            dataset_kwargs['distribution'] = [URIRef(dist) for dist in dataset['distribution']]
        if 'other_identifier' in dataset:
            dataset_kwargs['other_identifier'] = dataset['other_identifier']
        
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
