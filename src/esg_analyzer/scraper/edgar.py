"""SEC EDGAR API client for discovering and fetching filings."""

import asyncio
import contextlib
import time
from datetime import date
from typing import Any

import httpx
from pydantic import HttpUrl

from esg_analyzer.analyzer.models import Company, Filing, FilingSearchResult
from esg_analyzer.config import get_settings


class RateLimiter:
    """Simple rate limiter for SEC's 10 requests/second limit."""

    def __init__(self, requests_per_second: int = 10) -> None:
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait if necessary to respect rate limit."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_request_time = time.monotonic()


class EdgarClient:
    """Client for SEC EDGAR API.

    Provides methods to search for filings, get company information,
    and retrieve filing documents.

    SEC EDGAR API requires a User-Agent header with contact information.
    Rate limit: 10 requests per second.

    Example:
        async with EdgarClient() as client:
            filings = await client.search_filings(form_type="10-K", year=2023)
            for filing in filings:
                docs = await client.get_filing_documents(filing)
    """

    # API data is at data.sec.gov, but documents are at www.sec.gov
    BASE_URL = "https://data.sec.gov"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    FULL_TEXT_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

    def __init__(
        self,
        user_agent: str | None = None,
        requests_per_second: int | None = None,
    ) -> None:
        """Initialize the EDGAR client.

        Args:
            user_agent: Required by SEC. Format: "AppName contact@email.com"
            requests_per_second: Rate limit (default: 10, SEC's limit)
        """
        settings = get_settings()
        self.user_agent = user_agent or settings.edgar.user_agent
        self.rate_limiter = RateLimiter(requests_per_second or settings.edgar.requests_per_second)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "EdgarClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=30.0,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, ensuring it's initialized."""
        if self._client is None:
            raise RuntimeError(
                "EdgarClient must be used as async context manager: "
                "async with EdgarClient() as client: ..."
            )
        return self._client

    async def _get(self, url: str) -> httpx.Response:
        """Make a rate-limited GET request."""
        await self.rate_limiter.acquire()
        response = await self.client.get(url)
        response.raise_for_status()
        return response

    async def _get_json(self, url: str) -> dict[str, Any]:
        """Make a rate-limited GET request and return JSON."""
        response = await self._get(url)
        return response.json()  # type: ignore[no-any-return]

    async def get_company_info(self, cik: str) -> Company:
        """Get company information by CIK.

        Args:
            cik: Central Index Key (will be zero-padded to 10 digits)

        Returns:
            Company information
        """
        cik_padded = cik.zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"

        data = await self._get_json(url)

        return Company(
            name=data.get("name", "Unknown"),
            cik=cik_padded,
            ticker=data.get("tickers", [None])[0] if data.get("tickers") else None,
            sic=data.get("sic"),
            sic_description=data.get("sicDescription"),
            state=data.get("stateOfIncorporation"),
        )

    async def get_company_filings(
        self,
        cik: str,
        form_types: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[Filing]:
        """Get filings for a specific company.

        Args:
            cik: Central Index Key
            form_types: Filter by form types (e.g., ["10-K", "DEF 14A"])
            start_date: Filter filings after this date
            end_date: Filter filings before this date
            limit: Maximum number of filings to return

        Returns:
            List of filings matching the criteria
        """
        cik_padded = cik.zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"

        data = await self._get_json(url)

        # Build company info
        company = Company(
            name=data.get("name", "Unknown"),
            cik=cik_padded,
            ticker=data.get("tickers", [None])[0] if data.get("tickers") else None,
            sic=data.get("sic"),
            sic_description=data.get("sicDescription"),
            state=data.get("stateOfIncorporation"),
        )

        # Parse filings from recent filings
        filings: list[Filing] = []
        recent = data.get("filings", {}).get("recent", {})

        if not recent:
            return filings

        # SEC returns arrays for each field
        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        for i, accession_number in enumerate(accession_numbers):
            if len(filings) >= limit:
                break

            form_type = forms[i] if i < len(forms) else ""

            # Filter by form type
            if form_types and form_type not in form_types:
                continue

            # Parse filing date
            filing_date_str = filing_dates[i] if i < len(filing_dates) else ""
            try:
                filing_date_parsed = date.fromisoformat(filing_date_str)
            except ValueError:
                continue

            # Filter by date range
            if start_date and filing_date_parsed < start_date:
                continue
            if end_date and filing_date_parsed > end_date:
                continue

            # Parse report date
            report_date_str = report_dates[i] if i < len(report_dates) else ""
            report_date_parsed = None
            if report_date_str:
                with contextlib.suppress(ValueError):
                    report_date_parsed = date.fromisoformat(report_date_str)

            # Build filing URL (documents are at www.sec.gov, not data.sec.gov)
            cik_stripped = cik_padded.lstrip("0")
            accession_formatted = accession_number.replace("-", "")
            filing_url = (
                f"{self.ARCHIVES_URL}/"
                f"{cik_stripped}/{accession_formatted}/{accession_number}-index.htm"
            )

            primary_doc = primary_docs[i] if i < len(primary_docs) else None

            filing = Filing(
                company=company,
                accession_number=accession_number,
                form_type=form_type,
                filing_date=filing_date_parsed,
                report_date=report_date_parsed,
                primary_document=primary_doc,
                filing_url=HttpUrl(filing_url),
            )
            filings.append(filing)

        return filings

    async def search_filings(
        self,
        form_type: str = "10-K",
        year: int | None = None,
        query: str | None = None,
        limit: int = 100,  # noqa: ARG002 - Reserved for future implementation
    ) -> FilingSearchResult:
        """Search for filings using SEC full-text search.

        Args:
            form_type: Filing form type (e.g., "10-K", "DEF 14A")
            year: Filter by filing year
            query: Optional text search query
            limit: Maximum number of results

        Returns:
            FilingSearchResult with matching filings
        """
        # Build search query
        search_params: dict[str, Any] = {
            "forms": form_type,
            "startdt": f"{year}-01-01" if year else "2020-01-01",
            "enddt": f"{year}-12-31" if year else date.today().isoformat(),
        }

        if query:
            search_params["q"] = query

        # SEC full-text search endpoint
        url = f"{self.FULL_TEXT_SEARCH_URL}?q={query or ''}&forms={form_type}"
        if year:
            url += f"&dateRange=custom&startdt={year}-01-01&enddt={year}-12-31"

        # Note: SEC's full-text search returns HTML, not JSON
        # For simplicity, we'll use the company submissions API instead
        # and iterate through known company CIKs

        # For now, return empty result - we'll implement via company iteration
        return FilingSearchResult(
            query=f"form:{form_type} year:{year}",
            total_hits=0,
            filings=[],
        )

    async def get_filing_documents(self, filing: Filing) -> list[HttpUrl]:
        """Get document URLs for a filing.

        Args:
            filing: Filing to get documents for

        Returns:
            List of document URLs (PDFs and HTMLs)
        """
        cik = filing.company.cik.lstrip("0")  # CIK without leading zeros for URLs
        accession = filing.accession_number_raw

        document_urls: list[HttpUrl] = []

        # If we have a primary document, add it directly
        if filing.primary_document:
            primary_url = f"{self.ARCHIVES_URL}/{cik}/{accession}/{filing.primary_document}"
            document_urls.append(HttpUrl(primary_url))

        # Try to get additional documents from the filing index page
        # Using the -index.htm page which lists all documents
        index_url = f"{self.ARCHIVES_URL}/{cik}/{accession}/{filing.accession_number}-index.htm"

        try:
            response = await self._get(index_url)
            html = response.text

            # Parse for document links (simple parsing)
            import re

            # Find all links to documents in the filing
            pattern = rf'/Archives/edgar/data/{cik}/{accession}/([^"]+\.(pdf|htm|html))'
            matches = re.findall(pattern, html, re.IGNORECASE)

            for filename, _ in matches:
                doc_url = f"{self.ARCHIVES_URL}/{cik}/{accession}/{filename}"
                if HttpUrl(doc_url) not in document_urls:
                    document_urls.append(HttpUrl(doc_url))

        except httpx.HTTPStatusError:
            # If index page fails, just return primary document
            pass

        return document_urls

    async def get_10k_filings_batch(
        self,
        ciks: list[str],
        year: int | None = None,
        limit_per_company: int = 1,
    ) -> list[Filing]:
        """Get 10-K filings for multiple companies.

        Args:
            ciks: List of CIKs to fetch
            year: Filter by year
            limit_per_company: Max filings per company

        Returns:
            List of all filings found
        """
        all_filings: list[Filing] = []

        start_date = date(year, 1, 1) if year else None
        end_date = date(year, 12, 31) if year else None

        for cik in ciks:
            try:
                filings = await self.get_company_filings(
                    cik=cik,
                    form_types=["10-K", "10-K/A"],
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit_per_company,
                )
                all_filings.extend(filings)
            except httpx.HTTPStatusError as e:
                # Log and continue on errors
                print(f"Warning: Failed to fetch CIK {cik}: {e}")
                continue

        return all_filings


# Convenience function for synchronous usage
def get_edgar_client(
    user_agent: str | None = None,
    requests_per_second: int | None = None,
) -> EdgarClient:
    """Create an EdgarClient instance.

    Use as async context manager:
        async with get_edgar_client() as client:
            filings = await client.get_company_filings("320193")  # Apple
    """
    return EdgarClient(user_agent=user_agent, requests_per_second=requests_per_second)
