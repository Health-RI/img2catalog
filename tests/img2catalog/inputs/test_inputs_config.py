from img2catalog.inputs.config import ConfigInput


def test_update_metadata_source_obj_list():
    """ Test if source_objects gets converted to list if it is not a list """
    config_input = ConfigInput({})
    source_objects = {'test_key': 'test_value'}
    expected_source_objects = [source_objects]
    assert config_input.update_metadata(source_objects, {}) == expected_source_objects


def test_update_metadata_config_obj_list():
    """ Test if config_object is reduced to the first element if list is supplied  """
    config_input = ConfigInput({})
    source_objects = [{'test_key': 'test_value'}]
    config_object = [{'test_key': 'right_test_value'}, {'test_key': 'wrong_test_value'}]
    expected_source_objects = [{'test_key': 'right_test_value'}]
    assert config_input.update_metadata(source_objects, config_object) == expected_source_objects
