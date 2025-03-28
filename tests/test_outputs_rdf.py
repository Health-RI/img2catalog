# @freeze_time("2024-04-01")
# @patch("xnat.session.BaseXNATSession")
# @patch("img2catalog.xnat_parser.xnat_to_DCATCatalog")
# @patch("img2catalog.xnat_parser.xnat_list_datasets")
# def test_xnat_to_rdf(xnat_list_datasets, xnat_to_DCATCatalog, session, mock_dataset, mock_catalog, config, empty_graph):
#     """Tests if XNAT to RDF pushing happens with correct arguments and graph is modified correctly
#
#     Tests if `xnat_to_RDF` creates a Catalog based on the XNAT URL from the XNATSession object, and combines them
#     properly with the discovered datasets.
#     """
#     xnat_to_DCATCatalog.return_value = mock_catalog
#
#     session.projects = {}
#     session.url_for.return_value = "https://example.com"
#
#     xnat_list_datasets.return_value = [(mock_dataset, URIRef("https://example.com/dataset"))]
#
#     result_graph = xnat_to_RDF(session, config)
#     reference_graph = empty_graph.parse(source="tests/references/minimal_dcat_catalog_dataset.ttl")
#
#     assert to_isomorphic(result_graph) == to_isomorphic(reference_graph)
