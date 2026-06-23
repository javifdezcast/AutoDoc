import os
from typing import Iterable
from git import Repo
from languages import languages

class FileFinder:
    
    root_dir: str
    extensions: Iterable[str]
    scope: str
    ignore: Iterable[str]

    def __init__(self, config: dict):
        self.root_dir = config['root_dir']
        self.scope = config['scope']
        self.ignore = config['ignore']
        self.extensions = languages[config['language']].extensions

    
    def find_different_files(self) -> list[str]:
        langauge_files = self._find_matching_files(self.root_dir, self.extensions)
        files_to_document = langauge_files
        if (self.scope == 'diff'):
            different_files = self._find_changed_files(self.root_dir)
            files_to_document = list(set(langauge_files) & set(different_files))
        files_to_document = self._remove_ignored_files(files_to_document)
        return files_to_document

    
    def _find_matching_files(self, root: str, extensions: Iterable[str]) -> list[str]:
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

    
    def _find_changed_files(self, root: str) -> list[str]:
        repo = Repo(root)
        head_commit = repo.head.commit
        if not head_commit.parents:
            changed = {
                blob.path
                for blob in head_commit.tree.traverse()
                if blob.type == 'blob'
            }
            return [os.path.join(root, p) for p in sorted(changed)]
        parent_commit = head_commit.parents[0]
        diff_index = parent_commit.diff(head_commit)
        changed: set[str] = set()
        for change_type in ('A', 'D', 'M', 'R'):
            for diff in diff_index.iter_change_type(change_type):
                if diff.a_path:
                    changed.add(diff.a_path)
                if diff.b_path:
                    changed.add(diff.b_path)
        return [os.path.join(root, p) for p in sorted(changed)]

    
    def _remove_ignored_files(self, files_to_document: list[str]) -> list[str]:
        return [file for file in files_to_document if not self._is_ignored(file)]

    def _is_ignored(self, file)-> bool:
        normalized = file.replace("\\", "/")
        if 'venv' in file and not any(ignored in normalized for ignored in self.ignore):
            print('hola')
        return any(ignored in normalized for ignored in self.ignore)