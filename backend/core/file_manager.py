"""
SIVI AI -- File Manager Module
Voice-controlled file and folder operations.

Advanced features:
  - Background SQLite indexer with recency scoring (modified_at)
  - Extension-aware smart search (e.g. "find excel file" -> .xlsx only)
  - Periodic re-indexing every 10 minutes (no stale data)
  - Immediate index updates on create/delete
  - Safe deletion with system-path guards
"""

import os
import sys
import shutil
import sqlite3
import subprocess
import threading
from pathlib import Path
from typing import Optional


# ── Extension hint mapping ────────────────────────────────────────────────────
# When a user says "find my pdf report", we filter by .pdf extension.
EXT_HINTS: dict[str, list[str]] = {
    "pdf":        [".pdf"],
    "excel":      [".xlsx", ".xls", ".csv"],
    "word":       [".docx", ".doc"],
    "powerpoint": [".pptx", ".ppt"],
    "image":      [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
    "photo":      [".jpg", ".jpeg", ".png", ".heic", ".raw"],
    "video":      [".mp4", ".mov", ".avi", ".mkv", ".webm"],
    "audio":      [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "zip":        [".zip", ".rar", ".7z", ".tar", ".gz"],
    "code":       [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs"],
    "text":       [".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml"],
    "notebook":   [".ipynb"],
    "shortcut":   [".lnk", ".url"],
}

# Directories to exclude from indexing
EXCLUDE_DIRS = {
    "node_modules", ".git", "venv", "env", "__pycache__", "dist", "build",
    ".venv", ".cache", ".npm", "AppData", "sivi_whatsapp_data", "$Recycle.Bin",
    "System Volume Information", "Windows", "Program Files", "Program Files (x86)",
}

MAX_DEPTH = 4       # Max directory depth to scan
REINDEX_EVERY = 600  # Re-index every 10 minutes (600 seconds)


class FileManager:
    def __init__(self):
        self.desktop   = Path(os.path.expanduser("~/Desktop"))
        self.documents = Path(os.path.expanduser("~/Documents"))
        self.downloads = Path(os.path.expanduser("~/Downloads"))
        self.music     = Path(os.path.expanduser("~/Music"))
        self.videos    = Path(os.path.expanduser("~/Videos"))
        self.pictures  = Path(os.path.expanduser("~/Pictures"))

        self.db_path = Path(os.path.expanduser("~/.sivi_files.db"))
        self._db_lock = threading.Lock()
        self._indexing = False

        self._init_db()

        # Launch background indexer
        self._start_indexer()

    # ── Database Setup ────────────────────────────────────────────────────────

    def _init_db(self):
        """Create the SQLite schema with indexes for fast queries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path       TEXT PRIMARY KEY,
                    name       TEXT NOT NULL,
                    lower_name TEXT NOT NULL,
                    ext        TEXT NOT NULL DEFAULT '',
                    modified_at REAL NOT NULL DEFAULT 0
                )
            """)
            # Covering indexes for the two most common query patterns
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lower_name ON files(lower_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ext ON files(ext)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_modified ON files(modified_at DESC)")

    # ── Indexer ───────────────────────────────────────────────────────────────

    def _start_indexer(self):
        """Start the background indexer thread and schedule re-indexing."""
        # Delay the first indexing run by 10 seconds to allow the server to boot smoothly
        timer = threading.Timer(10.0, self._indexer_worker)
        timer.daemon = True
        timer.start()

    def _schedule_reindex(self):
        """Schedule the next re-index after REINDEX_EVERY seconds."""
        timer = threading.Timer(REINDEX_EVERY, self._reindex)
        timer.daemon = True
        timer.start()

    def _reindex(self):
        """Periodic re-index -- runs every 10 minutes to catch new files."""
        print("[Sivi FileIndexer] Starting periodic re-index...")
        self._indexer_worker()

    def _indexer_worker(self):
        """Walk user directories and rebuild the SQLite file index."""
        if self._indexing:
            return  # Already running
        self._indexing = True
        print("[Sivi FileIndexer] Building file index...")

        search_dirs = [
            self.desktop, self.documents, self.downloads,
            self.music, self.videos, self.pictures,
        ]

        rows: list[tuple] = []
        try:
            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue
                for root, dirs, files in os.walk(str(search_dir)):
                    # Depth check
                    try:
                        depth = len(Path(root).relative_to(search_dir).parts)
                    except ValueError:
                        depth = MAX_DEPTH
                    if depth >= MAX_DEPTH:
                        dirs.clear()
                        continue
                    # Prune excluded dirs
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

                    for f in files:
                        if f.startswith("."):
                            continue
                        full_path = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(full_path)
                        except OSError:
                            mtime = 0.0
                        ext = Path(f).suffix.lower()
                        rows.append((full_path, f, f.lower(), ext, mtime))
                    
                    for d in dirs:
                        full_path = os.path.join(root, d)
                        try:
                            mtime = os.path.getmtime(full_path)
                        except OSError:
                            mtime = 0.0
                        rows.append((full_path, d, d.lower(), 'folder', mtime))

            with self._db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("BEGIN TRANSACTION")
                    conn.execute("DELETE FROM files")
                    conn.executemany(
                        "INSERT OR IGNORE INTO files (path, name, lower_name, ext, modified_at) VALUES (?,?,?,?,?)",
                        rows,
                    )
                    conn.execute("COMMIT")

            print(f"[Sivi FileIndexer] Indexed {len(rows)} files.")
        except Exception as e:
            print(f"[Sivi FileIndexer] Error: {e}")
        finally:
            self._indexing = False
            self._schedule_reindex()  # Schedule next re-index

    # ── Smart Search ──────────────────────────────────────────────────────────

    def _extract_ext_filter(self, query: str) -> list[str]:
        """
        Detect extension hints in the search query.
        'find my pdf report' -> ['.pdf']
        'find excel file'    -> ['.xlsx', '.xls', '.csv']
        """
        q_lower = query.lower()
        for hint, exts in EXT_HINTS.items():
            if hint in q_lower:
                return exts
        return []

    def _clean_query(self, query: str) -> str:
        """Remove extension hint words from query so they don't corrupt the name search."""
        q = query.lower()
        for hint in EXT_HINTS:
            q = q.replace(hint, "").strip()
        # Remove common filler words
        for filler in ["file", "folder", "directory", "my", "the", "a", "an", "find", "search", "for", "named", "called", "open", "show"]:
            q = q.replace(f" {filler} ", " ").strip()
            if q.startswith(filler + " "):
                q = q[len(filler):].strip()
            if q.endswith(" " + filler):
                q = q[:-len(filler)].strip()
        return q.strip()

    def find_file(self, query: str, limit: int = 10) -> str:
        """
        Smart file search against the SQLite index.
        - Extension-aware: 'find excel file report' -> searches .xlsx files named *report*
        - Recency-sorted: most recently modified files first
        - Gracefully handles the indexer still building
        """
        if not query or not query.strip():
            return "Please specify a file name to search for."

        ext_filter = self._extract_ext_filter(query)
        clean_name = self._clean_query(query)
        tokens = clean_name.split() if clean_name else []

        try:
            with self._db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    where_clauses = []
                    params = []

                    if tokens:
                        for t in tokens:
                            where_clauses.append("lower_name LIKE ?")
                            params.append(f"%{t}%")
                    else:
                        where_clauses.append("1=1")

                    if ext_filter:
                        placeholders = ",".join("?" * len(ext_filter))
                        where_clauses.append(f"ext IN ({placeholders})")
                        params.extend(ext_filter)
                    else:
                        # Allow both files and folders if no extension specified
                        pass

                    where_sql = " AND ".join(where_clauses)
                    sql = (
                        f"SELECT path, name, modified_at FROM files "
                        f"WHERE {where_sql} "
                        f"ORDER BY modified_at DESC LIMIT ?"
                    )
                    params.append(limit)

                    cursor = conn.execute(sql, params)
                    results = cursor.fetchall()

        except Exception as e:
            return "File index is currently building, please try again in a moment."

        if not results:
            # If we searched with extension filter and found nothing, retry without
            if ext_filter:
                return self.find_file(clean_name or query, limit)
            return f"No files matching '{query}' found."

        if len(results) == 1:
            path, name, _ = results[0]
            return f"Found: {name}\nLocation: {path}"

        names = [r[1] for r in results]
        return f"Found {len(results)} file(s): {', '.join(names)}"

    def get_file_path(self, query: str) -> Optional[str]:
        """Return the full path of the best matching file, or None."""
        ext_filter = self._extract_ext_filter(query)
        clean_name = self._clean_query(query)
        tokens = clean_name.split() if clean_name else []
        if not tokens: tokens = query.lower().split()

        try:
            with self._db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    where_clauses = []
                    params = []

                    for t in tokens:
                        where_clauses.append("lower_name LIKE ?")
                        params.append(f"%{t}%")

                    if ext_filter:
                        placeholders = ",".join("?" * len(ext_filter))
                        where_clauses.append(f"ext IN ({placeholders})")
                        params.extend(ext_filter)

                    where_sql = " AND ".join(where_clauses)
                    sql = f"SELECT path FROM files WHERE {where_sql} ORDER BY modified_at DESC LIMIT 1"
                    
                    row = conn.execute(sql, params).fetchone()
                    return row[0] if row else None
        except Exception:
            return None

    # ── Index Live Updates ────────────────────────────────────────────────────

    def _index_add(self, path: str, name: str):
        """Immediately add a new file to the index after creation."""
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0.0
        ext = Path(name).suffix.lower()
        try:
            with self._db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO files (path, name, lower_name, ext, modified_at) VALUES (?,?,?,?,?)",
                        (path, name, name.lower(), ext, mtime),
                    )
        except Exception:
            pass

    def _index_remove(self, path: str):
        """Immediately remove a deleted file from the index."""
        try:
            with self._db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM files WHERE path = ?", (path,))
        except Exception:
            pass

    # ── Path Resolution ───────────────────────────────────────────────────────

    def _resolve_path(self, name: str) -> Path:
        """Resolve a bare file/folder name to an absolute path, defaulting to Desktop."""
        name_lower = name.lower().strip()
        if name_lower in ("desktop",):       return self.desktop
        if name_lower in ("documents", "docs"): return self.documents
        if name_lower in ("downloads",):     return self.downloads
        if name_lower in ("music",):         return self.music
        if name_lower in ("videos",):        return self.videos
        if name_lower in ("pictures", "photos"): return self.pictures

        p = Path(name)
        if p.is_absolute():
            return p
        # Bare name -- default to Desktop
        if str(p.parent) == ".":
            return self.desktop / name
        return p

    # ── File Operations ───────────────────────────────────────────────────────

    def create_file(self, name: str, folder: str = "desktop") -> str:
        """Create a new file and immediately add it to the index."""
        target = self._folder_to_path(folder)
        path = target / name
        try:
            path.touch(exist_ok=True)
            self._index_add(str(path), name)
            return f"Created file '{name}' in {folder}."
        except Exception as e:
            return f"Could not create file '{name}': {e}"

    def delete_file(self, name: str) -> str:
        """
        Delete a file by name. Searches Desktop, Documents, Downloads.
        Protected against deleting system-critical paths.
        """
        PROTECTED = ["C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"]
        # First try to find the exact path via index
        found_path = self.get_file_path(name)
        if found_path:
            target = Path(found_path)
        else:
            # Fallback: check common folders
            target = None
            for d in [self.desktop, self.documents, self.downloads]:
                candidate = d / name
                if candidate.exists() and candidate.is_file():
                    target = candidate
                    break

        if target is None:
            return f"File '{name}' not found."

        # Safety check
        for prot in PROTECTED:
            if str(target).startswith(prot) and len(str(target)) < len(prot) + 10:
                return "Cannot delete system-protected paths."

        try:
            target.unlink()
            self._index_remove(str(target))
            return f"Deleted '{target.name}'."
        except Exception as e:
            return f"Could not delete '{name}': {e}"

    def open_file(self, name: str) -> str:
        """Open a file by name. Uses index to locate it first."""
        path_str = self.get_file_path(name)
        if path_str:
            path = Path(path_str)
        else:
            path = self._resolve_path(name)

        if path.exists():
            try:
                if sys.platform == "win32":
                    os.startfile(str(path))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(path)])
                else:
                    subprocess.run(["xdg-open", str(path)])
                return f"Opening '{path.name}'."
            except Exception as e:
                return f"Could not open '{name}': {e}"
        return f"File '{name}' not found."

    # ── Folder Operations ─────────────────────────────────────────────────────

    def create_folder(self, name: str, folder: str = "desktop") -> str:
        target = self._folder_to_path(folder)
        path = target / name
        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"Created folder '{name}' in {folder}."
        except Exception as e:
            return f"Could not create folder '{name}': {e}"

    def delete_folder(self, name: str) -> str:
        for d in [self.desktop, self.documents, self.downloads]:
            path = d / name
            if path.exists() and path.is_dir():
                try:
                    shutil.rmtree(str(path))
                    return f"Deleted folder '{name}'."
                except Exception as e:
                    return f"Could not delete folder '{name}': {e}"
        return f"Folder '{name}' not found."

    def list_files(self, folder_name: str = "desktop") -> str:
        """List files in a known folder."""
        target = self._folder_to_path(folder_name)
        if not target.exists():
            return f"Folder '{folder_name}' not found."
        try:
            items = sorted(
                [f for f in target.iterdir() if f.is_file() and not f.name.startswith(".")],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if not items:
                return f"'{folder_name}' is empty."
            names = [f.name for f in items[:15]]
            suffix = f" and {len(items) - 15} more." if len(items) > 15 else "."
            return f"Files in {folder_name}: {', '.join(names)}{suffix}"
        except Exception as e:
            return f"Could not read '{folder_name}': {e}"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _folder_to_path(self, folder: str) -> Path:
        """Map a folder name string to a Path object."""
        folder_lower = (folder or "desktop").lower().strip()
        mapping = {
            "desktop":   self.desktop,
            "documents": self.documents,
            "docs":      self.documents,
            "downloads": self.downloads,
            "music":     self.music,
            "videos":    self.videos,
            "pictures":  self.pictures,
            "photos":    self.pictures,
        }
        return mapping.get(folder_lower, self.desktop)

    @property
    def index_size(self) -> int:
        """Return the number of files currently indexed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        except Exception:
            return 0


file_manager = FileManager()
