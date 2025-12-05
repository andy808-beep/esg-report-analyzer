"""CSV export for ESG analysis results."""

import csv
from pathlib import Path

from esg_analyzer.analyzer.models import AnalysisResult


class CSVExporter:
    """Export ESG analysis results to CSV format.

    Generates two CSV files:
    - Summary: one row per filing with aggregate counts
    - Details: one row per keyword match

    Example:
        exporter = CSVExporter()
        exporter.export_summary(results, Path("summary.csv"))
        exporter.export_details(results, Path("details.csv"))
    """

    def export_summary(
        self,
        results: list[AnalysisResult],
        output_path: Path,
    ) -> None:
        """Export summary CSV with one row per filing.

        Columns: Company, Ticker, CIK, Form, Filing Date, Environmental,
                 Social, Governance, Total

        Args:
            results: Analysis results to export
            output_path: Path to save CSV file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "Company",
                    "Ticker",
                    "CIK",
                    "Form Type",
                    "Filing Date",
                    "Environmental",
                    "Social",
                    "Governance",
                    "Total Matches",
                ]
            )

            # Data rows
            for result in results:
                company = result.filing.company
                writer.writerow(
                    [
                        company.name,
                        company.ticker or "",
                        company.cik,
                        result.filing.form_type,
                        result.filing.filing_date.isoformat(),
                        result.environmental_count,
                        result.social_count,
                        result.governance_count,
                        result.total_matches,
                    ]
                )

    def export_details(
        self,
        results: list[AnalysisResult],
        output_path: Path,
        include_context: bool = True,
    ) -> None:
        """Export detailed CSV with one row per keyword match.

        Columns: Company, Ticker, Form, Filing Date, Category, Subcategory,
                 Keyword, Sentence, Context (optional)

        Args:
            results: Analysis results to export
            output_path: Path to save CSV file
            include_context: Whether to include context column
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            headers = [
                "Company",
                "Ticker",
                "Form Type",
                "Filing Date",
                "Category",
                "Subcategory",
                "Keyword",
                "Sentence",
            ]
            if include_context:
                headers.append("Context")

            writer.writerow(headers)

            # Data rows
            for result in results:
                company = result.filing.company
                for match in result.matches:
                    row = [
                        company.name,
                        company.ticker or "",
                        result.filing.form_type,
                        result.filing.filing_date.isoformat(),
                        match.category.value,
                        match.subcategory,
                        match.keyword,
                        match.sentence,
                    ]
                    if include_context:
                        row.append(match.context)

                    writer.writerow(row)

    def export_all(
        self,
        results: list[AnalysisResult],
        output_dir: Path,
        prefix: str = "esg_analysis",
    ) -> tuple[Path, Path]:
        """Export both summary and details CSVs.

        Args:
            results: Analysis results
            output_dir: Directory to save files
            prefix: Filename prefix

        Returns:
            Tuple of (summary_path, details_path)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        summary_path = output_dir / f"{prefix}_summary.csv"
        details_path = output_dir / f"{prefix}_details.csv"

        self.export_summary(results, summary_path)
        self.export_details(results, details_path)

        return summary_path, details_path
