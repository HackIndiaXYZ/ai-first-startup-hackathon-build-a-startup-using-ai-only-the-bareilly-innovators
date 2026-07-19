"""
SIVI AI  File Manager Module
Voice-controlled file and folder operations.
"""

import os
import sys
import subprocess
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
        
        self.db_path = Path(os.path.expanduser("~/.sivi_files.db"))
        self._init_db()
        
        # Start background indexing thread
        self.index_thread = threading.Thread(target=self._indexer_worker, daemon=True)
        self.index_thread.start()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    name TEXT,
                    lower_name TEXT
                )
            ''')
            # Create index for fast O(1) lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_lower_name ON files(lower_name)')

    def _indexer_worker(self):
        """Background thread that walks directories and builds the SQLite index."""
        print("[Sivi] Background File Indexer starting...")
        search_dirs = [
            self.desktop, self.documents, self.downloads,
            Path(os.path.expanduser("~/Music")),
            Path(os.path.expanduser("~/Videos")),
            Path(os.path.expanduser("~/Pictures")),
        ]
        exclude_dirs = {'node_modules', '.git', 'venv', 'env', '__pycache__', 'dist', 'build',
                        '.venv', '.cache', '.npm', 'AppData', 'sivi_whatsapp_data'}
        max_depth = 4

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('BEGIN TRANSACTION')
                # Clear old index to prevent stale files
                conn.execute('DELETE FROM files')
                
                for search_dir in search_dirs:
                    if not search_dir.exists(): continue
                    for root, dirs, files in os.walk(search_dir):
                        depth = len(Path(root).relative_to(search_dir).parts)
                        if depth >= max_depth:
                            dirs.clear()
                            continue
                        dirs[:] = [d for d in dirs if d not in exclude_dirs]
                        
                        # Bulk insert
                        rows = [(os.path.join(root, f), f, f.lower()) for f in files]
                        conn.executemany('INSERT OR IGNORE INTO files (path, name, lower_name) VALUES (?, ?, ?)', rows)
                conn.execute('COMMIT')
            print("[Sivi] Background File Indexer finished successfully.")
        except Exception as e:
            print(f"[Sivi] File Indexer error: {e}")

    def find_file(self, name: str) -> str:
        print(f" Searching for: {name} (via SQLite Index)")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT path FROM files WHERE lower_name LIKE ? LIMIT 10", 
                    (f"%{name.lower()}%",)
                )
                results = [row[0] for row in cursor.fetchall()]
        except Exception:
            return "File database is currently indexing, please wait..."

        if results:
            found = ", ".join(os.path.basename(r) for r in results)
            return f"Found {len(results)} file(s): {found}"
        
        # Fallback if index is building or file not found
        return f"No files matching '{name}' found in the index."

    def list_files(self, folder_name: str = None) -> str:
        if not folder_name:
            folder_name = "desktop"
        
        target = self.desktop
        if "document" in folder_name.lower():
            target = self.documents
        elif "download" in folder_name.lower():
            target = self.downloads
            
        if not target.exists():
            return f"Could not find {folder_name} folder."
            
        try:
            files = [f.name for f in target.iterdir() if f.is_file() and not f.name.startswith('.')]
            if files:
                return f"Files in {folder_name}: " + ", ".join(files[:10]) + (f" and {len(files)-10} more." if len(files) > 10 else ".")
            return f"{folder_name} is empty."
        except Exception as e:
            return f"Could not read {folder_name}."

    def create_file(self, name: str, folder: str = "desktop") -> str:
        target = self.desktop
        if folder == "documents": target = self.documents
        elif folder == "downloads": target = self.downloads
        
        file_path = target / name
        try:
            file_path.touch()
            # Immediately add to index
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('INSERT OR IGNORE INTO files (path, name, lower_name) VALUES (?, ?, ?)', 
                           (str(file_path), name, name.lower()))
            return f"Created file '{name}' on {folder}."
        except Exception as e:
            return f"Could not create file: {e}"

    def delete_file(self, name: str) -> str:
        for search_dir in [self.desktop, self.documents, self.downloads]:
            file_path = search_dir / name
            if file_path.exists() and file_path.is_file():
                try:
                    file_path.unlink()
                    # Remove from index
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute('DELETE FROM files WHERE path = ?', (str(file_path),))
                    return f"Deleted file '{name}'."
                except Exception as e:
                    return f"Could not delete file '{name}': {e}"
        return f"File '{name}' not found on Desktop, Documents, or Downloads."

    def create_folder(self, name: str, folder: str = "desktop") -> str:
        target = self.desktop
        if folder == "documents": target = self.documents
        elif folder == "downloads": target = self.downloads
        
        folder_path = target / name
        try:
            folder_path.mkdir(exist_ok=True)
            return f"Created folder '{name}' on {folder}."
        except Exception as e:
            return f"Could not create folder: {e}"

    def delete_folder(self, name: str) -> str:
        for search_dir in [self.desktop, self.documents, self.downloads]:
            folder_path = search_dir / name
            if folder_path.exists() and folder_path.is_dir():
                try:
                    shutil.rmtree(folder_path)
                    return f"Deleted folder '{name}'."
                except Exception as e:
                    return f"Could not delete folder '{name}': {e}"
        return f"Folder '{name}' not found."

    def open_file(self, name: str) -> str:
        path = self._resolve_path(name)
        if path.exists():
            if sys.platform == "darwin":
                subprocess.run(["open", str(path)])
            else:
                os.startfile(str(path))
            return f"Opening {name}."
        return f"File '{name}' not found."


file_manager = FileManager()
