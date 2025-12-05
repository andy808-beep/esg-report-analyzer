"""Tests for the keyword analyzer module."""

import pytest

from esg_analyzer.analyzer import KeywordAnalyzer, quick_analyze
from esg_analyzer.analyzer.models import (
    Company,
    ESGCategory,
    ExtractedDocument,
    Filing,
)


@pytest.fixture
def sample_filing() -> Filing:
    """Create a sample filing for testing."""
    return Filing(
        company=Company(name="Test Corp", cik="0001234567", ticker="TEST"),
        accession_number="0001234567-24-000001",
        form_type="10-K",
        filing_date="2024-01-15",
        filing_url="https://example.com/filing",
    )


@pytest.fixture
def sample_document(sample_filing: Filing) -> ExtractedDocument:
    """Create a sample extracted document for testing."""
    content = """
    Test Corporation is committed to achieving carbon neutrality by 2030.
    We have implemented comprehensive greenhouse gas emissions monitoring
    across all our facilities. Our Scope 1 and Scope 2 emissions have
    decreased by 25% since 2020.

    The company maintains strong governance practices with board diversity
    as a key priority. Our independent directors comprise 60% of the board.
    We have a robust whistleblower policy and anti-corruption training
    for all employees.

    Employee wellbeing is central to our mission. We ensure workplace safety
    through regular audits and have zero tolerance for child labor in our
    supply chain. Our supplier code of conduct is reviewed annually.
    """
    return ExtractedDocument(
        filing=sample_filing,
        filename="test-10k.htm",
        content=content,
        page_count=50,
    )


class TestKeywordAnalyzer:
    """Tests for KeywordAnalyzer class."""

    def test_analyzer_initialization(self) -> None:
        """Test that analyzer initializes with keywords."""
        analyzer = KeywordAnalyzer()
        keywords = analyzer.get_all_keywords()
        assert len(keywords) > 0

    def test_keyword_count(self) -> None:
        """Test keyword count by category."""
        analyzer = KeywordAnalyzer()
        counts = analyzer.get_keyword_count()

        assert "environmental" in counts
        assert "social" in counts
        assert "governance" in counts

    def test_analyze_finds_environmental_keywords(
        self, sample_document: ExtractedDocument
    ) -> None:
        """Test that environmental keywords are found."""
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(sample_document)

        assert result.environmental_count > 0
        env_keywords = [
            m.keyword for m in result.matches if m.category == ESGCategory.ENVIRONMENTAL
        ]
        assert "carbon neutrality" in env_keywords or "greenhouse gas" in env_keywords

    def test_analyze_finds_social_keywords(
        self, sample_document: ExtractedDocument
    ) -> None:
        """Test that social keywords are found."""
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(sample_document)

        assert result.social_count > 0
        social_keywords = [
            m.keyword for m in result.matches if m.category == ESGCategory.SOCIAL
        ]
        assert any(
            kw in social_keywords
            for kw in ["workplace safety", "child labor", "supplier code of conduct"]
        )

    def test_analyze_finds_governance_keywords(
        self, sample_document: ExtractedDocument
    ) -> None:
        """Test that governance keywords are found."""
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(sample_document)

        assert result.governance_count > 0
        gov_keywords = [
            m.keyword for m in result.matches if m.category == ESGCategory.GOVERNANCE
        ]
        assert any(
            kw in gov_keywords
            for kw in ["board diversity", "independent directors", "whistleblower"]
        )

    def test_analyze_includes_context(
        self, sample_document: ExtractedDocument
    ) -> None:
        """Test that matches include context."""
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(sample_document)

        assert len(result.matches) > 0
        for match in result.matches:
            assert len(match.context) > len(match.keyword)
            assert match.keyword.lower() in match.context.lower()

    def test_analyze_respects_max_matches(
        self, sample_document: ExtractedDocument
    ) -> None:
        """Test that max_matches limit is respected."""
        analyzer = KeywordAnalyzer(max_matches=3)
        result = analyzer.analyze(sample_document)

        assert len(result.matches) <= 3

    def test_analyze_empty_document(self, sample_filing: Filing) -> None:
        """Test analyzing empty document."""
        doc = ExtractedDocument(
            filing=sample_filing,
            filename="empty.htm",
            content="",
            page_count=0,
        )
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(doc)

        assert result.total_matches == 0
        assert len(result.matches) == 0

    def test_analyze_no_matches(self, sample_filing: Filing) -> None:
        """Test document with no ESG keywords."""
        doc = ExtractedDocument(
            filing=sample_filing,
            filename="no-esg.htm",
            content="The quick brown fox jumps over the lazy dog.",
            page_count=1,
        )
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(doc)

        assert result.total_matches == 0

    def test_case_insensitive_matching(self, sample_filing: Filing) -> None:
        """Test that matching is case-insensitive."""
        doc = ExtractedDocument(
            filing=sample_filing,
            filename="caps.htm",
            content="Our CARBON NEUTRALITY goal is ambitious. GREENHOUSE GAS emissions are tracked.",
            page_count=1,
        )
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(doc)

        assert result.environmental_count > 0


class TestQuickAnalyze:
    """Tests for quick_analyze function."""

    def test_quick_analyze_basic(self) -> None:
        """Test basic quick analysis."""
        text = "We are committed to carbon neutrality and board diversity."
        result = quick_analyze(text)

        assert "environmental" in result or "governance" in result

    def test_quick_analyze_returns_categories(self) -> None:
        """Test that categories are returned correctly."""
        text = """
        Carbon neutrality is our goal. We monitor greenhouse gas emissions.
        Board diversity is important. We have anti-corruption policies.
        """
        result = quick_analyze(text)

        assert isinstance(result, dict)
        if "environmental" in result:
            assert isinstance(result["environmental"], list)

    def test_quick_analyze_empty_text(self) -> None:
        """Test quick analysis of empty text."""
        result = quick_analyze("")
        assert result == {} or all(len(v) == 0 for v in result.values())
