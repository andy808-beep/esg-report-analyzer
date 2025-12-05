"""Tests for Pydantic data models."""

from datetime import date

import pytest
from pydantic import ValidationError

from esg_analyzer.analyzer.models import (
    AnalysisResult,
    Company,
    ESGCategory,
    Filing,
    KeywordMatch,
)


class TestCompany:
    """Tests for Company model."""

    def test_create_company(self) -> None:
        """Test creating a company."""
        company = Company(
            name="Apple Inc.",
            cik="320193",
            ticker="AAPL",
            sic="3571",
            sic_description="Electronic Computers",
        )

        assert company.name == "Apple Inc."
        assert company.ticker == "AAPL"

    def test_cik_padded(self) -> None:
        """Test CIK zero-padding."""
        company = Company(name="Test", cik="123")
        assert company.cik_padded == "0000000123"

        company2 = Company(name="Test", cik="0000000123")
        assert company2.cik_padded == "0000000123"

    def test_company_optional_fields(self) -> None:
        """Test that optional fields can be None."""
        company = Company(name="Test Corp", cik="123456")

        assert company.ticker is None
        assert company.sic is None
        assert company.sic_description is None
        assert company.state is None


class TestFiling:
    """Tests for Filing model."""

    def test_create_filing(self) -> None:
        """Test creating a filing."""
        company = Company(name="Test", cik="123456")
        filing = Filing(
            company=company,
            accession_number="0001234567-24-000001",
            form_type="10-K",
            filing_date=date(2024, 1, 15),
            filing_url="https://example.com/filing",
        )

        assert filing.form_type == "10-K"
        assert filing.filing_date == date(2024, 1, 15)

    def test_accession_number_formatted(self) -> None:
        """Test accession number formatting."""
        company = Company(name="Test", cik="123456")
        filing = Filing(
            company=company,
            accession_number="0001234567-24-000001",
            form_type="10-K",
            filing_date=date(2024, 1, 15),
            filing_url="https://example.com",
        )

        assert filing.accession_number_formatted == "0001234567-24-000001"

    def test_accession_number_raw(self) -> None:
        """Test raw accession number (no dashes)."""
        company = Company(name="Test", cik="123456")
        filing = Filing(
            company=company,
            accession_number="0001234567-24-000001",
            form_type="10-K",
            filing_date=date(2024, 1, 15),
            filing_url="https://example.com",
        )

        assert filing.accession_number_raw == "000123456724000001"


class TestKeywordMatch:
    """Tests for KeywordMatch model."""

    def test_create_match(self) -> None:
        """Test creating a keyword match."""
        match = KeywordMatch(
            keyword="carbon neutrality",
            category=ESGCategory.ENVIRONMENTAL,
            subcategory="climate",
            sentence="We are committed to carbon neutrality by 2030.",
            context="Our company has set ambitious goals. We are committed to carbon neutrality by 2030. This aligns with global standards.",
        )

        assert match.keyword == "carbon neutrality"
        assert match.category == ESGCategory.ENVIRONMENTAL
        assert match.subcategory == "climate"

    def test_match_requires_all_fields(self) -> None:
        """Test that all required fields must be provided."""
        with pytest.raises(ValidationError):
            KeywordMatch(
                keyword="test",
                # Missing category, subcategory, sentence, context
            )


class TestAnalysisResult:
    """Tests for AnalysisResult model."""

    def test_category_count_properties(self) -> None:
        """Test category count properties."""
        company = Company(name="Test", cik="123456")
        filing = Filing(
            company=company,
            accession_number="0001234567-24-000001",
            form_type="10-K",
            filing_date=date(2024, 1, 15),
            filing_url="https://example.com",
        )

        result = AnalysisResult(
            filing=filing,
            total_matches=30,
            matches_by_category={
                ESGCategory.ENVIRONMENTAL: 15,
                ESGCategory.SOCIAL: 10,
                ESGCategory.GOVERNANCE: 5,
            },
            matches=[],
        )

        assert result.environmental_count == 15
        assert result.social_count == 10
        assert result.governance_count == 5

    def test_missing_category_returns_zero(self) -> None:
        """Test that missing categories return 0."""
        company = Company(name="Test", cik="123456")
        filing = Filing(
            company=company,
            accession_number="0001234567-24-000001",
            form_type="10-K",
            filing_date=date(2024, 1, 15),
            filing_url="https://example.com",
        )

        result = AnalysisResult(
            filing=filing,
            total_matches=5,
            matches_by_category={ESGCategory.ENVIRONMENTAL: 5},
            matches=[],
        )

        assert result.environmental_count == 5
        assert result.social_count == 0
        assert result.governance_count == 0


class TestESGCategory:
    """Tests for ESGCategory enum."""

    def test_category_values(self) -> None:
        """Test category string values."""
        assert ESGCategory.ENVIRONMENTAL.value == "environmental"
        assert ESGCategory.SOCIAL.value == "social"
        assert ESGCategory.GOVERNANCE.value == "governance"

    def test_category_from_string(self) -> None:
        """Test creating category from string."""
        assert ESGCategory("environmental") == ESGCategory.ENVIRONMENTAL
        assert ESGCategory("social") == ESGCategory.SOCIAL
        assert ESGCategory("governance") == ESGCategory.GOVERNANCE

