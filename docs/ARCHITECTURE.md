# ClaudeMD Forge — Architecture

## Data Flow

```
Project Directory
       │
       ▼
┌─────────────┐
│   Scanner   │──── Walks filesystem, catalogs files
└─────────────┘
       │
       ▼
 ProjectStructure (Pydantic model)
       │
       ├──► LanguageAnalyzer ──► AnalysisResult (tech stack)
       ├──► PatternAnalyzer  ──► AnalysisResult (conventions)
       ├──► CommandAnalyzer  ──► AnalysisResult (CLI commands)
       └──► DomainAnalyzer   ──► AnalysisResult (terminology)
                │
                ▼
        list[AnalysisResult]
                │
                ▼
       ┌────────────────┐
       │   Composer      │──── Assembles sections via templates
       └────────────────┘
                │
                ▼
         CLAUDE.md (string)
                │
                ▼
          Written to disk
```

## Audit Flow

```
Existing CLAUDE.md + ProjectStructure + list[AnalysisResult]
       │
       ▼
┌─────────────┐
│   Auditor   │
└─────────────┘
       │
       ├──► Section coverage checks
       ├──► Accuracy checks (CLAUDE.md vs reality)
       ├──► Anti-pattern detection
       ├──► Specificity checks
       └──► Freshness checks
                │
                ▼
         AuditReport (score + findings)
```

## Design Principles

1. **No LLM calls**: Everything is static analysis + templates. Fast, free, deterministic.
2. **Pydantic everywhere**: All data flows through typed models. No raw dicts.
3. **Plugin analyzers**: Add new analyzers without modifying existing code.
4. **Template composition**: Each section is independent. Include/exclude via config.
5. **Dogfood-first**: The tool must work well on its own codebase.

## Extension Points

- **Custom analyzers**: Implement `analyze(structure, config) -> AnalysisResult`
- **Custom templates**: Add Jinja2 templates for new sections
- **Framework presets**: Add entries to `FRAMEWORK_PRESETS` dict
- **Preset packs**: Add entries to `PRESET_PACKS` dict

## Phase 2 (Future)

- FastAPI web endpoint for CI integration
- GitHub Action that runs on PR and comments audit results
- VS Code extension that regenerates CLAUDE.md on save
- Paid tier: team templates, custom rules, multi-repo scanning
