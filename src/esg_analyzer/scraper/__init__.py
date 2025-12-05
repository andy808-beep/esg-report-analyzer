"""Web scraping modules for SEC EDGAR and document downloading."""

from esg_analyzer.scraper.downloader import Downloader, DownloadResult
from esg_analyzer.scraper.edgar import EdgarClient, get_edgar_client

__all__ = [
    "EdgarClient",
    "get_edgar_client",
    "Downloader",
    "DownloadResult",
]
