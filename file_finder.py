import os
from typing import Iterable


class Git:

    def __init__(self):
        pass

    @classmethod
    def find_different_files(cls,config: dict) -> list[str]:
        return cls.find_matching_files(
            config[config['language']]['root'],
            config[config['language']]['extensions']
        )


    @classmethod
    def find_matching_files(self, root: str, extensions: Iterable[str]) -> list[str]:
        normalized = tuple(
            (ext if ext.startswith('.') else f'.{ext}').lower()
            for ext in extensions
        )

        matches = []
        for current_dir, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.lower().endswith(normalized):
                    matches.append(os.path.join(current_dir, filename))
        return matches

    @classmethod
    def find_changed_files(cls, root: str, extensions: Iterable[str]) -> list[str]:
        