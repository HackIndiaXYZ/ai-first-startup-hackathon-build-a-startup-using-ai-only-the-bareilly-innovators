"""
TITAN AI  File Manager Module
Voice-controlled file and folder operations.
"""

import os
import shutil
import glob
from pathlib import Path


class FileManager:
    def __init__(self):
        # Default paths
        self.desktop = Path(os.path.expanduser("~/Desktop"))
        self.documents = Path(os.path.expanduser("~/Documents"))
        self.downloads = Path(os.path.expanduser("~/Downloads"))

    def _resolve_path(self, name: str) -> Path:
        """If name has no path separator, default to Desktop."""
        name_lower = name.lower()
        if name_lower == "desktop":
            return self.desktop
        elif name_lower == "documents":
            return self.documents
        elif name_lower == "downloads":
            return self.downloads
            
        p = Path(name)
        if not p.is_absolute() and str(p.parent) == ".":
            return self.desktop / name
        return p

    def create_file(self, name: str) -> str:
        path = self._resolve_path(name)
        try:
            path.touch()
            print(f" Created file: {path}")
            return f"File '{name}' created on Desktop."
        except Exception as e:
            return f"Failed to create file: {e}"

    def create_folder(self, name: str) -> str:
        path = self._resolve_path(name)
        try:
            path.mkdir(parents=True, exist_ok=True)
            print(f" Created folder: {path}")
            return f"Folder '{name}' created on Desktop."
        except Exception as e:
            return f"Failed to create folder: {e}"

    def delete_file(self, name: str) -> str:
        path = self._resolve_path(name)
        # Safety: prevent deleting system-critical paths
        protected = ["C:\\Windows", "C:\\Program Files", "C:\\Users"]
        for p in protected:
            if str(path).startswith(p) and len(str(path)) < len(p) + 10:
                return "Cannot delete system-protected paths."

        try:
            if path.is_file():
                path.unlink()
                return f"File '{name}' deleted."
            elif path.is_dir():
                shutil.rmtree(path)
                return f"Folder '{name}' deleted."
            else:
                return f"'{name}' not found on Desktop."
        except Exception as e:
            return f"Failed to delete: {e}"

    def find_file(self, name: str) -> str:
        print(f" Searching for: {name}")
        results = []
        for search_dir in [self.desktop, self.documents, self.downloads]:
            matches = glob.glob(str(search_dir / f"**/*{name}*"), recursive=True)
            results.extend(matches[:5])  # limit per folder

        if results:
            found = ", ".join(os.path.basename(r) for r in results[:5])
            return f"Found: {found}"
        return f"No files matching '{name}' found."

    def list_files(self, folder_name: str = None) -> str:
        if folder_name:
            target = self._resolve_path(folder_name)
        else:
            target = self.desktop

        if not target.exists():
            return f"Folder '{folder_name}' not found."

        items = list(target.iterdir())[:15]  # limit to 15
        if not items:
            return "The folder is empty."

        listing = ", ".join(i.name for i in items)
        return f"Contents: {listing}"

    def open_file(self, name: str) -> str:
        path = self._resolve_path(name)
        if path.exists():
            os.startfile(str(path))
            return f"Opening {name}."
        return f"File '{name}' not found."


file_manager = FileManager()
