"""Pushing the Catalog, Datasets, Distributions and their contact points (vcard:Kind) to an FDP, from the CLI.

Each input is run with its example configuration (and, for XDS, its example CSV); only the external systems (EGA API,
XNAT server, FDP) are simulated. Every push is run twice, as rerunning must update the FDP instead of adding to it.
"""

import datetime
import pathlib
from unittest.mock import MagicMock, patch

import pytest
from fairclient.sparqlclient import FDPSPARQLClient
from rdflib import DCAT, DCTERMS, RDF, BNode, Graph, Literal, Namespace, URIRef

from img2catalog.cli_app import cli_click

from .outputs.fake_fdp import FDP_ROOT, FDP_URL, FakeFDP, FakeSPARQLEndpoint

EXAMPLES = pathlib.Path(__file__).parents[2] / "examples"
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
FDP_ARGS = ["fdp", "--fdp", FDP_URL, "-u", "user", "-p", "password", "-s", f"{FDP_URL}/sparql"]

# The SPARQL parser of rdflib, used by the fake FDP, uses deprecated pyparsing functions
pytestmark = [
    pytest.mark.filterwarnings(r"ignore::DeprecationWarning:rdflib.plugins.sparql"),
    pytest.mark.filterwarnings(r"ignore::DeprecationWarning:pyparsing"),
]


@pytest.fixture
def fdp():
    """A simulated FDP, which the FDP output of the CLI logs in to and queries."""
    fake = FakeFDP()

    def sparql_client(endpoint):
        client = FDPSPARQLClient(endpoint)
        client.sparql = FakeSPARQLEndpoint(fake)
        return client

    fdp_client = patch("img2catalog.outputs.fdp.FDPClient", return_value=fake)
    sparql = patch("img2catalog.outputs.fdp.FDPSPARQLClient", side_effect=sparql_client)
    with fdp_client, sparql:
        yield fake


def run(runner, args):
    result = runner.invoke(cli_click, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return result


def existing_catalog(fdp, title="Existing catalog", datasets=0):
    """A catalog already in the FDP, with datasets that the push does not know about."""
    graph = Graph()
    subject = URIRef("http://example.com/catalog")
    graph.add((subject, RDF.type, DCAT.Catalog))
    graph.add((subject, DCTERMS.title, Literal(title)))
    graph.add((subject, DCTERMS.isPartOf, FDP_ROOT))
    catalog = fdp.create_and_publish("catalog", graph)
    for number in range(datasets):
        dataset = Graph()
        subject = URIRef(f"http://example.com/other-dataset-{number}")
        dataset.add((subject, RDF.type, DCAT.Dataset))
        dataset.add((subject, DCTERMS.identifier, Literal(str(subject))))
        dataset.add((subject, DCTERMS.isPartOf, catalog))
        fdp.create_and_publish("dataset", dataset)
    return catalog


def assert_contact_point(fdp, record):
    """The record has a contact point (vcard:Kind) with its name and email."""
    graph = fdp.records[record]
    contact_points = list(graph.objects(record, DCAT.contactPoint))
    assert len(contact_points) == 1, f"{record} has contact points {contact_points}"
    kind = contact_points[0]
    assert isinstance(kind, BNode)
    assert (kind, RDF.type, VCARD.Kind) in graph
    assert graph.value(kind, VCARD.fn) is not None
    assert str(graph.value(kind, VCARD.hasEmail)).startswith("mailto:")


def assert_fdp_consistent(fdp):
    """All records are published, linked to their parent and their parent to them, without internal URIs."""
    store = fdp.graph()
    assert not [term for triple in store for term in triple if "img2catalog.internal" in str(term)]
    assert set(fdp.states.values()) == {"PUBLISHED"}
    for catalog in fdp.of_type("catalog"):
        assert fdp.records[catalog].value(catalog, DCTERMS.isPartOf) == FDP_ROOT
    for child_type, link in (("dataset", DCAT.dataset), ("distribution", DCAT.distribution)):
        for child in fdp.of_type(child_type):
            parent = fdp.records[child].value(child, DCTERMS.isPartOf)
            assert parent in fdp.records, f"{child} is part of {parent}, which is not in the FDP"
            assert (parent, link, child) in fdp.records[parent], f"{parent} does not link to {child}"


def test_ega_pushes_catalog_datasets_distributions_and_contact_points(fdp, default_ega_dataset, isolated_cli_runner):
    # Arrange: an EGA dataset with files in two formats
    default_ega_dataset["files"].append({"accession_id": "EGAF00000000003", "filesize": 500, "extension": "vcf"})
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]

    # Act: push, change the dataset in EGA, and push again
    with patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset]):
        run(isolated_cli_runner, args + FDP_ARGS)
        first = dict(fdp.records)
        default_ega_dataset["title"] = "Updated title"
        run(isolated_cli_runner, args + FDP_ARGS)

    # Assert: one Catalog, Dataset and Distribution per format, the same records as after the first push
    catalogs, datasets, distributions = (list(fdp.of_type(t)) for t in ("catalog", "dataset", "distribution"))
    assert (len(catalogs), len(datasets), len(distributions)) == (1, 1, 2)
    assert set(fdp.records) == set(first)
    assert_fdp_consistent(fdp)

    catalog, dataset = catalogs[0], datasets[0]
    assert fdp.records[catalog].value(catalog, DCTERMS.title) == Literal("Example EGA catalog")
    assert fdp.records[dataset].value(dataset, DCTERMS.title) == Literal("Updated title")
    assert_contact_point(fdp, catalog)
    assert_contact_point(fdp, dataset)
    formats = {fdp.records[d].value(d, DCTERMS.format) for d in distributions}
    assert formats == {
        URIRef("http://publications.europa.eu/resource/authority/file-type/BIN"),
        URIRef("http://publications.europa.eu/resource/authority/file-type/TXT"),
    }


