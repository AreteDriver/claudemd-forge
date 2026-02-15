"""Codebase scanner that walks a project directory and produces a ProjectStructure."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

from claudemd_forge.config import CONFIG_LANGUAGES, LANGUAGE_EXTENSIONS
from claudemd_forge.exceptions import ScanError
from claudemd_forge.models import FileInfo, ForgeConfig, ProjectStructure

logger = logging.getLogger(__name__)

# Size of chunk for binary detection and line counting.
_READ_CHUNK = 8192


class CodebaseScanner:
    """Walks a project directory and produces a structured inventory."""

    def __init__(self, config: ForgeConfig) -> None:
        self.config = config
        self._seen_real_paths: set[Path] = set()

    def scan(self) -> ProjectStructure:
        """Main entry point. Returns complete project structure."""
        root = self.config.root_path.resolve()
        if not root.is_dir():
            raise ScanError(f"Project root is not a directory: {root}")

        files: list[FileInfo] = []
        directories: set[Path] = set()
        total_lines = 0

        for path in self._walk(root):
            if len(files) >= self.config.max_files:
                logger.warning("Reached max file limit (%d). Stopping scan.", self.config.max_files)
                break

            if path.is_dir():
                directories.add(path.relative_to(root))
                continue

            if not path.is_file():
                continue

            if not self._should_include(path, root):
                continue

            rel_path = path.relative_to(root)
            try:
                size = path.stat().st_size
            except OSError as e:
                logger.warning("Cannot stat %s: %s", rel_path, e)
                continue

            if size > self.config.max_file_size_kb * 1024:
                logger.debug("Skipping oversized file: %s (%d KB)", rel_path, size // 1024)
                continue

            line_count = self._count_lines(path)
            if line_count is not None:
                total_lines += line_count

            files.append(
                FileInfo(
                    path=rel_path,
                    extension=path.suffix.lower(),
                    size_bytes=size,
                    line_count=line_count,
                )
            )

        files.sort(key=lambda f: f.path)
        sorted_dirs = sorted(directories)

        languages = self._detect_languages(files)
        primary = self._get_primary_language(languages)

        return ProjectStructure(
            root=root,
            files=files,
            directories=sorted_dirs,
            total_files=len(files),
            total_lines=total_lines,
            primary_language=primary,
            languages=languages,
        )

    def _walk(self, root: Path) -> list[Path]:
        """Walk directory tree, respecting exclude patterns and symlink cycles."""
        results: list[Path] = []
        self._seen_real_paths = set()
        self._walk_recursive(root, root, results)
        return results

    def _walk_recursive(self, current: Path, root: Path, results: list[Path]) -> None:
        """Recursively walk directories."""
        try:
            real = current.resolve()
        except OSError as e:
            logger.warning("Cannot resolve path %s: %s", current, e)
            return

        if real in self._seen_real_paths:
            logger.debug("Symlink cycle detected at %s, skipping.", current)
            return
        self._seen_real_paths.add(real)

        try:
            entries = sorted(current.iterdir())
        except PermissionError:
            logger.warning("Permission denied: %s", current)
            return
        except OSError as e:
            logger.warning("Cannot read directory %s: %s", current, e)
            return

        for entry in entries:
            if entry.is_dir():
                rel_name = entry.name
                if self._is_excluded_dir(rel_name):
                    continue
                results.append(entry)
                self._walk_recursive(entry, root, results)
            else:
                results.append(entry)

    def _should_include(self, path: Path, root: Path) -> bool:
        """Check path against include/exclude patterns and size limits."""
        rel = path.relative_to(root)

        # Check if any parent directory is excluded.
        for part in rel.parts[:-1]:
            if self._is_excluded_dir(part):
                return False

        # Check filename against exclude patterns.
        name = path.name
        return all(not fnmatch.fnmatch(name, pattern) for pattern in self.config.exclude_patterns)

    def _is_excluded_dir(self, name: str) -> bool:
        """Check if a directory name matches an exclude pattern."""
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.config.exclude_patterns)

    def _detect_languages(self, files: list[FileInfo]) -> dict[str, int]:
        """Count files per language using LANGUAGE_EXTENSIONS mapping."""
        counts: dict[str, int] = {}
        for f in files:
            lang = LANGUAGE_EXTENSIONS.get(f.extension)
            if lang:
                counts[lang] = counts.get(lang, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def _count_lines(self, path: Path) -> int | None:
        """Count lines in a text file. Returns None for binary files.

        Uses chunked reads to avoid loading entire file into memory.
        """
        if self._is_binary(path):
            return None

        count = 0
        try:
            with path.open("rb") as f:
                while True:
                    chunk = f.read(_READ_CHUNK)
                    if not chunk:
                        break
                    count += chunk.count(b"\n")
        except (OSError, PermissionError) as e:
            logger.warning("Cannot read %s for line counting: %s", path, e)
            return None

        return count

    def _is_binary(self, path: Path) -> bool:
        """Check first 8KB for null bytes to detect binary files."""
        try:
            with path.open("rb") as f:
                chunk = f.read(_READ_CHUNK)
                return b"\x00" in chunk
        except (OSError, PermissionError):
            return True

    def _get_primary_language(self, languages: dict[str, int]) -> str | None:
        """Return language with most files, excluding config/markup languages."""
        candidates = {k: v for k, v in languages.items() if k not in CONFIG_LANGUAGES}
        if not candidates:
            return None
        return max(candidates, key=lambda k: candidates[k])
