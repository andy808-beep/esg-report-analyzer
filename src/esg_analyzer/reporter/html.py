"""HTML report generator for ESG analysis results."""

import html
import re
from datetime import datetime
from pathlib import Path

from esg_analyzer.analyzer.models import AnalysisResult


class HTMLReporter:
    """Generate standalone HTML reports for ESG analysis.

    Creates beautiful, self-contained HTML files with embedded CSS.

    Example:
        reporter = HTMLReporter()
        html_content = reporter.generate_report(results)
        reporter.save_report(results, Path("report.html"))
    """

    def __init__(self, highlight_keywords: bool = True) -> None:
        """Initialize HTML reporter.

        Args:
            highlight_keywords: Highlight matched keywords in output
        """
        self.highlight_keywords = highlight_keywords

    def generate_report(
        self,
        results: list[AnalysisResult],
        title: str = "ESG Analysis Report",
    ) -> str:
        """Generate HTML report for multiple analysis results.

        Args:
            results: List of analysis results
            title: Report title

        Returns:
            Complete HTML document as string
        """
        # Calculate totals
        total_env = sum(r.environmental_count for r in results)
        total_soc = sum(r.social_count for r in results)
        total_gov = sum(r.governance_count for r in results)
        total_all = sum(r.total_matches for r in results)

        # Build HTML
        html_parts = [self._get_html_header(title)]

        # Summary section
        html_parts.append(f"""
        <div class="summary-cards">
            <div class="card environmental">
                <div class="card-value">{total_env}</div>
                <div class="card-label">Environmental</div>
            </div>
            <div class="card social">
                <div class="card-value">{total_soc}</div>
                <div class="card-label">Social</div>
            </div>
            <div class="card governance">
                <div class="card-value">{total_gov}</div>
                <div class="card-label">Governance</div>
            </div>
            <div class="card total">
                <div class="card-value">{total_all}</div>
                <div class="card-label">Total Matches</div>
            </div>
        </div>
        """)

        # Summary table
        html_parts.append("""
        <h2>Filing Summary</h2>
        <table class="summary-table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Ticker</th>
                    <th>Form</th>
                    <th>Date</th>
                    <th class="env">Env</th>
                    <th class="soc">Soc</th>
                    <th class="gov">Gov</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
        """)

        for result in results:
            company = result.filing.company
            html_parts.append(f"""
                <tr>
                    <td>{html.escape(company.name[:40])}</td>
                    <td>{html.escape(company.ticker or "-")}</td>
                    <td>{html.escape(result.filing.form_type)}</td>
                    <td>{result.filing.filing_date}</td>
                    <td class="env">{result.environmental_count}</td>
                    <td class="soc">{result.social_count}</td>
                    <td class="gov">{result.governance_count}</td>
                    <td><strong>{result.total_matches}</strong></td>
                </tr>
            """)

        html_parts.append("</tbody></table>")

        # Detailed results for each filing
        html_parts.append("<h2>Detailed Results</h2>")

        for result in results:
            html_parts.append(self._generate_filing_section(result))

        html_parts.append(self._get_html_footer())

        return "\n".join(html_parts)

    def _generate_filing_section(self, result: AnalysisResult) -> str:
        """Generate HTML section for a single filing."""
        company = result.filing.company
        title = f"{company.name}"
        if company.ticker:
            title += f" ({company.ticker})"

        html_parts = [
            f"""
        <div class="filing-section">
            <h3>{html.escape(title)}</h3>
            <p class="filing-meta">
                {html.escape(result.filing.form_type)} |
                Filed: {result.filing.filing_date}
            </p>
        """
        ]

        if result.matches:
            html_parts.append('<div class="matches">')

            for match in result.matches[:20]:  # Limit to 20 per filing
                category_class = match.category.value
                context_text = html.escape(match.context)

                if self.highlight_keywords:
                    context_text = self._highlight_keyword(context_text, match.keyword)

                html_parts.append(f"""
                <div class="match {category_class}">
                    <div class="match-header">
                        <span class="category-badge">{match.category.value.upper()}</span>
                        <span class="subcategory">{html.escape(match.subcategory)}</span>
                        <span class="keyword">"{html.escape(match.keyword)}"</span>
                    </div>
                    <div class="match-context">{context_text}</div>
                </div>
                """)

            if len(result.matches) > 20:
                remaining = len(result.matches) - 20
                html_parts.append(f'<p class="more-matches">... and {remaining} more matches</p>')

            html_parts.append("</div>")
        else:
            html_parts.append('<p class="no-matches">No ESG keywords found</p>')

        html_parts.append("</div>")

        return "\n".join(html_parts)

    def _highlight_keyword(self, text: str, keyword: str) -> str:
        """Highlight keyword in HTML text."""
        escaped_keyword = html.escape(keyword)
        pattern = re.compile(re.escape(escaped_keyword), re.IGNORECASE)

        def replacer(match: re.Match[str]) -> str:
            return f'<mark class="keyword-highlight">{match.group()}</mark>'

        return pattern.sub(replacer, text)

    def save_report(
        self,
        results: list[AnalysisResult],
        output_path: Path,
        title: str = "ESG Analysis Report",
    ) -> None:
        """Save HTML report to file.

        Args:
            results: Analysis results
            output_path: Path to save HTML file
            title: Report title
        """
        html_content = self.generate_report(results, title)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _get_html_header(self, title: str) -> str:
        """Get HTML document header with embedded CSS."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            --env-color: #22c55e;
            --soc-color: #3b82f6;
            --gov-color: #a855f7;
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #e2e8f0;
            --text-muted: #94a3b8;
            --border-color: #334155;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 2rem;
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--env-color), var(--soc-color), var(--gov-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        h2 {{
            font-size: 1.5rem;
            margin: 2rem 0 1rem;
            color: var(--text-color);
        }}

        h3 {{
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: var(--text-muted);
            margin-bottom: 2rem;
        }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid var(--border-color);
        }}

        .card.environmental {{ border-top: 3px solid var(--env-color); }}
        .card.social {{ border-top: 3px solid var(--soc-color); }}
        .card.governance {{ border-top: 3px solid var(--gov-color); }}
        .card.total {{ border-top: 3px solid var(--text-color); }}

        .card-value {{
            font-size: 2.5rem;
            font-weight: 700;
        }}

        .card.environmental .card-value {{ color: var(--env-color); }}
        .card.social .card-value {{ color: var(--soc-color); }}
        .card.governance .card-value {{ color: var(--gov-color); }}

        .card-label {{
            color: var(--text-muted);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 12px;
            overflow: hidden;
        }}

        .summary-table th,
        .summary-table td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        .summary-table th {{
            background: rgba(0, 0, 0, 0.2);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}

        .summary-table td.env {{ color: var(--env-color); }}
        .summary-table td.soc {{ color: var(--soc-color); }}
        .summary-table td.gov {{ color: var(--gov-color); }}

        .summary-table tr:hover {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .filing-section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-color);
        }}

        .filing-meta {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }}

        .match {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-left: 3px solid var(--border-color);
        }}

        .match.environmental {{ border-left-color: var(--env-color); }}
        .match.social {{ border-left-color: var(--soc-color); }}
        .match.governance {{ border-left-color: var(--gov-color); }}

        .match-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
            flex-wrap: wrap;
        }}

        .category-badge {{
            font-size: 0.7rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .match.environmental .category-badge {{ background: var(--env-color); color: #000; }}
        .match.social .category-badge {{ background: var(--soc-color); color: #000; }}
        .match.governance .category-badge {{ background: var(--gov-color); color: #000; }}

        .subcategory {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}

        .keyword {{
            font-weight: 600;
            color: var(--text-color);
        }}

        .match-context {{
            color: var(--text-muted);
            font-size: 0.9rem;
            line-height: 1.7;
        }}

        .keyword-highlight {{
            background: rgba(239, 68, 68, 0.3);
            color: #fca5a5;
            padding: 0.1rem 0.25rem;
            border-radius: 3px;
        }}

        .more-matches, .no-matches {{
            color: var(--text-muted);
            font-style: italic;
            padding: 1rem;
        }}

        footer {{
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.875rem;
            text-align: center;
        }}
    </style>
</head>
<body>
    <h1>{html.escape(title)}</h1>
    <p class="subtitle">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
"""

    def _get_html_footer(self) -> str:
        """Get HTML document footer."""
        return """
    <footer>
        Generated by ESG Report Analyzer
    </footer>
</body>
</html>
"""
