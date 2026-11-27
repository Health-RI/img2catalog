"""Pushing the Catalog, Datasets, Distributions and their contact points (vcard:Kind) to an FDP, from the CLI.

Each input is run with its example configuration (and, for XDS, its example CSV); only the external systems (EGA API,
XNAT server, FDP) are simulated. Every push is run twice, as rerunning must update the FDP instead of adding to it.
"""

import copy
import datetime
import pathlib
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest
import requests
from fairclient.sparqlclient import FDPSPARQLClient
from fairclient.utils import rewrite_graph_subject
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


def existing_catalog(fdp, title="Existing catalog", datasets=0, parent=FDP_ROOT):
    """A catalog already in the FDP (in the FDP with this parent), with datasets that the push does not know about."""
    graph = Graph()
    subject = URIRef("http://example.com/catalog")
    graph.add((subject, RDF.type, DCAT.Catalog))
    graph.add((subject, DCTERMS.title, Literal(title)))
    graph.add((subject, DCTERMS.isPartOf, parent))
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
        # A catalog only links to datasets in the FDP, not to e.g. XNAT project URLs
        assert set(fdp.records[catalog].objects(catalog, DCAT.dataset)) <= set(fdp.of_type("dataset"))
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


def test_ega_pushes_into_given_catalog_without_changing_it(fdp, default_ega_dataset, isolated_cli_runner):
    """A catalog given with -c may be maintained otherwise, so by default it is not updated with the mapped Catalog."""
    catalog = existing_catalog(fdp, datasets=2)
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]

    with patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset]):
        run(isolated_cli_runner, [*args, *FDP_ARGS, "-c", str(catalog)])
        run(isolated_cli_runner, [*args, *FDP_ARGS, "-c", str(catalog)])

    assert list(fdp.of_type("catalog")) == [catalog]
    assert fdp.records[catalog].value(catalog, DCTERMS.title) == Literal("Existing catalog")
    assert len(list(fdp.records[catalog].objects(catalog, DCAT.dataset))) == 3
    assert_fdp_consistent(fdp)


def test_ega_updates_given_catalog_and_keeps_its_other_datasets(fdp, default_ega_dataset, isolated_cli_runner):
    # Arrange: a catalog in the FDP with two datasets not from this push
    catalog = existing_catalog(fdp, datasets=2)
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]
    fdp_args = [*FDP_ARGS, "-c", str(catalog), "--update-catalog"]

    # Act
    with patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset]):
        run(isolated_cli_runner, args + fdp_args)
        run(isolated_cli_runner, args + fdp_args)

    # Assert: the given catalog is updated with the mapped Catalog, and still lists its other datasets
    assert list(fdp.of_type("catalog")) == [catalog]
    assert fdp.records[catalog].value(catalog, DCTERMS.title) == Literal("Example EGA catalog")
    assert len(list(fdp.records[catalog].objects(catalog, DCAT.dataset))) == 3
    assert_contact_point(fdp, catalog)
    assert_fdp_consistent(fdp)


def test_xds_pushes_example_datasets_with_contact_points(fdp, isolated_cli_runner):
    # Arrange: XDS has no Catalog, so its datasets go into a given catalog
    catalog = existing_catalog(fdp)
    example_csv = EXAMPLES / "xds" / "input_example.csv"
    args = ["-c", str(EXAMPLES / "xds" / "example_config.toml"), "xds", "--input", str(example_csv), "map-xds"]

    # Act
    run(isolated_cli_runner, args + FDP_ARGS + ["-c", str(catalog)])

    # Assert: one Dataset per row of the example CSV
    datasets = list(fdp.of_type("dataset"))
    assert len(datasets) == 4
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


def test_xds_rerun_adds_the_datasets_again(fdp, isolated_cli_runner):
    """The identifier is a prefix and a new UUID on every run, so the FDP output cannot find a dataset again."""
    catalog = existing_catalog(fdp)
    example_csv = EXAMPLES / "xds" / "input_example.csv"
    args = ["-c", str(EXAMPLES / "xds" / "example_config.toml"), "xds", "--input", str(example_csv), "map-xds"]

    run(isolated_cli_runner, args + FDP_ARGS + ["-c", str(catalog)])
    run(isolated_cli_runner, args + FDP_ARGS + ["-c", str(catalog)])

    assert len(list(fdp.of_type("dataset"))) == 8
    assert_fdp_consistent(fdp)


