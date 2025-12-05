"""Command-line interface for ESG Report Analyzer."""

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from esg_analyzer.analyzer import AnalysisResult, KeywordAnalyzer
from esg_analyzer.config import get_settings
from esg_analyzer.extractor import DocumentExtractor
from esg_analyzer.reporter import ConsoleReporter, CSVExporter, HTMLReporter
from esg_analyzer.scraper import Downloader, EdgarClient

app = typer.Typer(
    name="esg-analyzer",
    help="Analyze ESG disclosures in SEC filings using keyword extraction.",
    add_completion=False,
)

console = Console()


@app.command()
def discover(
    form_type: Annotated[str, typer.Option("--form-type", "-f", help="Filing form type")] = "10-K",
    year: Annotated[int | None, typer.Option("--year", "-y", help="Filing year")] = None,
    ciks: Annotated[
        str | None,
        typer.Option("--ciks", "-c", help="Comma-separated CIKs to search"),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max filings to discover")] = 50,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output JSON file")] = Path(
        "filings.json"
    ),
    user_agent: Annotated[
        str | None, typer.Option("--user-agent", help="SEC API User-Agent")
    ] = None,
) -> None:
    """Discover SEC filings from EDGAR."""
    settings = get_settings()
    agent = user_agent or settings.edgar.user_agent

    if not ciks:
        console.print(
            "[yellow]Warning:[/yellow] No CIKs provided. Use --ciks to specify company CIKs."
        )
        console.print("Example: --ciks 320193,789019,1318605")
        console.print("\nCommon CIKs:")
        console.print("  Apple: 320193")
        console.print("  Microsoft: 789019")
        console.print("  Tesla: 1318605")
        console.print("  Amazon: 1018724")
        console.print("  Google: 1652044")
        raise typer.Exit(1)

    cik_list = [c.strip() for c in ciks.split(",")]

    async def _discover() -> list[dict[str, object]]:
        filings_data: list[dict[str, object]] = []

        async with EdgarClient(user_agent=agent) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Discovering filings...", total=len(cik_list))

                for cik in cik_list:
                    try:
                        filings = await client.get_company_filings(
                            cik=cik,
                            form_types=[form_type] if form_type else None,
                            limit=limit // len(cik_list) or 1,
                        )

                        # Filter by year if specified
                        if year:
                            filings = [f for f in filings if f.filing_date.year == year]

                        for filing in filings:
                            filings_data.append(
                                {
                                    "company_name": filing.company.name,
                                    "ticker": filing.company.ticker,
                                    "cik": filing.company.cik,
                                    "form_type": filing.form_type,
                                    "filing_date": filing.filing_date.isoformat(),
                                    "accession_number": filing.accession_number,
                                    "primary_document": filing.primary_document,
                                    "filing_url": str(filing.filing_url),
                                }
                            )
                    except Exception as e:
                        console.print(f"[red]Error fetching CIK {cik}:[/red] {e}")

                    progress.advance(task)

        return filings_data

    filings_data = asyncio.run(_discover())

    # Save to JSON
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(filings_data, f, indent=2)

    console.print(f"\n[green]✓[/green] Discovered {len(filings_data)} filings")
    console.print(f"[green]✓[/green] Saved to {output}")


@app.command()
def download(
    input_file: Annotated[
        Path, typer.Option("--input", "-i", help="Input JSON file from discover")
    ] = Path("filings.json"),
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Output directory for downloads")
    ] = Path("cache"),
    concurrency: Annotated[
        int, typer.Option("--concurrency", "-c", help="Max concurrent downloads")
    ] = 5,
    skip_existing: Annotated[
        bool, typer.Option("--skip-existing/--no-skip", help="Skip existing files")
    ] = True,
    user_agent: Annotated[
        str | None, typer.Option("--user-agent", help="SEC API User-Agent")
    ] = None,
) -> None:
    """Download SEC filing documents."""
    if not input_file.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_file}")
        raise typer.Exit(1)

    with open(input_file) as f:
        filings_data = json.load(f)

    settings = get_settings()
    agent = user_agent or settings.edgar.user_agent

    async def _download() -> int:
        downloaded = 0

        async with Downloader(user_agent=agent, concurrency=concurrency) as downloader:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading...", total=len(filings_data))

                for filing in filings_data:
                    cik = filing["cik"].lstrip("0")
                    accession = filing["accession_number"].replace("-", "")
                    primary_doc = filing.get("primary_document")

                    if not primary_doc:
                        progress.advance(task)
                        continue

                    # Build URL
                    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}"

                    # Output path
                    ticker = filing.get("ticker") or filing["cik"]
                    filename = f"{ticker}_{filing['accession_number']}{Path(primary_doc).suffix}"
                    output_path = output_dir / filename

                    result = await downloader.download_file(
                        url, output_path, skip_existing=skip_existing
                    )

                    if result.success:
                        downloaded += 1

                    progress.advance(task)

        return downloaded

    downloaded = asyncio.run(_download())

    console.print(f"\n[green]✓[/green] Downloaded {downloaded} files to {output_dir}")


