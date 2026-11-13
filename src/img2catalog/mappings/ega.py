import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from rdflib import XSD, URIRef
from sempyro import LiteralField
from sempyro.dcat import AccessRights, Attribution
from sempyro.foaf import Agent
from sempyro.hri_dcat import (
    DatasetStatus,
    DatasetTheme,
    HRIAgent,
    HRICatalog,
    HRIDataset,
    HRIDistribution,
    HRIVCard,
)

logger = logging.getLogger(__name__)

# Source used: Health-RI FSD "Mapping from the European Genome-Phenome Archive (EGA)" (schema v2.0.3)

EGA_DATASET_URL = "https://ega-archive.org/datasets/"
EGA_DAC_URL = "https://ega-archive.org/dacs/"
PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/"

FILE_TYPE_BINARY = "http://publications.europa.eu/resource/authority/file-type/BIN"
FILE_TYPE_TEXT = "http://publications.europa.eu/resource/authority/file-type/TXT"
# Extensions of uncompressed text based file formats; all other EGA files (bam, cram, gzipped files, ...) are binary
TEXT_FILE_EXTENSIONS = {
    "bed",
    "csv",
    "fa",
    "fasta",
    "fastq",
    "fq",
    "gff",
    "gff3",
    "gtf",
    "json",
    "maf",
    "sam",
    "tab",
    "tsv",
    "txt",
    "vcf",
    "xml",
}


def _is_empty(value: Any) -> bool:
    """Check if a value has no content: None, a blank string, or a list or dict containing only empty values.

    Empty values are left out of the mapping, so that they are not shown as if they have content.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict)):
        values = value.values() if isinstance(value, dict) else value
        return all(_is_empty(item) for item in values)
    return False


class MissingEGAValueError(KeyError):
    """A mandatory value of an EGA dataset is missing or empty, so the dataset cannot be mapped."""


def _text(value: Any) -> Optional[str]:
    """Return a single text or number as stripped text, or None when it is empty.

    Lists and dicts are refused, as they would otherwise be shown as text like "['a', None]".
    """
    if _is_empty(value):
        return None
    if not isinstance(value, (str, int, float)):
        raise TypeError(f"Expected a single text value, got {type(value).__name__}: {value!r}")
    return str(value).strip()


def _non_empty(values: Optional[List[Any]]) -> List[Any]:
    """Return the values of a list that have content."""
    return [value for value in values or [] if not _is_empty(value)]


def _to_literals(values: Optional[List[Any]]) -> List[LiteralField]:
    return [LiteralField(value=_text(value)) for value in _non_empty(values)]


def _required_config_literals(config: Dict, key: str) -> List[LiteralField]:
    """Convert a mandatory text config value, which may be a single text or a list of texts.

    An empty mandatory value is refused with a clear error, instead of silently leaving the field out.
    """
    value = config[key]
    literals = _to_literals(value if isinstance(value, list) else [value])
    if not literals:
        raise ValueError(f"Configuration value '{key}' is mandatory, but empty")
    return literals


def _without_empty(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Leave out the fields without content."""
    return {field: value for field, value in fields.items() if not _is_empty(value)}


def _to_urls(values: List[str]) -> List[URIRef]:
    return [URIRef(_text(value)) for value in _non_empty(values)]


def _to_datetime(value: Union[str, datetime]) -> datetime:
    """Accept a TOML datetime or an ISO 8601 string; "Z" is only parsed by fromisoformat from Python 3.11."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional(dataset_config: Dict, key: str, convert: Callable[[Any], Any]) -> Any:
    """Convert an optional config value, or return None when the key is absent or empty."""
    value = dataset_config.get(key)
    if _is_empty(value):
        return None
    return convert(value)


def _required_text(ega_dataset: Dict, key: str) -> str:
    """Return a mandatory text field of an EGA dataset; an empty value counts as missing."""
    value = _text(ega_dataset.get(key))
    if value is None:
        raise MissingEGAValueError(f"EGA dataset {ega_dataset.get('accession_id')} has no {key}")
    return value


def _dac_page(dac: Dict) -> Optional[str]:
    """Build the EGA archive URL of a Data Access Committee (DAC), or return None when it has no accession_id."""
    accession_id = _text(dac.get("accession_id"))
    return f"{EGA_DAC_URL}{accession_id}" if accession_id else None


def get_identifier(ega_dataset: Dict) -> str:
    """Build the EGA archive URL for an EGA dataset's accession_id."""
    return f"{EGA_DATASET_URL}{ega_dataset['accession_id']}"


