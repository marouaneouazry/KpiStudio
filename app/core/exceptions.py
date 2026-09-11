class AppError(Exception):
    """Base exception class for Mantis KPI Studio application."""
    pass

class AppConfigError(AppError):
    """Raised when an application configuration error occurs."""
    pass

class HolidayCalendarError(AppError):
    """Raised when a holiday calendar error or unvalidated status issue occurs."""
    pass

class ReportGenerationError(AppError):
    """Raised when an error occurs during KPI Excel or PPTX dashboard generation."""
    pass

class MantisAPIError(AppError):
    """Raised when an external Mantis API request fails or returns an invalid payload."""
    pass
