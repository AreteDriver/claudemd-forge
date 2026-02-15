"""CLAUDE.md auditor — evaluates existing files against best practices."""

from __future__ import annotations

import re

from claudemd_forge.models import (
    AnalysisResult,
    AuditFinding,
    AuditReport,
    ForgeConfig,
    ProjectStructure,
)

# Recommended sections and their severity if missing.
_REQUIRED_SECTIONS: dict[str, str] = {
    "Project Overview": "error",
    "Common Commands": "error",
    "Architecture": "error",
    "Coding Standards": "warning",
    "Anti-Patterns": "warning",
    "Dependencies": "info",
    "Git Conventions": "info",
    "Domain Context": "info",
}

_VAGUE_PHRASES = [
    "follow best practices",
    "use standard conventions",
    "write clean code",
    "keep it simple",
    "be consistent",
    "use appropriate",
    "handle errors properly",
]


class ClaudeMdAuditor:
    """Audits an existing CLAUDE.md against the actual codebase and best practices."""

    def __init__(self, config: ForgeConfig) -> None:
        self.config = config

    def audit(
        self,
        claude_md_content: str,
        structure: ProjectStructure,
        analyses: list[AnalysisResult],
    ) -> AuditReport:
        """Full audit producing scored report with findings."""
        findings: list[AuditFinding] = []

        findings.extend(self._check_section_coverage(claude_md_content))
        findings.extend(self._check_accuracy(claude_md_content, structure, analyses))
        findings.extend(self._check_anti_patterns(claude_md_content))
        findings.extend(self._check_specificity(claude_md_content))
        findings.extend(self._check_freshness(claude_md_content, structure))

        # Count present sections.
        section_count = sum(1 for name in _REQUIRED_SECTIONS if f"## {name}" in claude_md_content)
        missing = [name for name in _REQUIRED_SECTIONS if f"## {name}" not in claude_md_content]

        score = self._calculate_score(findings, section_count)
        recommendations = self._generate_recommendations(findings, missing)

        return AuditReport(
            score=score,
            findings=findings,
            missing_sections=missing,
            recommendations=recommendations,
        )

    def _check_section_coverage(self, content: str) -> list[AuditFinding]:
        """Check which recommended sections are present/missing."""
        findings: list[AuditFinding] = []
        for section_name, severity in _REQUIRED_SECTIONS.items():
            if f"## {section_name}" not in content:
                # Also check for close variants.
                lower_content = content.lower()
                lower_name = section_name.lower()
                if lower_name not in lower_content:
                    findings.append(
                        AuditFinding(
                            severity=severity,  # type: ignore[arg-type]
                            category="coverage",
                            message=f'Missing "{section_name}" section',
                            suggestion=f"Add a ## {section_name} section with relevant content",
                        )
                    )
        return findings

    def _check_accuracy(
        self,
        content: str,
        structure: ProjectStructure,
        analyses: list[AnalysisResult],
    ) -> list[AuditFinding]:
        """Compare CLAUDE.md claims against actual codebase state."""
        findings: list[AuditFinding] = []
        lower_content = content.lower()

        # Check "greenfield" claim on large projects.
        if "greenfield" in lower_content and structure.total_files > 50:
            findings.append(
                AuditFinding(
                    severity="error",
                    category="accuracy",
                    message=(
                        f'Says "greenfield" but project has {structure.total_files} source files'
                    ),
                    suggestion="Update the project phase description",
                )
            )

        # Check framework claims vs reality.
        for analysis in analyses:
            if analysis.category != "language":
                continue
            detected_frameworks = set(analysis.findings.get("frameworks", []))

            # Look for framework names mentioned in CLAUDE.md.
            common_frameworks = {
                "react",
                "vue",
                "angular",
                "django",
                "flask",
                "fastapi",
                "express",
                "nextjs",
                "svelte",
                "spring",
            }
            for fw in common_frameworks:
                if fw in lower_content and fw not in detected_frameworks:
                    findings.append(
                        AuditFinding(
                            severity="error",
                            category="accuracy",
                            message=f'Lists "{fw}" but it was not detected in dependencies',
                            suggestion=f"Remove {fw} reference or add it to dependencies",
                        )
                    )

        return findings

    def _check_anti_patterns(self, content: str) -> list[AuditFinding]:
        """Check for common CLAUDE.md anti-patterns."""
        findings: list[AuditFinding] = []
        lines = content.splitlines()
        line_count = len(lines)

        if line_count > 500:
            findings.append(
                AuditFinding(
                    severity="warning",
                    category="anti_pattern",
                    message=f"CLAUDE.md is {line_count} lines — too long, agents lose context",
                    suggestion="Trim to under 300 lines, focus on essentials",
                )
            )

        if line_count < 20:
            findings.append(
                AuditFinding(
                    severity="warning",
                    category="anti_pattern",
                    message=f"CLAUDE.md is only {line_count} lines — too short for useful context",
                    suggestion="Add more sections: overview, commands, coding standards",
                )
            )

        # Check for TODO/FIXME.
        for line in lines:
            if re.search(r"\bTODO\b|\bFIXME\b", line):
                findings.append(
                    AuditFinding(
                        severity="warning",
                        category="anti_pattern",
                        message="Contains TODO/FIXME items (stale planning artifacts)",
                        suggestion="Resolve or remove TODO items from CLAUDE.md",
                    )
                )
                break

        # Check for conversation fragments.
        conversation_markers = [
            "can you",
            "please help",
            "i want you to",
            "let me know",
            "sure, I",
            "here's what",
            "I'll help",
        ]
        lower_content = content.lower()
        for marker in conversation_markers:
            if marker in lower_content:
                findings.append(
                    AuditFinding(
                        severity="warning",
                        category="anti_pattern",
                        message="Contains conversation fragments (copy-paste from AI chat)",
                        suggestion="Use declarative style, not conversational prompts",
                    )
                )
                break

        # Check for first-person usage.
        first_person = re.findall(r"\b(I want|We use|I need|Our team|We have)\b", content)
        if first_person:
            findings.append(
                AuditFinding(
                    severity="info",
                    category="anti_pattern",
                    message="Uses first-person language instead of declarative style",
                    suggestion='Use declarative: "Use pytest" instead of "We use pytest"',
                )
            )

        # Check for unclosed code blocks.
        if content.count("```") % 2 != 0:
            findings.append(
                AuditFinding(
                    severity="info",
                    category="anti_pattern",
                    message="Contains unclosed code block (odd number of ``` markers)",
                    suggestion="Close all code blocks with matching ```",
                )
            )

        return findings

    def _check_specificity(self, content: str) -> list[AuditFinding]:
        """Check for vague/generic content that should be specific."""
        findings: list[AuditFinding] = []
        lower_content = content.lower()

        for phrase in _VAGUE_PHRASES:
            if phrase in lower_content:
                findings.append(
                    AuditFinding(
                        severity="warning",
                        category="specificity",
                        message=f'Contains vague phrase: "{phrase}"',
                        suggestion="Replace with specific, actionable instructions",
                    )
                )

        # Check if anti-patterns section exists but lacks code examples.
        if "## Anti-Patterns" in content or "## Anti-patterns" in content:
            # Find the anti-patterns section.
            anti_start = content.lower().find("## anti-pattern")
            if anti_start >= 0:
                # Find next section or end of file.
                next_section = content.find("\n## ", anti_start + 1)
                anti_section = (
                    content[anti_start:next_section] if next_section > 0 else content[anti_start:]
                )
                if "```" not in anti_section and "`" not in anti_section:
                    findings.append(
                        AuditFinding(
                            severity="info",
                            category="specificity",
                            message="Anti-patterns section lacks code examples",
                            suggestion="Add inline code or code blocks showing what NOT to do",
                        )
                    )

        # Check if commands section exists but has no actual commands.
        if "## Common Commands" in content or "## Commands" in content:
            cmd_start = content.lower().find("## common command")
            if cmd_start < 0:
                cmd_start = content.lower().find("## command")
            if cmd_start >= 0:
                next_section = content.find("\n## ", cmd_start + 1)
                cmd_section = (
                    content[cmd_start:next_section] if next_section > 0 else content[cmd_start:]
                )
                if "```" not in cmd_section:
                    findings.append(
                        AuditFinding(
                            severity="info",
                            category="specificity",
                            message="Commands section lacks actual command strings",
                            suggestion="Add code blocks with runnable commands",
                        )
                    )

        return findings

    def _check_freshness(self, content: str, structure: ProjectStructure) -> list[AuditFinding]:
        """Detect stale information."""
        findings: list[AuditFinding] = []

        # Check for references to files/directories that don't exist.
        existing_paths = {str(f.path) for f in structure.files}
        existing_dirs = {str(d) for d in structure.directories}
        all_existing = existing_paths | existing_dirs

        # Look for file path references in CLAUDE.md.
        path_refs = re.findall(r"`([a-zA-Z_./][a-zA-Z0-9_./\-]+)`", content)
        for ref in path_refs:
            # Skip things that look like commands or code.
            if " " in ref or ref.startswith(("pip", "npm", "cargo", "make", "git")):
                continue
            # Only check things that look like file paths.
            if (
                "/" in ref
                and ref not in all_existing
                and ("." in ref.split("/")[-1] or ref.endswith("/"))
            ):
                # Check if it's a real path reference (has extension or known dir).
                findings.append(
                    AuditFinding(
                        severity="warning",
                        category="freshness",
                        message=f"References path `{ref}` which doesn't exist in the project",
                        suggestion="Update or remove stale file references",
                    )
                )

        return findings

    def _calculate_score(self, findings: list[AuditFinding], section_count: int) -> int:
        """Score 0-100 based on findings severity and coverage."""
        base_score = 100

        # Deductions per finding.
        for f in findings:
            if f.severity == "error":
                base_score -= 15
            elif f.severity == "warning":
                base_score -= 5
            elif f.severity == "info":
                base_score -= 1

        # Section bonus.
        total_recommended = len(_REQUIRED_SECTIONS)
        section_bonus = int((section_count / total_recommended) * 20)

        final = base_score + section_bonus
        return max(0, min(100, final))

    def _generate_recommendations(
        self, findings: list[AuditFinding], missing_sections: list[str]
    ) -> list[str]:
        """Generate actionable recommendations."""
        recs: list[str] = []

        # Priority 1: Missing critical sections.
        critical_missing = [s for s in missing_sections if _REQUIRED_SECTIONS.get(s) == "error"]
        if critical_missing:
            recs.append(f"Add missing critical sections: {', '.join(critical_missing)}")

        # Priority 2: Accuracy issues.
        accuracy_errors = [
            f for f in findings if f.category == "accuracy" and f.severity == "error"
        ]
        if accuracy_errors:
            recs.append("Fix accuracy issues — CLAUDE.md doesn't match actual codebase")

        # Priority 3: Anti-patterns.
        anti_warnings = [f for f in findings if f.category == "anti_pattern"]
        if anti_warnings:
            recs.append("Clean up CLAUDE.md anti-patterns (TODOs, conversation fragments, etc.)")

        # Priority 4: Specificity.
        vague = [f for f in findings if f.category == "specificity"]
        if vague:
            recs.append("Replace vague instructions with specific, actionable guidance")

        if not recs:
            recs.append("CLAUDE.md is in good shape!")

        return recs
