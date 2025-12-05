"""Async document downloader with progress tracking."""

import asyncio
from collections.abc import Callable
from pathlib import Path

import httpx
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from esg_analyzer.analyzer.models import Filing
from esg_analyzer.config import get_settings


class DownloadResult:
    """Result of a download operation."""

    def __init__(
        self,
        url: str,
        filepath: Path | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        self.url = url
        self.filepath = filepath
        self.success = success
        self.error = error


class Downloader:
    """Async downloader for SEC filing documents.

    Features:
    - Concurrent downloads with configurable limit
    - Progress bar with rich
    - Automatic retry on failure
    - Caching (skip existing files)

    Example:
        async with Downloader() as downloader:
            results = await downloader.download_filings(filings, "./cache")
    """

    def __init__(
        self,
        user_agent: str | None = None,
        concurrency: int | None = None,
        max_retries: int | None = None,
        timeout: int | None = None,
    ) -> None:
        """Initialize downloader.

        Args:
            user_agent: User-Agent header (required by SEC)
            concurrency: Max concurrent downloads
            max_retries: Retry count on failure
            timeout: Request timeout in seconds
        """
        settings = get_settings()
        self.user_agent = user_agent or settings.edgar.user_agent
        self.concurrency = concurrency or settings.download.concurrency
        self.max_retries = max_retries or settings.download.max_retries
        self.timeout = timeout or settings.download.timeout
        self._client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None

    async def __aenter__(self) -> "Downloader":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=float(self.timeout),
            follow_redirects=True,
        )
        self._semaphore = asyncio.Semaphore(self.concurrency)
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._client is None:
            raise RuntimeError("Downloader must be used as async context manager")
        return self._client

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Get concurrency semaphore."""
        if self._semaphore is None:
            raise RuntimeError("Downloader must be used as async context manager")
        return self._semaphore

    async def download_file(
        self,
        url: str,
        output_path: Path,
        skip_existing: bool = True,
    ) -> DownloadResult:
        """Download a single file.

        Args:
            url: URL to download
            output_path: Path to save file
            skip_existing: Skip if file already exists

        Returns:
            DownloadResult with success status
        """
        if skip_existing and output_path.exists():
            return DownloadResult(url=url, filepath=output_path, success=True)

        async with self.semaphore:
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.get(url)
                    response.raise_for_status()

                    # Ensure parent directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Write content
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    return DownloadResult(url=url, filepath=output_path, success=True)

                except httpx.HTTPStatusError as e:
                    if attempt == self.max_retries - 1:
                        return DownloadResult(
                            url=url,
                            success=False,
                            error=f"HTTP {e.response.status_code}: {e}",
                        )
                    await asyncio.sleep(1 * (attempt + 1))  # Backoff

                except Exception as e:
                    if attempt == self.max_retries - 1:
                        return DownloadResult(url=url, success=False, error=str(e))
                    await asyncio.sleep(1 * (attempt + 1))

        return DownloadResult(url=url, success=False, error="Max retries exceeded")

    async def download_urls(
        self,
        urls: list[str],
        output_dir: Path,
        skip_existing: bool = True,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[DownloadResult]:
        """Download multiple URLs concurrently.

        Args:
            urls: List of URLs to download
            output_dir: Directory to save files
            skip_existing: Skip existing files
            progress_callback: Called with (completed, total) after each download

        Returns:
            List of DownloadResults
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        async def download_one(url: str, index: int) -> DownloadResult:
            # Extract filename from URL
            filename = url.split("/")[-1]
            output_path = output_dir / filename
            result = await self.download_file(url, output_path, skip_existing)
            if progress_callback:
                progress_callback(index + 1, len(urls))
            return result

        tasks = [download_one(url, i) for i, url in enumerate(urls)]
        return await asyncio.gather(*tasks)

    async def download_filings(
        self,
        filings: list[Filing],
        output_dir: Path | str,
        skip_existing: bool = True,
        show_progress: bool = True,
    ) -> dict[str, list[DownloadResult]]:
        """Download documents for multiple filings.

        Organizes downloads by company ticker/CIK and filing date.

        Args:
            filings: List of filings to download
            output_dir: Base output directory
            skip_existing: Skip existing files
            show_progress: Show progress bar

        Returns:
            Dict mapping filing accession numbers to download results
        """
        output_dir = Path(output_dir)
        results: dict[str, list[DownloadResult]] = {}

        if show_progress:
            progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
            )
        else:
            progress = None

        if progress:
            progress.start()
            task_id: TaskID = progress.add_task("Downloading filings...", total=len(filings))

        try:
            for filing in filings:
                # Create filing-specific directory
                company_id = filing.company.ticker or filing.company.cik
                filing_dir = output_dir / company_id / filing.accession_number_formatted

                # Get document URLs
                doc_urls = [str(url) for url in filing.document_urls]

                if doc_urls:
                    filing_results = await self.download_urls(
                        doc_urls,
                        filing_dir,
                        skip_existing=skip_existing,
                    )
                    results[filing.accession_number] = filing_results

                if progress:
                    progress.advance(task_id)

        finally:
            if progress:
                progress.stop()

        return results

    async def download_filing_primary_doc(
        self,
        filing: Filing,
        output_dir: Path | str,
        skip_existing: bool = True,
    ) -> DownloadResult | None:
        """Download only the primary document for a filing.

        Args:
            filing: Filing to download
            output_dir: Output directory
            skip_existing: Skip if exists

        Returns:
            DownloadResult or None if no primary doc
        """
        if not filing.primary_document:
            return None

        output_dir = Path(output_dir)
        company_id = filing.company.ticker or filing.company.cik

        # Build URL for primary document (documents are at www.sec.gov)
        cik = filing.company.cik.lstrip("0")  # Remove leading zeros
        accession = filing.accession_number_raw
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filing.primary_document}"
        )

        # Output path
        output_path = output_dir / company_id / f"{filing.accession_number_formatted}.pdf"
        if filing.primary_document.endswith(".htm"):
            output_path = output_path.with_suffix(".htm")

        return await self.download_file(doc_url, output_path, skip_existing)