def test_xds_without_catalog_fails(fdp, isolated_cli_runner):
    args = ["xds", "--input", str(EXAMPLES / "xds" / "input_example.csv"), "map-xds"]

    result = isolated_cli_runner.invoke(
        cli_click, ["-c", str(EXAMPLES / "xds" / "example_config.toml"), *args, *FDP_ARGS]
    )

    # Reported as an error of the push, not as a traceback
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "No catalog URI set to push to" in result.output
    assert fdp.records == {}


def xnat_metadata(description="In this project, we test xnat and dcat and make sure a description appears."):
    """Metadata as XNATInput gathers it from the XNAT server, for one project."""
    project_uri = "https://xnat.example.com/data/archive/projects/test_img2catalog"
    dataset = {
        "title": ["Basic test project to test the img2catalog"],
        "description": [description],
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
    # The project description changes between the two runs
    metadata = [xnat_metadata(), xnat_metadata("Updated description")]
    xnat_projects = patch("img2catalog.cli_app.XNATInput.get_metadata", side_effect=metadata)
    with xnat_server, xnat_projects:
        run(isolated_cli_runner, [*args, "map-xnat-hriv2", *FDP_ARGS])
        first = dict(fdp.records)
        run(isolated_cli_runner, [*args, "map-xnat-hriv2", *FDP_ARGS])

    # Assert: the XNAT Catalog is created once and found again by its title, with the dataset in it
    catalogs, datasets = list(fdp.of_type("catalog")), list(fdp.of_type("dataset"))
    assert (len(catalogs), len(datasets)) == (1, 1)
    assert set(fdp.records) == set(first)
    assert fdp.records[catalogs[0]].value(catalogs[0], DCTERMS.title) == Literal("Example XNAT catalog")
    assert fdp.records[datasets[0]].value(datasets[0], DCTERMS.description) == Literal("Updated description")
    assert_contact_point(fdp, catalogs[0])
    assert_contact_point(fdp, datasets[0])
    assert_fdp_consistent(fdp)


def test_ega_skips_distributions_of_dataset_that_failed(fdp, default_ega_dataset, isolated_cli_runner, caplog):
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]
    create_record = fdp.create_and_publish

    def refuse_datasets(resource_type, metadata):
        if resource_type == "dataset":
            raise ValueError("400 Bad Request")
        return create_record(resource_type, metadata)

    ega = patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset])
    with ega, patch.object(fdp, "create_and_publish", side_effect=refuse_datasets):
        result = isolated_cli_runner.invoke(cli_click, args + FDP_ARGS)

    # The failed push is reported, so that scripts notice that the FDP is not up to date
    assert result.exit_code == 1
    assert "1 record(s) could not be pushed to the FDP: dataset" in result.output
    assert list(fdp.of_type("dataset")) == []
    assert list(fdp.of_type("distribution")) == []
    assert "as its Dataset was not pushed to the FDP" in caplog.text


def test_ega_reports_failed_distribution_but_pushes_the_rest(fdp, default_ega_dataset, isolated_cli_runner):
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]
    create_record = fdp.create_and_publish

    def refuse_distributions(resource_type, metadata):
        if resource_type == "distribution":
            raise ValueError("400 Bad Request")
        return create_record(resource_type, metadata)

    ega = patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset])
    with ega, patch.object(fdp, "create_and_publish", side_effect=refuse_distributions):
        result = isolated_cli_runner.invoke(cli_click, args + FDP_ARGS)

    assert result.exit_code == 1
    assert "1 record(s) could not be pushed to the FDP: distribution" in result.output
    assert len(list(fdp.of_type("dataset"))) == 1
    assert list(fdp.of_type("distribution")) == []


def test_ega_pushes_distributions_when_publishing_updated_dataset_fails(fdp, default_ega_dataset, isolated_cli_runner):
    """The dataset is updated, so its Distributions are still pushed into it; the push is reported as failed."""
    # Arrange: pushed once, then a file of the dataset changed in EGA
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]
    with patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset]):
        run(isolated_cli_runner, args + FDP_ARGS)
        get_record = fdp.get

        def state_unreachable(url, headers, timeout):
            if url.endswith("/meta"):
                raise requests.ConnectionError("timeout")
            return get_record(url, headers, timeout)

        default_ega_dataset["files"][0]["filesize"] = 5000

        # Act
        with patch.object(fdp, "get", side_effect=state_unreachable):
            result = isolated_cli_runner.invoke(cli_click, args + FDP_ARGS)

    # Assert
    assert result.exit_code == 1
    assert "publishing it failed" in result.output
    sizes = {str(size) for d in fdp.of_type("distribution") for size in fdp.records[d].objects(d, DCAT.byteSize)}
    assert sizes == {"7000"}