def get_title(ega_dataset: Dict) -> str:
    return _required_text(ega_dataset, "title")


def get_description(ega_dataset: Dict) -> str:
    return _required_text(ega_dataset, "description")


def get_number_of_records(ega_dataset: Dict) -> Optional[int]:
    return ega_dataset.get("num_samples")


def get_release_date(ega_dataset: Dict) -> Optional[datetime]:
    released_date = _text(ega_dataset.get("released_date"))
    if released_date is None:
        return None

    try:
        return datetime.fromisoformat(released_date)
    except ValueError:
        logger.error("Could not parse EGA release date %r", released_date)
        return released_date


def get_keyword(ega_dataset: Dict) -> List[LiteralField]:
    """Map EGA's free-text `technologies` field to DCAT-AP keywords."""
    return _to_literals(ega_dataset.get("technologies"))


def get_contact_page(ega_dataset: Dict) -> List[str]:
    """Build the EGA archive URLs of the Data Access Committees (DACs) controlling the dataset."""
    return _non_empty([_dac_page(dac) for dac in ega_dataset.get("dacs") or []])


def get_main_contacts(ega_dataset: Dict) -> List[Dict]:
    """Return the main contacts of the Data Access Committees (DACs) controlling the dataset, with their DAC."""
    return [
        {**contact, "dac": dac}
        for dac in ega_dataset.get("dacs") or []
        for contact in dac.get("contacts") or []
        if contact.get("is_main")
    ]


def get_contact_email(ega_dataset: Dict) -> Optional[str]:
    """Return the email of the first DAC main contact, which handles the access requests of the dataset."""
    for contact in get_main_contacts(ega_dataset):
        email = _text(contact.get("email"))
        if email:
            return f"mailto:{email}"
    return None


def get_contact_name(contact: Dict) -> Optional[str]:
    """Join the first name and surname of an EGA contact, leaving out the empty parts."""
    return _text(" ".join(_text(contact.get(key)) or "" for key in ("first_name", "surname")))


def get_is_referenced_by(ega_dataset: Dict) -> List[str]:
    """Build PubMed URLs of the publications of the EGA studies the dataset belongs to."""
    urls = []
    for study in ega_dataset.get("studies") or []:
        for pubmed_id in _non_empty(study.get("pubmed_ids")):
            url = f"{PUBMED_URL}{_text(pubmed_id)}/"
            if url not in urls:
                urls.append(url)
    return urls


def get_qualified_attribution(ega_dataset: Dict, dataset_config: Dict) -> List[Attribution]:
    """Attribute the dataset to the main contact(s) of its Data Access Committees (DACs).

    EGA does not provide an ORCID or homepage for DAC contacts, so the DAC page is used as the agent's identifier
    and homepage.
    The role is not present in EGA metadata and is taken from the local node configuration when set.
    Contacts without a name, or of a DAC without an accession_id, are left out, as their agent would miss its
    mandatory name or identifier.
    """
    attribution_kwargs = {}
    role = _text((dataset_config.get("qualified_attribution") or {}).get("role"))
    if role:
        attribution_kwargs["role"] = role

    attributions = []
    for contact in get_main_contacts(ega_dataset):
        name = get_contact_name(contact)
        dac_page = _dac_page(contact["dac"])
        if name is None or dac_page is None:
            logger.debug("Skipping DAC main contact without a name or DAC accession_id: %s", contact)
            continue

        agent_kwargs = {}
        email = _text(contact.get("email"))
        if email:
            agent_kwargs["mbox"] = [f"mailto:{email}"]

        agent = Agent(
            name=[LiteralField(value=name)],
            identifier=LiteralField(value=dac_page),
            homepage=dac_page,
            **agent_kwargs,
        )
        attributions.append(Attribution(agent=agent, **attribution_kwargs))

    return attributions


