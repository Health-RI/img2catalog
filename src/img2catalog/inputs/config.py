from typing import List, Dict, Union


class ConfigInput:
    """ Input class that handles the metadata input from configuration

    Parameters
    ----------
    config : Dict
        Dictionary containing the contents of the configuration

    """
    def __init__(self, config: Dict):
        self.config = config

    def get_metadata_concept(self, concept_type: str) -> List[Union[Dict, None]]:
        """ Get metadata for a specified concept type

        This method returns a list of length one containing a dictionary with the metadata for the specified
        concept type from the configuration file. If no metadata can be found, None is returned.

        Parameters
        ----------
        concept_type : str
            Name of the concept type of which you want to retrieve the metadata from the configuration

        Returns
        ----------
        List[Union[Dict, None]]
            List containing a dictionary with the metadata, or None if no metadata could be found.
        """
        return [self.config.get(concept_type, {})]

    def update_metadata(self, source_objects: List[Dict], config_object: List[Dict]) -> List[Dict]:
        """ Update the metadata for a concept with additional metadata

        The list of dictionaries containing metadata, `source_objects`, gets updated with the metadata in
        `config_object`. `config_object` should be a list of length 1 containing a dictionary with the
        metadata. If the length of `config_object` is larger than 1, the first element is taken.

        Parameters
        ----------
        source_objects : List[Dict]
            A list of dictionaries containing the metadata that should be updated.
        config_object : List[Dict]
            A list of length 1 containing the dictionary with the metadata used to update the `source_objects`.

        Returns
        ----------
        List[Dict]
            List containing the updated metadata dictionaries.
        """
        if isinstance(config_object, list):
            config_object = config_object[0]
        if not isinstance(source_objects, list):
            source_objects = [source_objects]
        for source_obj in source_objects:
            # If the source_obj does not already contain information that is in config_object,
            # i.e., if the keys from source_obj are not in the keys of config_object,
            # we can just run source_obj.update(config_object)
            if not set(source_obj.keys()).intersection(set(config_object.keys())):
                source_obj.update(config_object)
            else:
                # If items from source_obj are in config_object, we cannot update the source_obj dictionary
                # in one go. We need to update each item separately in order check if for example a value is
                # a list, and update each item in the list one by one.
                items_already_updated = []
                for source_key, source_value in source_obj.items():
                    if source_key in config_object.keys():
                        if isinstance(source_value, list):
                            for item in source_obj[source_key]:
                                item.update(config_object[source_key])
                        elif isinstance(source_value, dict):
                            source_obj[source_key].update(config_object[source_key])
                        else:
                            source_obj[source_key] = config_object[source_key]
                        items_already_updated.append(source_key)
                for config_key, config_value in config_object.items():
                    if config_key not in items_already_updated:
                        source_obj[config_key] = config_value

        return source_objects
