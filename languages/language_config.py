from typing import Any

from builders import Skeletoniser


class LanguageConfig:
    name:str
    extensions:list[str]
    skeletoniser:Skeletoniser
    template_directory:str
    example_directory:str
    node_types:dict[str, str]
    insertion:str
    queries:list[str]

    def __init__(self, data: dict[str, Any]):
        self.name = data['name']
        self.extensions = data['extensions']
        self.skeletoniser = data['skeletoniser']
        self.template_directory = data['template_directory']
        self.example_directory = data['example_directory']
        self.node_types = data['node_types']
        self.insertion = data['insertion']
        self.queries = data['queries']