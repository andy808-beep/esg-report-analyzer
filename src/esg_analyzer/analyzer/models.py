"""Pydantic data models for ESG analysis."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class FormType(str, Enum):
    """SEC filing form types relevant to ESG analysis."""

    FORM_10K = "10-K"
    FORM_10K_A = "10-K/A"  # Amended 10-K
    FORM_DEF_14A = "DEF 14A"  # Proxy statement
    FORM_20F = "20-F"  # Foreign private issuer annual report
    FORM_8K = "8-K"  # Current report


class ESGCategory(str, Enum):
    """Top-level ESG categories."""

    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"
    GOVERNANCE = "governance"


class Company(BaseModel):
    """Company information from SEC EDGAR."""

    name: str = Field(..., description="Company name")
    cik: str = Field(..., description="SEC Central Index Key (10-digit, zero-padded)")
    ticker: str | None = Field(None, description="Stock ticker symbol")
    sic: str | None = Field(None, description="Standard Industrial Classification code")
    sic_description: str | None = Field(None, description="SIC industry description")
    state: str | None = Field(None, description="State of incorporation")

    @property
    def cik_padded(self) -> str:
        """Return CIK zero-padded to 10 digits."""
        return self.cik.zfill(10)


class Filing(BaseModel):
    """SEC filing metadata."""

    company: Company
    accession_number: str = Field(..., description="SEC accession number (unique filing ID)")
    form_type: str = Field(..., description="Filing form type (e.g., 10-K, DEF 14A)")
    filing_date: date = Field(..., description="Date filed with SEC")
    report_date: date | None = Field(None, description="Period of report")
    primary_document: str | None = Field(None, description="Primary document filename")
    filing_url: HttpUrl = Field(..., description="URL to filing index page")
    document_urls: list[HttpUrl] = Field(
        default_factory=list, description="URLs to filing documents"
    )

    @property
    def accession_number_formatted(self) -> str:
        """Return accession number with dashes (as used in URLs)."""
        # Convert 0001193125-24-012345 format
        if "-" in self.accession_number:
            return self.accession_number
        # Convert 0001193125240012345 to 0001193125-24-012345
        an = self.accession_number.replace("-", "")
        return f"{an[:10]}-{an[10:12]}-{an[12:]}"

    @property
    def accession_number_raw(self) -> str:
        """Return accession number without dashes (as used in some APIs)."""
        return self.accession_number.replace("-", "")


class ExtractedDocument(BaseModel):
    """Extracted text content from a filing document."""

    filing: Filing
    filename: str = Field(..., description="Document filename")
    content: str = Field(..., description="Extracted text content")
    page_count: int | None = Field(None, description="Number of pages (for PDFs)")
    extracted_at: datetime = Field(default_factory=datetime.now)


class KeywordMatch(BaseModel):
    """A single keyword match found in a document."""

    keyword: str = Field(..., description="The matched keyword")
    category: ESGCategory = Field(..., description="ESG category (E/S/G)")
    subcategory: str = Field(..., description="Subcategory (e.g., climate, labor)")
    sentence: str = Field(..., description="The sentence containing the match")
    context: str = Field(..., description="Surrounding sentences for context")
    page_number: int | None = Field(None, description="Page number (if available)")


class AnalysisResult(BaseModel):
    """Results of keyword analysis on a filing."""

    filing: Filing
    total_matches: int = Field(..., description="Total keyword matches found")
    matches_by_category: dict[ESGCategory, int] = Field(
        default_factory=dict, description="Match count per ESG category"
    )
    matches_by_subcategory: dict[str, int] = Field(
        default_factory=dict, description="Match count per subcategory"
    )
    matches: list[KeywordMatch] = Field(default_factory=list, description="Individual matches")
    analyzed_at: datetime = Field(default_factory=datetime.now)

    @property
    def environmental_count(self) -> int:
        """Number of environmental matches."""
        return self.matches_by_category.get(ESGCategory.ENVIRONMENTAL, 0)

    @property
    def social_count(self) -> int:
        """Number of social matches."""
        return self.matches_by_category.get(ESGCategory.SOCIAL, 0)

    @property
    def governance_count(self) -> int:
        """Number of governance matches."""
        return self.matches_by_category.get(ESGCategory.GOVERNANCE, 0)


class FilingSearchResult(BaseModel):
    """Search results from SEC EDGAR."""

    query: str = Field(..., description="Search query used")
    total_hits: int = Field(..., description="Total number of results")
    filings: list[Filing] = Field(default_factory=list, description="List of matching filings")
    searched_at: datetime = Field(default_factory=datetime.now)