@app.command()
def analyze(
    input_dir: Annotated[
        Path, typer.Option("--input-dir", "-i", help="Directory with downloaded filings")
    ] = Path("cache"),
    keywords: Annotated[
        Path | None, typer.Option("--keywords", "-k", help="Keywords YAML file")
    ] = None,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output JSON file")] = Path(
        "results.json"
    ),
    max_matches: Annotated[
        int, typer.Option("--max-matches", "-m", help="Max matches per filing")
    ] = 50,
) -> None:
    """Analyze filings for ESG keywords."""
    if not input_dir.exists():
        console.print(f"[red]Error:[/red] Input directory not found: {input_dir}")
        raise typer.Exit(1)

    # Find all documents
    files = list(input_dir.glob("*.htm")) + list(input_dir.glob("*.html"))
    files += list(input_dir.glob("*.pdf"))

    if not files:
        console.print(f"[yellow]Warning:[/yellow] No files found in {input_dir}")
        raise typer.Exit(1)

    console.print(f"Found {len(files)} files to analyze")

    # Initialize components
    extractor = DocumentExtractor()
    analyzer = KeywordAnalyzer(keywords_path=keywords, max_matches=max_matches)

    results_data: list[dict[str, object]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing...", total=len(files))

        for filepath in files:
            try:
                # Extract text
                doc = extractor.extract(filepath)

                # Analyze
                result = analyzer.analyze(doc)

                # Convert to serializable dict
                results_data.append(
                    {
                        "filename": filepath.name,
                        "company_name": result.filing.company.name,
                        "form_type": result.filing.form_type,
                        "filing_date": result.filing.filing_date.isoformat(),
                        "total_matches": result.total_matches,
                        "environmental": result.environmental_count,
                        "social": result.social_count,
                        "governance": result.governance_count,
                        "matches": [
                            {
                                "keyword": m.keyword,
                                "category": m.category.value,
                                "subcategory": m.subcategory,
                                "sentence": m.sentence[:500],
                                "context": m.context[:1000],
                            }
                            for m in result.matches
                        ],
                    }
                )

            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Failed to analyze {filepath.name}: {e}")

            progress.advance(task)

    # Save results
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(results_data, f, indent=2)

    total_matches = sum(r["total_matches"] for r in results_data)
    console.print(f"\n[green]✓[/green] Analyzed {len(results_data)} files")
    console.print(f"[green]✓[/green] Found {total_matches} total matches")
    console.print(f"[green]✓[/green] Saved to {output}")


@app.command()
def report(
    input_file: Annotated[
        Path, typer.Option("--input", "-i", help="Input JSON file from analyze")
    ] = Path("results.json"),
    format_type: Annotated[
        str, typer.Option("--format", "-f", help="Output format: console, html, csv")
    ] = "console",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output file (for html/csv)")
    ] = None,
) -> None:
    """Generate report from analysis results."""
    if not input_file.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_file}")
        raise typer.Exit(1)

    with open(input_file) as f:
        results_data = json.load(f)

    # Convert back to AnalysisResult objects
    from datetime import date

    from esg_analyzer.analyzer.models import (
        Company,
        ESGCategory,
        Filing,
        KeywordMatch,
    )

    results: list[AnalysisResult] = []
    for data in results_data:
        company = Company(name=data["company_name"], cik="0000000000")
        filing = Filing(
            company=company,
            accession_number="0000000000-00-000000",
            form_type=data["form_type"],
            filing_date=date.fromisoformat(data["filing_date"]),
            filing_url="https://example.com",  # type: ignore[arg-type]
        )
        matches = [
            KeywordMatch(
                keyword=m["keyword"],
                category=ESGCategory(m["category"]),
                subcategory=m["subcategory"],
                sentence=m["sentence"],
                context=m["context"],
            )
            for m in data["matches"]
        ]
        results.append(
            AnalysisResult(
                filing=filing,
                total_matches=data["total_matches"],
                matches_by_category={
                    ESGCategory.ENVIRONMENTAL: data["environmental"],
                    ESGCategory.SOCIAL: data["social"],
                    ESGCategory.GOVERNANCE: data["governance"],
                },
                matches=matches,
            )
        )

    if format_type == "console":
        reporter = ConsoleReporter()
        reporter.print_summary(results)
        for result in results[:3]:  # Show details for first 3
            reporter.print_result(result, max_matches=5)

    elif format_type == "html":
        output_path = output or Path("report.html")
        reporter = HTMLReporter()
        reporter.save_report(results, output_path)
        console.print(f"[green]✓[/green] HTML report saved to {output_path}")

    elif format_type == "csv":
        output_dir = output.parent if output else Path(".")
        prefix = output.stem if output else "esg_analysis"
        exporter = CSVExporter()
        summary_path, details_path = exporter.export_all(results, output_dir, prefix)
        console.print(f"[green]✓[/green] Summary CSV saved to {summary_path}")
        console.print(f"[green]✓[/green] Details CSV saved to {details_path}")

    else:
        console.print(f"[red]Error:[/red] Unknown format: {format_type}")
        raise typer.Exit(1)