def get_file_type(ega_file: Dict) -> str:
    """Map an EGA file extension to the EU file type: TXT for text formats, BIN for binary formats."""
    extension = (ega_file.get("extension") or "").lower()
    return FILE_TYPE_TEXT if extension in TEXT_FILE_EXTENSIONS else FILE_TYPE_BINARY


def get_byte_size(ega_files: List[Dict], description: str = "files") -> Optional[LiteralField]:
    """Sum the known sizes of the files, or return None when no file size is known.

    Unknown sizes are not counted as 0 bytes, so a size of 0 is never shown for files of unknown size. When only
    some sizes are known, their sum is a lower bound of the actual size, which is logged as a warning.
    """
    file_sizes = [int(ega_file["filesize"]) for ega_file in ega_files if not _is_empty(ega_file.get("filesize"))]
    if not file_sizes:
        return None
    if len(file_sizes) < len(ega_files):
        logger.warning(
            "Size of %d of %d %s is unknown; byte size only counts the known sizes",
            len(ega_files) - len(file_sizes),
            len(ega_files),
            description,
        )
    return LiteralField(value=str(sum(file_sizes)), datatype=XSD.nonNegativeInteger)


def get_publisher(publisher_config: Dict) -> HRIAgent:
    """Build the publishing organisation, which is not present in EGA metadata, from the local node configuration."""
    publisher_kwargs = {}
    publisher_type = _text(publisher_config.get("publisher_type"))
    if publisher_type:
        publisher_kwargs["publisher_type"] = publisher_type

    return HRIAgent(
        name=_required_config_literals(publisher_config, "name"),
        identifier=_required_config_literals(publisher_config, "identifier"),
        mbox=publisher_config["mbox"],
        homepage=publisher_config["homepage"],
        **publisher_kwargs,
    )


def map_ega_to_healthri_dcat_distributions(ega_dataset: Dict, config: Dict) -> List[HRIDistribution]:
    """Map the files of an EGA dataset to Distributions.

    The files together form the Distribution of the dataset, so individual files are not mapped to separate
    Distributions. Only when the data is available in multiple formats, a Distribution is made per format.
    """
    files_per_type: Dict[str, List[Dict]] = {}
    for ega_file in ega_dataset.get("files") or []:
        files_per_type.setdefault(get_file_type(ega_file), []).append(ega_file)

    if not files_per_type:
        return []

    distribution_config = config["distribution"]
    dataset_page = get_identifier(ega_dataset)

    distributions = []
    for file_type, ega_files in files_per_type.items():
        # The byte size is mandatory, so a Distribution without any known file size is left out
        format_code = file_type.rsplit("/", 1)[-1]
        byte_size = get_byte_size(ega_files, f"{format_code} files of EGA dataset {ega_dataset['accession_id']}")
        if byte_size is None:
            logger.warning(
                "Skipping %s Distribution of EGA dataset %s: no file size is known",
                format_code,
                ega_dataset["accession_id"],
            )
            continue

        # Properties in the order of the FSD mapping document
        distribution_fields = {
            "access_url": dataset_page,
            "byte_size": byte_size,
            "description": [LiteralField(value=get_description(ega_dataset))],
            "format": file_type,
            "language": _optional(distribution_config, "language", _to_urls),
            "license": distribution_config["license"],
            "release_date": get_release_date(ega_dataset),
            # EGA shows the DAC access policy on the dataset page
            "rights": dataset_page,
            "title": [LiteralField(value=get_title(ega_dataset))],
        }
        distributions.append(HRIDistribution(**_without_empty(distribution_fields)))

    return distributions


