"""Tests for the reporter module."""

from datetime import date
from pathlib import Path

import pytest

from esg_analyzer.analyzer.models import (
    AnalysisResult,
    Company,
    ESGCategory,
    Filing,
    KeywordMatch,
)
from esg_analyzer.reporter import CSVExporter, HTMLReporter


@pytest.fixture
def sample_results() -> list[AnalysisResult]:
    """Create sample analysis results for testing."""
    company1 = Company(name="Test Corp", cik="0001234567", ticker="TEST")
    filing1 = Filing(
        company=company1,
        accession_number="0001234567-24-000001",
        form_type="10-K",
        filing_date=date(2024, 1, 15),
        filing_url="https://example.com/filing1",
    )

    company2 = Company(name="Sample Inc", cik="0007654321", ticker="SMPL")
    filing2 = Filing(
        company=company2,
        accession_number="0007654321-24-000001",
        form_type="10-K",
        filing_date=date(2024, 2, 20),
        filing_url="https://example.com/filing2",
    )

    matches1 = [
        KeywordMatch(
            keyword="carbon neutrality",
            category=ESGCategory.ENVIRONMENTAL,
            subcategory="climate",
            sentence="We are committed to carbon neutrality by 2030.",
            context="Our company is committed to carbon neutrality by 2030. This is a key goal.",
        ),
        KeywordMatch(
            keyword="board diversity",
            category=ESGCategory.GOVERNANCE,
            subcategory="board",
            sentence="Board diversity is a priority.",
            context="Board diversity is a priority for our organization.",
        ),
    ]

    matches2 = [
        KeywordMatch(
            keyword="workplace safety",
            category=ESGCategory.SOCIAL,
            subcategory="labor",
            sentence="Workplace safety is paramount.",
            context="Workplace safety is paramount to our operations.",
        ),
    ]

    result1 = AnalysisResult(
        filing=filing1,
        total_matches=2,
        matches_by_category={
            ESGCategory.ENVIRONMENTAL: 1,
            ESGCategory.GOVERNANCE: 1,
        },
        matches=matches1,
    )

    result2 = AnalysisResult(
        filing=filing2,
        total_matches=1,
        matches_by_category={ESGCategory.SOCIAL: 1},
        matches=matches2,
    )

    return [result1, result2]


class TestHTMLReporter:
    """Tests for HTMLReporter class."""

    def test_generate_report(self, sample_results: list[AnalysisResult]) -> None:
        """Test HTML report generation."""
        reporter = HTMLReporter()
        html = reporter.generate_report(sample_results, title="Test Report")

        assert "<!DOCTYPE html>" in html
        assert "Test Report" in html
        assert "Test Corp" in html
        assert "Sample Inc" in html
        assert "carbon neutrality" in html

    def test_generate_report_has_css(self, sample_results: list[AnalysisResult]) -> None:
        """Test that generated HTML includes CSS."""
        reporter = HTMLReporter()
        html = reporter.generate_report(sample_results)

        assert "<style>" in html
        assert "</style>" in html

    def test_save_report(
        self, sample_results: list[AnalysisResult], tmp_path: Path
    ) -> None:
        """Test saving HTML report to file."""
        output_path = tmp_path / "report.html"

        reporter = HTMLReporter()
        reporter.save_report(sample_results, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_keyword_highlighting(
        self, sample_results: list[AnalysisResult]
    ) -> None:
        """Test that keywords are highlighted."""
        reporter = HTMLReporter(highlight_keywords=True)
        html = reporter.generate_report(sample_results)

        assert "keyword-highlight" in html

    def test_empty_results(self) -> None:
        """Test report with no results."""
        reporter = HTMLReporter()
        html = reporter.generate_report([], title="Empty Report")

        assert "<!DOCTYPE html>" in html
        assert "Empty Report" in html


class TestCSVExporter:
    """Tests for CSVExporter class."""

    def test_export_summary(
        self, sample_results: list[AnalysisResult], tmp_path: Path
    ) -> None:
        """Test summary CSV export."""
        output_path = tmp_path / "summary.csv"

        exporter = CSVExporter()
        exporter.export_summary(sample_results, output_path)

        assert output_path.exists()

        content = output_path.read_text()
        lines = content.strip().split("\n")

        # Header + 2 data rows
        assert len(lines) == 3
        assert "Company" in lines[0]
        assert "Test Corp" in lines[1]
        assert "Sample Inc" in lines[2]

    def test_export_details(
        self, sample_results: list[AnalysisResult], tmp_path: Path
    ) -> None:
        """Test details CSV export."""
        output_path = tmp_path / "details.csv"

        exporter = CSVExporter()
        exporter.export_details(sample_results, output_path)

        assert output_path.exists()

        content = output_path.read_text()
        lines = content.strip().split("\n")

        # Header + 3 matches (2 from result1 + 1 from result2)
        assert len(lines) == 4
        assert "Keyword" in lines[0]
        assert "carbon neutrality" in content
        assert "workplace safety" in content

    def test_export_details_without_context(
        self, sample_results: list[AnalysisResult], tmp_path: Path
    ) -> None:
        """Test details CSV export without context column."""
        output_path = tmp_path / "details.csv"

        exporter = CSVExporter()
        exporter.export_details(sample_results, output_path, include_context=False)

        content = output_path.read_text()
        header = content.split("\n")[0]

        assert "Context" not in header

    def test_export_all(
        self, sample_results: list[AnalysisResult], tmp_path: Path
    ) -> None:
        """Test exporting both summary and details."""
        exporter = CSVExporter()
        summary_path, details_path = exporter.export_all(
            sample_results, tmp_path, prefix="test"
        )

        assert summary_path.exists()
        assert details_path.exists()
        assert summary_path.name == "test_summary.csv"
        assert details_path.name == "test_details.csv"

    def test_empty_results(self, tmp_path: Path) -> None:
        """Test export with no results."""
        output_path = tmp_path / "empty.csv"

        exporter = CSVExporter()
        exporter.export_summary([], output_path)

        content = output_path.read_text()
        lines = content.strip().split("\n")

        # Only header row
        assert len(lines) == 1

