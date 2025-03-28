# @patch("img2catalog.xnat_parser.add_or_update_dataset")
# @patch("img2catalog.xnat_parser.xnat_list_datasets")
# def test_xnat_to_fdp_push(xnat_list_datasets, add_or_update_dataset, mock_dataset, config, empty_graph):
#     """Tests of XNAT to RDF pushing happens even when errors happen"""
#     # FIXME: Figure out what the goal is of this test
#
#     xnat_list_datasets.return_value = [(mock_dataset, URIRef("http://example.com/dataset"))]
#
#     xnat_to_FDP(None, config, URIRef("http://example.com/catalog"), None, None)
#
#     # Check if function is called and correct term added to Graph
#     add_or_update_dataset.assert_called_once()
#     assert (
#                URIRef("http://example.com/dataset"),
#                DCTERMS.isPartOf,
#                URIRef("http://example.com/catalog"),
#            ) in add_or_update_dataset.call_args.args[0], "FDP catalog reference missing"
#
#
# @patch("img2catalog.xnat_parser.add_or_update_dataset")
# @patch("img2catalog.xnat_parser.xnat_list_datasets")
# def test_xnat_to_fdp_push_error(xnat_list_datasets, add_or_update_dataset, mock_dataset, config, empty_graph):
#     # FIXME: Figure out what the goal is of this test also
#     xnat_list_datasets.return_value = [
#         (mock_dataset, URIRef("http://example.com/dataset1")),
#         (mock_dataset, URIRef("http://example.com/dataset2")),
#     ]
#     add_or_update_dataset.side_effect = [ValueError, None]
#
#     xnat_to_FDP(None, config, URIRef("http://example.com/catalog"), None, None)
#
#     assert add_or_update_dataset.call_count == 2
#     assert (
#                URIRef("http://example.com/dataset2"),
#                DCTERMS.isPartOf,
#                URIRef("http://example.com/catalog"),
#            ) in add_or_update_dataset.call_args_list[1].args[0], "FDP catalog reference missing"