@app.command()
def run(
    ciks: Annotated[str, typer.Option("--ciks", "-c", help="Comma-separated CIKs")],
    form_type: Annotated[str, typer.Option("--form-type", "-f", help="Filing form type")] = "10-K",
    year: Annotated[int | None, typer.Option("--year", "-y", help="Filing year")] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max filings")] = 10,
    format_type: Annotated[str, typer.Option("--format", help="Output format")] = "console",
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o", help="Output directory")] = Path(
        "output"
    ),
    user_agent: Annotated[
        str | None, typer.Option("--user-agent", help="SEC API User-Agent")
    ] = None,
) -> None:
    """Run full pipeline: discover → download → analyze → report."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        filings_json = tmpdir_path / "filings.json"
        cache_dir = tmpdir_path / "cache"
        results_json = tmpdir_path / "results.json"

        # Discover
        console.print("\n[bold cyan]Step 1/4: Discovering filings...[/bold cyan]")
        discover(
            form_type=form_type,
            year=year,
            ciks=ciks,
            limit=limit,
            output=filings_json,
            user_agent=user_agent,
        )

        # Download
        console.print("\n[bold cyan]Step 2/4: Downloading filings...[/bold cyan]")
        download(
            input_file=filings_json,
            output_dir=cache_dir,
            user_agent=user_agent,
        )

        # Analyze
        console.print("\n[bold cyan]Step 3/4: Analyzing filings...[/bold cyan]")
        analyze(
            input_dir=cache_dir,
            output=results_json,
        )

        # Report
        console.print("\n[bold cyan]Step 4/4: Generating report...[/bold cyan]")

        # For persistent output, copy results and generate report in output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        if format_type == "html":
            report(
                input_file=results_json,
                format_type="html",
                output=output_dir / "report.html",
            )
        elif format_type == "csv":
            report(
                input_file=results_json,
                format_type="csv",
                output=output_dir / "analysis.csv",
            )
        else:
            report(input_file=results_json, format_type="console")

        # Copy results to output dir
        import shutil

        shutil.copy(results_json, output_dir / "results.json")

    console.print(f"\n[bold green]✓ Complete![/bold green] Results in {output_dir}")


@app.callback()
def main() -> None:
    """ESG Report Analyzer - Extract ESG disclosures from SEC filings."""
    pass


if __name__ == "__main__":
    app()
