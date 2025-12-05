"""Console output reporter with rich formatting."""

import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from esg_analyzer.analyzer.models import AnalysisResult, ESGCategory


class ConsoleReporter:
    """Generate beautiful console output for ESG analysis results.

    Uses rich library for formatted tables, panels, and highlighted text.

    Example:
        reporter = ConsoleReporter()
        reporter.print_result(analysis_result)
        reporter.print_summary([result1, result2, result3])
    """

    def __init__(self, highlight_keywords: bool = True) -> None:
        """Initialize console reporter.

        Args:
            highlight_keywords: Highlight matched keywords in output
        """
        self.console = Console()
        self.highlight_keywords = highlight_keywords

        # Colors for ESG categories
        self.category_colors = {
            ESGCategory.ENVIRONMENTAL: "green",
            ESGCategory.SOCIAL: "blue",
            ESGCategory.GOVERNANCE: "magenta",
        }

    def print_result(
        self,
        result: AnalysisResult,
        max_matches: int = 10,
        show_context: bool = True,
    ) -> None:
        """Print analysis result for a single filing.

        Args:
            result: Analysis result to display
            max_matches: Maximum number of matches to show
            show_context: Whether to show context around matches
        """
        # Header panel
        company = result.filing.company
        title = f"{company.name}"
        if company.ticker:
            title += f" ({company.ticker})"

        subtitle = f"{result.filing.form_type} — {result.filing.filing_date}"

        self.console.print()
        self.console.print(
            Panel(
                f"[bold]{title}[/bold]\n{subtitle}",
                title="ESG Report Analysis",
                border_style="cyan",
            )
        )

        # Category summary table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Category", style="dim")
        table.add_column("Matches", justify="right")

        for category in ESGCategory:
            count = result.matches_by_category.get(category, 0)
            color = self.category_colors.get(category, "white")
            table.add_row(
                f"[{color}]{category.value.title()}[/{color}]",
                str(count),
            )

        table.add_row("[bold]Total[/bold]", f"[bold]{result.total_matches}[/bold]")

        self.console.print()
        self.console.print(table)

        # Top matches
        if result.matches:
            self.console.print()
            self.console.print("[bold]Top Matches:[/bold]")
            self.console.print("─" * 60)

            for match in result.matches[:max_matches]:
                color = self.category_colors.get(match.category, "white")
                category_label = (
                    f"[{color}][{match.category.value.upper()}/{match.subcategory}][/{color}]"
                )

                # Highlight keyword in context
                display_text = match.context if show_context else match.sentence

                if self.highlight_keywords:
                    display_text = self._highlight_keyword(display_text, match.keyword)

                self.console.print(f'{category_label} [bold]"{match.keyword}"[/bold]')
                self.console.print(f"  {display_text}")
                self.console.print()

            if len(result.matches) > max_matches:
                remaining = len(result.matches) - max_matches
                self.console.print(f"  [dim]... and {remaining} more matches[/dim]")

        self.console.print("─" * 60)

    def print_summary(self, results: list[AnalysisResult]) -> None:
        """Print summary table for multiple analysis results.

        Args:
            results: List of analysis results
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Analysis Summary[/bold]\n{len(results)} filings analyzed",
                border_style="cyan",
            )
        )

        table = Table(show_header=True, header_style="bold")
        table.add_column("Company", style="dim")
        table.add_column("Ticker")
        table.add_column("Form")
        table.add_column("Date")
        table.add_column("Env", justify="right", style="green")
        table.add_column("Soc", justify="right", style="blue")
        table.add_column("Gov", justify="right", style="magenta")
        table.add_column("Total", justify="right", style="bold")

        for result in results:
            company = result.filing.company
            table.add_row(
                company.name[:30] + ("..." if len(company.name) > 30 else ""),
                company.ticker or "-",
                result.filing.form_type,
                str(result.filing.filing_date),
                str(result.environmental_count),
                str(result.social_count),
                str(result.governance_count),
                str(result.total_matches),
            )

        self.console.print()
        self.console.print(table)

        # Aggregate stats
        total_env = sum(r.environmental_count for r in results)
        total_soc = sum(r.social_count for r in results)
        total_gov = sum(r.governance_count for r in results)
        total_all = sum(r.total_matches for r in results)

        self.console.print()
        self.console.print(f"[green]Environmental:[/green] {total_env}")
        self.console.print(f"[blue]Social:[/blue] {total_soc}")
        self.console.print(f"[magenta]Governance:[/magenta] {total_gov}")
        self.console.print(f"[bold]Total matches:[/bold] {total_all}")

    def _highlight_keyword(self, text: str, keyword: str) -> str:
        """Highlight keyword in text with red color."""
        # Case-insensitive replace with highlighting
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        def replacer(match: re.Match[str]) -> str:
            return f"[bold red]{match.group()}[/bold red]"

        return pattern.sub(replacer, text)


def print_result(result: AnalysisResult, **kwargs: object) -> None:
    """Convenience function to print a single result."""
    reporter = ConsoleReporter()
    reporter.print_result(result, **kwargs)  # type: ignore[arg-type]


def print_summary(results: list[AnalysisResult]) -> None:
    """Convenience function to print summary."""
    reporter = ConsoleReporter()
    reporter.print_summary(results)