def test_ega_updates_given_catalog_and_keeps_its_other_datasets(fdp, default_ega_dataset, isolated_cli_runner):
    # Arrange: a catalog in the FDP with two datasets not from this push
    catalog = existing_catalog(fdp, datasets=2)
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]

    # Act
    with patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset]):
        run(isolated_cli_runner, args + FDP_ARGS + ["-c", str(catalog)])
        run(isolated_cli_runner, args + FDP_ARGS + ["-c", str(catalog)])

    # Assert: the given catalog is updated with the mapped Catalog, and still lists its other datasets
    assert list(fdp.of_type("catalog")) == [catalog]
    assert fdp.records[catalog].value(catalog, DCTERMS.title) == Literal("Example EGA catalog")
    assert len(list(fdp.records[catalog].objects(catalog, DCAT.dataset))) == 3
    assert_contact_point(fdp, catalog)
    assert_fdp_consistent(fdp)


def test_xds_pushes_example_datasets_with_contact_points(fdp, isolated_cli_runner):
    # Arrange: XDS has no Catalog, so its datasets go into a given catalog
    catalog = existing_catalog(fdp)
    args = [
        "-c",
        str(EXAMPLES / "xds" / "example_config.toml"),
        "xds",
        "--input",
        str(EXAMPLES / "xds" / "input_example.csv"),
        "map-xds",
    ]

    # Act
    run(isolated_cli_runner, args + FDP_ARGS + ["-c", str(catalog)])
    first = dict(fdp.records)
    run(isolated_cli_runner, args + FDP_ARGS + ["-c", str(catalog)])

    # Assert: one Dataset per row of the example CSV, updated on the rerun
    datasets = list(fdp.of_type("dataset"))
    assert len(datasets) == 4
    assert set(fdp.records) == set(first)
    assert list(fdp.of_type("catalog")) == [catalog]
    titles = {str(fdp.records[d].value(d, DCTERMS.title)) for d in datasets}
    assert titles == {
        "Hospital A - CT - 2024",
        "Hospital A - MR - 2024",
        "Hospital B - CT - 2024",
        "Hospital B - CT - 2023",
    }
    for dataset in datasets:
        assert_contact_point(fdp, dataset)
    assert_fdp_consistent(fdp)


def test_xds_without_catalog_fails(fdp, isolated_cli_runner):
    args = ["xds", "--input", str(EXAMPLES / "xds" / "input_example.csv"), "map-xds"]

    result = isolated_cli_runner.invoke(
        cli_click, ["-c", str(EXAMPLES / "xds" / "example_config.toml"), *args, *FDP_ARGS]
    )

    assert result.exit_code != 0
    assert "No catalog URI set to push to" in str(result.exception)
    assert fdp.records == {}


def xnat_metadata():
    """Metadata as XNATInput gathers it from the XNAT server, for one project."""
    project_uri = "https://xnat.example.com/data/archive/projects/test_img2catalog"
    dataset = {
        "title": ["Basic test project to test the img2catalog"],
        "description": ["In this project, we test xnat and dcat and make sure a description appears."],
        "creator": [{"name": ["prof. Albus Dumbledore"]}],
        "keyword": ["demo", "test"],
        "identifier": project_uri,
        "issued": datetime.datetime(2024, 1, 1),
        "modified": datetime.datetime(2024, 1, 1),
        "uri": project_uri,
    }
    return {"catalog": [{"uri": "https://xnat.example.com", "dataset": [project_uri]}], "dataset": [dataset]}


def test_xnat_pushes_catalog_and_datasets_with_contact_points(fdp, isolated_cli_runner):
    args = ["-c", str(EXAMPLES / "xnat" / "example-config.toml"), "xnat", "--server", "https://xnat.example.com"]

    # Act
    xnat_server = patch("xnat.connect", return_value=MagicMock())
    xnat_projects = patch("img2catalog.cli_app.XNATInput.get_metadata", side_effect=xnat_metadata)
    with xnat_server, xnat_projects:
        run(isolated_cli_runner, [*args, "map-xnat-hriv2", *FDP_ARGS])
        first = dict(fdp.records)
        run(isolated_cli_runner, [*args, "map-xnat-hriv2", *FDP_ARGS])

    # Assert: the XNAT Catalog is created once and found again by its title, with the dataset in it
    catalogs, datasets = list(fdp.of_type("catalog")), list(fdp.of_type("dataset"))
    assert (len(catalogs), len(datasets)) == (1, 1)
    assert set(fdp.records) == set(first)
    assert fdp.records[catalogs[0]].value(catalogs[0], DCTERMS.title) == Literal("Example XNAT catalog")
    assert_contact_point(fdp, catalogs[0])
    assert_contact_point(fdp, datasets[0])
    assert_fdp_consistent(fdp)
