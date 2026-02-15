"""Custom exceptions for ClaudeMD Forge."""


class ForgeError(Exception):
    """Base exception for all ClaudeMD Forge errors."""


class ScanError(ForgeError):
    """Raised when filesystem scanning encounters an unrecoverable error."""


class AnalysisError(ForgeError):
    """Raised when codebase analysis fails."""


class TemplateError(ForgeError):
    """Raised when template rendering fails."""