def test_push_without_catalog_and_sparql_warns_about_new_catalogs(
    fdp, default_ega_dataset, isolated_cli_runner, caplog
):
    args = ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]
    fdp_args = ["fdp", "--fdp", FDP_URL, "-u", "user", "-p", "password"]

    with patch("img2catalog.cli_app.fetch_ega_datasets", return_value=[default_ega_dataset]):
        run(isolated_cli_runner, args + fdp_args)

    assert "a new catalog with new datasets is created on every push" in caplog.text


def test_xnat_removed_distribution_link_stays_removed(fdp, isolated_cli_runner):
    """Only links to children in the FDP are kept on an update, so a link removed in XNAT is removed in the FDP."""
    args = ["-c", str(EXAMPLES / "xnat" / "example-config.toml"), "xnat", "--server", "https://xnat.example.com"]
    link = URIRef("https://xnat.example.com/data/projects/test_img2catalog")
    with_link = xnat_metadata()
    with_link["dataset"][0]["distribution"] = [str(link)]

    with patch("xnat.connect", return_value=MagicMock()):
        with patch("img2catalog.cli_app.XNATInput.get_metadata", return_value=with_link):
            run(isolated_cli_runner, [*args, "map-xnat-hriv2", *FDP_ARGS])
        dataset = next(iter(fdp.of_type("dataset")))
        assert (dataset, DCAT.distribution, link) in fdp.records[dataset]
        with patch("img2catalog.cli_app.XNATInput.get_metadata", side_effect=xnat_metadata):
            run(isolated_cli_runner, [*args, "map-xnat-hriv2", *FDP_ARGS])

    assert (dataset, DCAT.distribution, link) not in fdp.records[dataset]


def test_xnat_pushes_into_given_catalog_without_changing_it(fdp, isolated_cli_runner):
    catalog = existing_catalog(fdp)
    args = ["-c", str(EXAMPLES / "xnat" / "example-config.toml"), "xnat", "--server", "https://xnat.example.com"]

    xnat_server = patch("xnat.connect", return_value=MagicMock())
    xnat_projects = patch("img2catalog.cli_app.XNATInput.get_metadata", side_effect=xnat_metadata)
    with xnat_server, xnat_projects:
        run(isolated_cli_runner, [*args, "map-xnat-hriv2", *FDP_ARGS, "-c", str(catalog)])

    assert list(fdp.of_type("catalog")) == [catalog]
    assert fdp.records[catalog].value(catalog, DCTERMS.title) == Literal("Existing catalog")
    assert len(fdp.of_type("dataset")) == 1
    assert_fdp_consistent(fdp)


def ega_args():
    return ["-c", str(EXAMPLES / "ega" / "example_config.toml"), "ega", "-a", "EGAD00001005083", "map-ega-hriv2"]


def invoke(runner, args, datasets):
    """Run the CLI with these EGA datasets, without asserting on the exit code."""
    with patch("img2catalog.cli_app.fetch_ega_datasets", return_value=datasets):
        return runner.invoke(cli_click, args)


def refuse_fdp_root(fdp):
    """Make reading the FDP itself fail, as when the FDP is briefly unreachable."""
    get_record = fdp.get

    def get(url, headers, timeout):
        if url == FDP_URL:
            raise requests.ConnectionError("timeout")
        return get_record(url, headers, timeout)

    return patch.object(fdp, "get", side_effect=get)


def add_record(fdp, uri, record_type, graph):
    """Put a record in the FDP as it is found with SPARQL, without going through the FDP API."""
    fdp.records[uri] = graph
    fdp.record_types[uri] = record_type
    fdp.states[uri] = "PUBLISHED"


def remove_record(fdp, uri):
    del fdp.records[uri], fdp.record_types[uri], fdp.states[uri]


def test_ega_fails_without_pushing_when_the_fdp_root_cannot_be_read(fdp, default_ega_dataset, isolated_cli_runner):
    """Without the URI of the FDP, the catalog would get the wrong parent and be created again on every push."""
    with refuse_fdp_root(fdp):
        result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "Could not read the FDP root" in result.output
    assert fdp.records == {}


