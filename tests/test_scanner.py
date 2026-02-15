"""Tests for the codebase scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from claudemd_forge.exceptions import ScanError
from claudemd_forge.models import ForgeConfig
from claudemd_forge.scanner import CodebaseScanner


@pytest.fixture
def config_for(tmp_path: Path):
    """Factory fixture to create a ForgeConfig for a given path."""

    def _make(root: Path | None = None, **kwargs) -> ForgeConfig:
        return ForgeConfig(root_path=root or tmp_path, **kwargs)

    return _make


class TestScanBasics:
    def test_empty_directory(self, tmp_path: Path, config_for) -> None:
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.total_files == 0
        assert result.files == []
        assert result.total_lines == 0

    def test_invalid_root_raises(self, tmp_path: Path) -> None:
        config = ForgeConfig(root_path=tmp_path / "nonexistent")
        scanner = CodebaseScanner(config)
        with pytest.raises(ScanError, match="not a directory"):
            scanner.scan()

    def test_single_file(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "hello.py").write_text("print('hello')\n")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.total_files == 1
        assert result.files[0].extension == ".py"
        assert result.files[0].line_count == 1


class TestExclusion:
    def test_node_modules_excluded(self, tmp_path: Path, config_for) -> None:
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {};")
        (tmp_path / "app.js").write_text("const x = 1;")

        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.total_files == 1
        assert result.files[0].path == Path("app.js")

    def test_git_excluded(self, tmp_path: Path, config_for) -> None:
        git_dir = tmp_path / ".git" / "objects"
        git_dir.mkdir(parents=True)
        (git_dir / "abc123").write_bytes(b"\x00\x01\x02")
        (tmp_path / "main.py").write_text("x = 1\n")

        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        paths = [str(f.path) for f in result.files]
        assert "main.py" in paths
        assert not any(".git" in p for p in paths)

    def test_pycache_excluded(self, tmp_path: Path, config_for) -> None:
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "mod.cpython-312.pyc").write_bytes(b"\x00\x01")
        (tmp_path / "mod.py").write_text("x = 1\n")

        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.total_files == 1


class TestBinaryDetection:
    def test_binary_file_detected(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.total_files == 1
        assert result.files[0].line_count is None

    def test_text_file_not_binary(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "readme.md").write_text("# Hello\n\nWorld\n")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.files[0].line_count == 3


class TestLanguageDetection:
    def test_python_detected(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "app.py").write_text("x = 1\n")
        (tmp_path / "utils.py").write_text("y = 2\n")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.languages.get("Python") == 2

    def test_typescript_detected(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "app.ts").write_text("const x = 1;")
        (tmp_path / "comp.tsx").write_text("export const C = () => null;")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.languages.get("TypeScript") == 2

    def test_rust_detected(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "main.rs").write_text("fn main() {}\n")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.languages.get("Rust") == 1

    def test_primary_language(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        (tmp_path / "c.ts").write_text("const z = 3;")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.primary_language == "Python"

    def test_primary_language_excludes_config(self, tmp_path: Path, config_for) -> None:
        """HTML/CSS shouldn't be primary even if they have more files."""
        (tmp_path / "a.html").write_text("<html></html>")
        (tmp_path / "b.html").write_text("<html></html>")
        (tmp_path / "c.css").write_text("body {}")
        (tmp_path / "app.py").write_text("x = 1\n")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.primary_language == "Python"


class TestFileSizeLimit:
    def test_oversized_file_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "big.py").write_text("x" * (600 * 1024))  # 600KB
        (tmp_path / "small.py").write_text("y = 1\n")
        config = ForgeConfig(root_path=tmp_path, max_file_size_kb=500)
        scanner = CodebaseScanner(config)
        result = scanner.scan()
        assert result.total_files == 1
        assert result.files[0].path == Path("small.py")


class TestLineCount:
    def test_accurate_count(self, tmp_path: Path, config_for) -> None:
        content = "\n".join(f"line {i}" for i in range(100)) + "\n"
        (tmp_path / "code.py").write_text(content)
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.files[0].line_count == 100
        assert result.total_lines == 100

    def test_empty_file(self, tmp_path: Path, config_for) -> None:
        (tmp_path / "empty.py").write_text("")
        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        assert result.files[0].line_count == 0


class TestSymlinks:
    def test_symlink_cycle_no_infinite_loop(self, tmp_path: Path, config_for) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "file.py").write_text("x = 1\n")
        link = tmp_path / "link_to_sub"
        link.symlink_to(subdir)

        scanner = CodebaseScanner(config_for())
        result = scanner.scan()
        # Should find the file but not loop
        py_files = [f for f in result.files if f.extension == ".py"]
        assert len(py_files) >= 1


class TestPermissions:
    def test_permission_error_handled(self, tmp_path: Path, config_for) -> None:
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        (restricted / "secret.py").write_text("x = 1\n")
        restricted.chmod(0o000)

        try:
            scanner = CodebaseScanner(config_for())
            result = scanner.scan()  # should not crash
            # The restricted dir's files should be skipped
            assert all("restricted" not in str(f.path) for f in result.files)
        finally:
            restricted.chmod(0o755)


class TestMaxFiles:
    def test_max_files_limit(self, tmp_path: Path) -> None:
        for i in range(20):
            (tmp_path / f"file_{i}.py").write_text(f"x = {i}\n")
        config = ForgeConfig(root_path=tmp_path, max_files=10)
        scanner = CodebaseScanner(config)
        result = scanner.scan()
        assert result.total_files == 10


class TestDogfood:
    def test_scan_self(self) -> None:
        """Scanner should work on the claudemd-forge project itself."""
        root = Path(__file__).parent.parent
        config = ForgeConfig(root_path=root)
        scanner = CodebaseScanner(config)
        result = scanner.scan()
        assert result.total_files > 0
        assert "Python" in result.languages
        assert result.primary_language == "Python"
