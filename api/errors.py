class ScrapperError(Exception):
    """Base exception class for all scrappers."""


class PaginationError(ScrapperError):
    """Raise while there is a error related pagination."""