def test_ega_pushes_into_given_catalog_when_the_fdp_root_cannot_be_read_to_update_it(
    fdp, default_ega_dataset, isolated_cli_runner
):
    catalog = existing_catalog(fdp)

    with refuse_fdp_root(fdp):
        result = invoke(
            isolated_cli_runner, ega_args() + FDP_ARGS + ["-c", str(catalog), "--update-catalog"], [default_ega_dataset]
        )

    # The catalog is not updated, which is reported, but the datasets are still pushed into it
    assert result.exit_code == 1
    assert f"catalog {catalog}: Could not read the FDP root" in result.output
    assert fdp.records[catalog].value(catalog, DCTERMS.title) == Literal("Existing catalog")
    assert len(fdp.of_type("dataset")) == 1
    assert len(fdp.of_type("distribution")) == 1


def test_ega_rerun_updates_datasets_when_the_fdp_root_cannot_be_read(
    fdp, default_ega_dataset, isolated_cli_runner, caplog
):
    """The root is not needed to push into a given catalog; the records found are then only trusted on the FDP URL."""
    catalog = existing_catalog(fdp)
    args = ega_args() + FDP_ARGS + ["-c", str(catalog)]
    assert invoke(isolated_cli_runner, args, [default_ega_dataset]).exit_code == 0

    with refuse_fdp_root(fdp), caplog.at_level("WARNING"):
        result = invoke(isolated_cli_runner, args, [default_ega_dataset])

    assert result.exit_code == 0, result.output
    assert "Only accepting records of" in caplog.text
    assert len(fdp.of_type("dataset")) == 1


def test_ega_stops_when_two_catalogs_have_the_title_of_the_catalog(fdp, default_ega_dataset, isolated_cli_runner):
    first = existing_catalog(fdp, title="Example EGA catalog")
    second = existing_catalog(fdp, title="Example EGA catalog")

    result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert result.exit_code == 1
    assert "More than one catalog titled 'Example EGA catalog'" in result.output
    assert "give the one to use with -c" in result.output
    assert set(fdp.of_type("catalog")) == {first, second}
    assert fdp.of_type("dataset") == {}


def test_ega_ignores_catalog_with_its_title_that_is_not_in_the_fdp_root(fdp, default_ega_dataset, isolated_cli_runner):
    """A catalog is found by its title within the FDP itself, so records of another FDP are not updated."""
    foreign = existing_catalog(fdp, title="Example EGA catalog", parent=URIRef("http://other-fdp.example.com"))

    result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert result.exit_code == 0, result.output
    assert len(fdp.of_type("catalog")) == 2
    assert not list(fdp.records[foreign].objects(foreign, DCAT.contactPoint)), "the foreign catalog was updated"
    assert not list(fdp.records[foreign].objects(foreign, DCAT.dataset))


def test_ega_does_not_update_catalog_found_outside_the_fdp(fdp, default_ega_dataset, isolated_cli_runner):
    """A forged SPARQL result must not receive the authenticated requests of the FDP client."""
    forged = URIRef("http://attacker.invalid/catalog/1")
    graph = Graph()
    graph.add((forged, RDF.type, DCAT.Catalog))
    graph.add((forged, DCTERMS.title, Literal("Example EGA catalog")))
    graph.add((forged, DCTERMS.isPartOf, FDP_ROOT))
    add_record(fdp, forged, "catalog", graph)
    before = set(graph)

    with patch.object(fdp, "get", wraps=fdp.get) as get, patch.object(
        fdp, "update_serialized", wraps=fdp.update_serialized
    ) as update:
        result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert result.exit_code == 1
    assert "not a record of the FDP" in result.output
    assert not [call for call in get.call_args_list if "attacker" in str(call.args[0])]
    update.assert_not_called()
    assert set(fdp.records[forged]) == before
    assert fdp.of_type("dataset") == {}


def test_ega_does_not_update_distribution_found_outside_the_fdp(fdp, default_ega_dataset, isolated_cli_runner):
    # Arrange: pushed once, after which the SPARQL store holds the distribution as a record on another host
    assert invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset]).exit_code == 0
    (distribution,) = fdp.of_type("distribution")
    forged = URIRef("http://attacker.invalid/distribution/1")
    graph = Graph() + fdp.records[distribution]
    rewrite_graph_subject(graph, distribution, forged)
    remove_record(fdp, distribution)
    add_record(fdp, forged, "distribution", graph)
    before = set(graph)

    # Act
    with patch.object(fdp, "get", wraps=fdp.get) as get, patch.object(
        fdp, "update_serialized", wraps=fdp.update_serialized
    ) as update:
        result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    # Assert
    assert result.exit_code == 1
    assert "not a record of the FDP" in result.output
    assert not [call for call in get.call_args_list if "attacker" in str(call.args[0])]
    assert all(call.args[0] != forged for call in update.call_args_list)
    assert set(fdp.records[forged]) == before


