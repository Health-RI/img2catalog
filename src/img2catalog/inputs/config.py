from typing import List, Dict


class ConfigInput:
    def __init__(self, config):
        self.config = config

    def get_metadata_concept(self, concept_type: str):
        return [self.config.get(concept_type, dict())]

    def update_metadata(self, source_objects: List[Dict], config_object: List[Dict]):
        if isinstance(config_object, list):
            config_object = config_object[0]
        if not isinstance(source_objects, list):
            source_objects = [source_objects]
        for source_obj in source_objects:
            source_obj.update(config_object)
        return source_objects