def map_ega_to_healthri_dcat_dataset(
    ega_dataset: Dict, config: Dict, distribution_uris: Optional[List[URIRef]] = None
) -> HRIDataset:
    """Map an EGA dataset to a Dataset, referring to its Distributions (mapped separately) by URI.

    Fields without content, in EGA or in the configuration, are left out instead of being mapped as empty values.
    """
    dataset_config = config["dataset"]
    contact_point_config = dataset_config["contact_point"]

    dataset_themes = [DatasetTheme(URIRef(theme)) for theme in dataset_config["theme"]]

    dataset_keywords = get_keyword(ega_dataset)
    dataset_keywords.extend(_to_literals(dataset_config.get("keyword")))

    dataset_applicable_legislation = _to_urls(dataset_config["applicable_legislation"])

    publisher = get_publisher(dataset_config["publisher"])

    contact_point_kwargs = {}
    contact_page = get_contact_page(ega_dataset)
    if contact_page:
        contact_point_kwargs["contact_page"] = contact_page

    # The DAC handles access requests, so its main contact's email is used; the configured email is a fallback
    contact_point = HRIVCard(
        hasEmail=get_contact_email(ega_dataset) or _text(contact_point_config.get("email")),
        formatted_name=_required_config_literals(contact_point_config, "formatted_name")[0].value,
        **contact_point_kwargs,
    )

    # Publications of the EGA studies, extended with configured publications
    is_referenced_by = _to_urls(get_is_referenced_by(ega_dataset) + _non_empty(dataset_config.get("is_referenced_by")))

    # Properties in the order of the FSD mapping document. Values not present in EGA metadata are
    # supplied from the local node configuration; optional ones are left out when not configured.
    dataset_fields = {
        "access_rights": AccessRights(URIRef(dataset_config["access_rights"])),
        "applicable_legislation": dataset_applicable_legislation,
        "code_values": _optional(dataset_config, "code_values", _to_urls),
        # Contact point combines the DAC from EGA with the name from the local node configuration
        "contact_point": contact_point,
        "creator": [publisher],
        "description": [LiteralField(value=get_description(ega_dataset))],
        "distribution": distribution_uris,
        "geographical_coverage": _optional(dataset_config, "spatial", _to_urls),
        "health_theme": _optional(dataset_config, "health_theme", _to_urls),
        "identifier": LiteralField(value=get_identifier(ega_dataset)),
        "is_referenced_by": is_referenced_by,
        "keyword": dataset_keywords,
        "language": _optional(dataset_config, "language", _to_urls),
        "legal_basis": _optional(dataset_config, "legal_basis", _to_urls),
        "minimum_typical_age": _optional(dataset_config, "minimum_typical_age", int),
        "number_of_records": get_number_of_records(ega_dataset),
        "number_of_unique_individuals": _optional(dataset_config, "number_of_unique_individuals", int),
        "personal_data": _optional(dataset_config, "personal_data", _to_urls),
        "population_coverage": _optional(
            dataset_config, "population_coverage", lambda value: LiteralField(value=_text(value))
        ),
        "publisher": publisher,
        "purpose": _optional(dataset_config, "purpose", _to_urls),
        "qualified_attribution": get_qualified_attribution(ega_dataset, dataset_config),
        "release_date": get_release_date(ega_dataset),
        "status": _optional(dataset_config, "status", lambda value: DatasetStatus(URIRef(value))),
        "theme": dataset_themes,
        "title": [LiteralField(value=get_title(ega_dataset))],
        "type": _optional(dataset_config, "type", _to_urls),
    }

    return HRIDataset(**_without_empty(dataset_fields))


def map_ega_to_healthri_dcat_catalog(config: Dict, dataset_uris: List[URIRef]) -> HRICatalog:
    """Map a Catalog grouping all EGA datasets of one institute.

    EGA has no equivalent of a Catalog, so its properties are supplied from the local node configuration. The
    institute publishing the datasets is also the creator and publisher of the Catalog.
    """
    catalog_config = config["catalog"]
    contact_point_config = catalog_config["contact_point"]
    publisher = get_publisher(config["dataset"]["publisher"])

    # Properties in the order of the FSD mapping document
    catalog_fields = {
        "contact_point": HRIVCard(
            hasEmail=_text(contact_point_config["email"]),
            formatted_name=_required_config_literals(contact_point_config, "formatted_name")[0].value,
        ),
        "creator": [publisher],
        "description": _required_config_literals(catalog_config, "description"),
        "geographical_coverage": _optional(catalog_config, "spatial", _to_urls),
        "language": _optional(catalog_config, "language", _to_urls),
        "publisher": publisher,
        "release_date": _optional(catalog_config, "release_date", _to_datetime),
        "title": _required_config_literals(catalog_config, "title"),
    }

    # The datasets are mandatory for a Catalog, so they are passed even when there are none
    return HRICatalog(dataset=dataset_uris, **_without_empty(catalog_fields))