def test_ega_distributions_are_found_within_their_own_dataset(fdp, default_ega_dataset, isolated_cli_runner):
    """Datasets with the same file formats each keep their own Distributions when rerunning."""
    default_ega_dataset["files"].append({"accession_id": "EGAF00000000003", "filesize": 500, "extension": "vcf"})
    second = copy.deepcopy(default_ega_dataset)
    second.update(accession_id="EGAD00001005084", title="Second dataset")
    datasets = [default_ega_dataset, second]

    first_run = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, datasets)
    first = set(fdp.records)
    second_run = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, datasets)

    assert (first_run.exit_code, second_run.exit_code) == (0, 0), second_run.output
    assert set(fdp.records) == first
    assert len(fdp.of_type("dataset")) == 2
    parents = Counter(fdp.records[d].value(d, DCTERMS.isPartOf) for d in fdp.of_type("distribution"))
    assert sorted(parents.values()) == [2, 2]
    assert set(parents) == set(fdp.of_type("dataset"))
    assert_fdp_consistent(fdp)


def test_ega_reports_two_distributions_with_the_same_format_in_a_dataset(fdp, default_ega_dataset, isolated_cli_runner):
    assert invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset]).exit_code == 0
    (distribution,) = fdp.of_type("distribution")
    fdp.create_and_publish("distribution", Graph() + fdp.records[distribution])

    result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert result.exit_code == 1
    assert "1 record(s) could not be pushed to the FDP: distribution" in result.output
    assert "More than one distribution with format" in result.output
    assert len(fdp.of_type("distribution")) == 2


def test_ega_pushes_datasets_into_given_catalog_when_updating_it_fails(fdp, default_ega_dataset, isolated_cli_runner):
    catalog = existing_catalog(fdp)
    update_record = fdp.update_serialized

    def refuse_catalog(resource_uri, metadata):
        if resource_uri == catalog:
            raise ValueError("400 Bad Request")
        return update_record(resource_uri, metadata)

    with patch.object(fdp, "update_serialized", side_effect=refuse_catalog):
        result = invoke(
            isolated_cli_runner, ega_args() + FDP_ARGS + ["-c", str(catalog), "--update-catalog"], [default_ega_dataset]
        )

    assert result.exit_code == 1
    assert f"1 record(s) could not be pushed to the FDP: catalog {catalog}: 400 Bad Request" in result.output
    assert fdp.records[catalog].value(catalog, DCTERMS.title) == Literal("Existing catalog")
    assert len(fdp.of_type("dataset")) == 1
    assert len(fdp.of_type("distribution")) == 1


def test_ega_pushes_nothing_when_the_catalog_cannot_be_created(fdp, default_ega_dataset, isolated_cli_runner):
    create_record = fdp.create_and_publish

    def refuse_catalogs(resource_type, metadata):
        if resource_type == "catalog":
            raise ValueError("400 Bad Request")
        return create_record(resource_type, metadata)

    with patch.object(fdp, "create_and_publish", side_effect=refuse_catalogs):
        result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert (
        "Could not push catalog 'Example EGA catalog' to the FDP, so no records are pushed: 400 Bad Request"
        in result.output
    )
    assert fdp.records == {}


def renamed_catalog_config(tmp_path):
    """The EGA example configuration, with the title of the catalog changed."""
    config = (EXAMPLES / "ega" / "example_config.toml").read_text()
    assert 'title = "Example EGA catalog"' in config
    path = tmp_path / "renamed.toml"
    path.write_text(config.replace('title = "Example EGA catalog"', 'title = "Renamed EGA catalog"'))
    return path


