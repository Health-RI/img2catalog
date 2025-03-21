from rdflib import URIRef
from sempyro.foaf import Agent
from sempyro.hri_dcat import HRICatalog, HRIDataset
from sempyro.vcard import VCard


def map_xnat_to_healthriv1(unmapped_objects):
    xnat_catalog = unmapped_objects['catalog'][0]
    xnat_datasets = unmapped_objects['dataset']
    catalog_obj = {
        'uri': URIRef(xnat_catalog['uri']),
        'model_object': HRICatalog(
            title=[xnat_catalog['title']],
            description=[xnat_catalog['description']],
            publisher=[Agent(**xnat_catalog['publisher'])],
            dataset=[dataset['uri'] for dataset in xnat_datasets]
        )
    }

    datasets = []
    for dataset in xnat_datasets:
        datasets.append({
            'uri': URIRef(dataset['uri']),
            'model_object': HRIDataset(
                title=dataset['title'],
                description=dataset['description'],
                creator=[Agent(**creator_dict) for creator_dict in dataset['creator']],
                keyword=dataset['keyword'],
                identifier=dataset['identifier'],
                issued=dataset['issued'],
                modified=dataset['modified'],
                publisher=[Agent(**dataset['publisher'])],
                theme=[URIRef(dataset['theme'])],
                contact_point=[VCard(
                    full_name=[dataset['contact_point']['full_name']],
                    hasEmail=[URIRef(dataset['contact_point']['email'])],
                    hasUID=URIRef(dataset['contact_point']['hasUID'])
                )]
            ),
        })

    mapped_objects = {
        'catalog': [catalog_obj],
        'dataset': datasets
    }
    return mapped_objects
