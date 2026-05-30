import os
from typing import Iterable
from git import Repo
from languages import languages


class FileFinder:

    def __init__(self):
        pass

    @classmethod
    def find_different_files(cls,config: dict) -> list[str]:
        root = config['root_dir']
        langauge_files = cls.find_matching_files(root, languages[config['language']]['extensions'])
        files_to_document = langauge_files
        if (config['scope'] == 'diff'):
            different_files = cls.find_changed_files(root)
            files_to_document = list(set(langauge_files) & set(different_files))
        return files_to_document



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
    def find_changed_files(cls, root: str) -> list[str]:
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