def test_ega_refuses_new_catalog_when_its_datasets_are_in_another_catalog(
    fdp, default_ega_dataset, isolated_cli_runner, tmp_path
):
    """Renaming the catalog in the config must not create a second catalog with every dataset again."""
    # Arrange: pushed once under the original title
    assert invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset]).exit_code == 0
    records = set(fdp.records)
    (catalog,) = fdp.of_type("catalog")
    renamed = ["-c", str(renamed_catalog_config(tmp_path)), *ega_args()[2:]]

    # Act
    result = invoke(isolated_cli_runner, renamed + FDP_ARGS, [default_ega_dataset])

    # Assert
    assert result.exit_code == 1
    assert "No catalog titled 'Renamed EGA catalog' is in the FDP" in result.output
    assert f"datasets of this push are already in catalog(s) {catalog}" in result.output
    assert set(fdp.records) == records


def test_ega_updates_renamed_catalog_when_given_with_its_uri(fdp, default_ega_dataset, isolated_cli_runner, tmp_path):
    assert invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset]).exit_code == 0
    records = set(fdp.records)
    (catalog,) = fdp.of_type("catalog")
    renamed = ["-c", str(renamed_catalog_config(tmp_path)), *ega_args()[2:]]

    result = invoke(
        isolated_cli_runner, renamed + FDP_ARGS + ["-c", str(catalog), "--update-catalog"], [default_ega_dataset]
    )

    assert result.exit_code == 0, result.output
    assert set(fdp.records) == records
    assert Literal("Renamed EGA catalog") in set(fdp.records[catalog].objects(catalog, DCTERMS.title))


def test_ega_creates_catalog_when_its_datasets_are_not_in_the_fdp(fdp, default_ega_dataset, isolated_cli_runner):
    """Datasets with other identifiers in another catalog do not stop a new catalog."""
    existing_catalog(fdp, datasets=2)

    result = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert result.exit_code == 0, result.output
    assert len(fdp.of_type("catalog")) == 2


def test_ega_keeps_compressed_and_uncompressed_distributions_apart_on_rerun(
    fdp, default_ega_dataset, isolated_cli_runner
):
    """A .vcf and a .vcf.gz file are both TXT; the compression keeps their Distributions apart in the FDP."""
    default_ega_dataset["files"] = [
        {"accession_id": "EGAF00000000001", "filesize": 100, "extension": "vcf"},
        {"accession_id": "EGAF00000000002", "filesize": 200, "extension": "vcf.gz"},
    ]

    first_run = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])
    records = set(fdp.records)
    second_run = invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset])

    assert (first_run.exit_code, second_run.exit_code) == (0, 0), second_run.output
    assert set(fdp.records) == records
    distributions = fdp.of_type("distribution")
    assert len(distributions) == 2
    gzip = URIRef("http://www.iana.org/assignments/media-types/application/gzip")
    sizes = {
        fdp.records[d].value(d, DCAT.compressFormat): str(fdp.records[d].value(d, DCAT.byteSize)) for d in distributions
    }
    assert sizes == {None: "100", gzip: "200"}
    assert_fdp_consistent(fdp)


def test_ega_pushes_into_catalog_found_by_its_title_without_changing_it(fdp, default_ega_dataset, isolated_cli_runner):
    """A catalog in the FDP with the title of the mapped Catalog gets the datasets, but keeps its metadata."""
    catalog = existing_catalog(fdp, title="Example EGA catalog", datasets=2)

    with patch.object(fdp, "update_serialized", wraps=fdp.update_serialized) as update:
        run_twice = [invoke(isolated_cli_runner, ega_args() + FDP_ARGS, [default_ega_dataset]) for _ in range(2)]

    assert all(result.exit_code == 0 for result in run_twice), run_twice[-1].output
    assert catalog not in [call.args[0] for call in update.call_args_list]
    assert list(fdp.of_type("catalog")) == [catalog]
    assert not list(fdp.records[catalog].objects(catalog, DCAT.contactPoint))
    assert len(list(fdp.records[catalog].objects(catalog, DCAT.dataset))) == 3


def test_ega_updates_catalog_found_by_its_title_with_update_catalog(fdp, default_ega_dataset, isolated_cli_runner):
    catalog = existing_catalog(fdp, title="Example EGA catalog", datasets=2)

    run_twice = [
        invoke(isolated_cli_runner, ega_args() + FDP_ARGS + ["--update-catalog"], [default_ega_dataset])
        for _ in range(2)
    ]

    assert all(result.exit_code == 0 for result in run_twice), run_twice[-1].output
    assert list(fdp.of_type("catalog")) == [catalog]
    assert_contact_point(fdp, catalog)
    assert len(list(fdp.records[catalog].objects(catalog, DCAT.dataset))) == 3
