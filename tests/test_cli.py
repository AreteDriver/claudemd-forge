"""Tests for the CLI interface."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from claudemd_forge.cli import app

runner = CliRunner()


def _normalized(output: str) -> str:
    """Collapse whitespace for assertion matching (rich wraps long lines)."""
    return " ".join(output.split())


class TestGenerate:
    def test_generate_creates_file(self, tmp_project: Path) -> None:
        result = runner.invoke(app, ["generate", str(tmp_project), "--quiet"])
        assert result.exit_code == 0
        assert (tmp_project / "CLAUDE.md").exists()

    def test_generate_refuses_overwrite(self, tmp_project: Path) -> None:
        (tmp_project / "CLAUDE.md").write_text("# existing")
        result = runner.invoke(app, ["generate", str(tmp_project)])
        assert result.exit_code == 1
        assert "already exists" in _normalized(result.output)

    def test_generate_force_overwrites(self, tmp_project: Path) -> None:
        (tmp_project / "CLAUDE.md").write_text("# old")
        result = runner.invoke(app, ["generate", str(tmp_project), "--force", "--quiet"])
        assert result.exit_code == 0
        content = (tmp_project / "CLAUDE.md").read_text()
        assert "# CLAUDE.md" in content
        assert content != "# old"

    def test_generate_quiet_suppresses_output(self, tmp_project: Path) -> None:
        result = runner.invoke(app, ["generate", str(tmp_project), "--quiet"])
        assert result.exit_code == 0
        assert "ClaudeMD Forge" not in result.output

    def test_generate_invalid_path(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate", str(tmp_path / "nonexistent")])
        assert result.exit_code == 1
        assert "not a directory" in result.output

    def test_generate_custom_output(self, tmp_project: Path) -> None:
        out = tmp_project / "docs" / "CLAUDE.md"
        out.parent.mkdir(exist_ok=True)
        result = runner.invoke(app, ["generate", str(tmp_project), "-o", str(out), "--quiet"])
        assert result.exit_code == 0
        assert out.exists()

    def test_generate_content_has_python(self, tmp_project: Path) -> None:
        result = runner.invoke(app, ["generate", str(tmp_project), "--quiet"])
        assert result.exit_code == 0
        content = (tmp_project / "CLAUDE.md").read_text()
        assert "Python" in content


class TestAudit:
    def test_audit_minimal_claude_md(self, tmp_project: Path) -> None:
        (tmp_project / "CLAUDE.md").write_text("# CLAUDE.md\n\nJust a title.\n")
        result = runner.invoke(app, ["audit", str(tmp_project / "CLAUDE.md")])
        # Should report missing sections.
        assert "Missing" in result.output or "missing" in result.output.lower()

    def test_audit_missing_file(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["audit", str(tmp_path / "CLAUDE.md")])
        assert result.exit_code == 1
        assert "not a file" in _normalized(result.output)

    def test_audit_verbose_shows_suggestions(self, tmp_project: Path) -> None:
        (tmp_project / "CLAUDE.md").write_text("# CLAUDE.md\n")
        result = runner.invoke(app, ["audit", str(tmp_project / "CLAUDE.md"), "-v"])
        # With verbose, should show suggestions.
        assert "Score" in result.output


class TestPresets:
    def test_presets_lists_available(self) -> None:
        result = runner.invoke(app, ["presets"])
        assert result.exit_code == 0
        assert "default" in result.output.lower() or "Default" in result.output

    def test_frameworks_lists_available(self) -> None:
        result = runner.invoke(app, ["frameworks"])
        assert result.exit_code == 0
        assert "FastAPI" in result.output or "fastapi" in result.output


class TestHelp:
    def test_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Generate and audit" in result.output

    def test_generate_help(self) -> None:
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "project root" in result.output.lower()

    def test_audit_help(self) -> None:
        result = runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        assert "CLAUDE.md" in result.output

    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
