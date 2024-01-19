class ScrapperError(Exception):
    """Base exception class for all scrappers."""


class PaginationError(ScrapperError):
    """Raise while there is a error related pagination."""


class ParsingError(Exception):
    """Raise while there is error while parsing json or html."""
