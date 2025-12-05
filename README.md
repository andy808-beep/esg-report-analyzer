# ESG Report Analyzer

[![CI](https://github.com/andy808-beep/esg-report-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/andy808-beep/esg-report-analyzer/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A CLI tool that automatically discovers, downloads, and analyzes corporate ESG/sustainability disclosures from SEC EDGAR filings using keyword extraction.

## Features

- 🔍 **Discover** — Search SEC EDGAR for 10-K filings and proxy statements
- 📥 **Download** — Batch download filings with async concurrency
- 📄 **Extract** — Pull text from PDF and HTML filings
- 🎯 **Analyze** — Match 100+ ESG keywords across Environmental, Social, and Governance categories
- 📊 **Report** — Generate console, HTML, or CSV reports with highlighted findings

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/andy808-beep/esg-report-analyzer.git
cd esg-report-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .

# For development (includes testing tools)
pip install -e ".[dev]"
```

### Basic Usage

Run the full pipeline with a single command:

```bash
# Analyze Apple and Microsoft's latest 10-K filings
esg-analyzer run --ciks 320193,789019 --form-type 10-K --limit 2 --format html

# Output saved to ./output/report.html
```

### Step-by-Step Usage

```bash
# 1. Discover filings from SEC EDGAR
esg-analyzer discover --ciks 320193,789019 --form-type 10-K --year 2024 --output filings.json

# 2. Download the filings
esg-analyzer download --input filings.json --output-dir ./cache/

# 3. Analyze for ESG keywords
esg-analyzer analyze --input-dir ./cache/ --output results.json

# 4. Generate a report
esg-analyzer report --input results.json --format html --output report.html
```

## CLI Reference

```
esg-analyzer --help

Commands:
  discover   Search SEC EDGAR for filings
  download   Download filing documents
  analyze    Run keyword analysis
  report     Generate output report
  run        Full pipeline in one command
```

### Common Company CIKs

| Company | CIK |
|---------|-----|
| Apple | 320193 |
| Microsoft | 789019 |
| Tesla | 1318605 |
| Amazon | 1018724 |
| Google (Alphabet) | 1652044 |
| Meta | 1326801 |
| NVIDIA | 1045810 |
| JPMorgan Chase | 19617 |

## Configuration

### Keyword Taxonomy

The analyzer uses a configurable keyword taxonomy in `config/keywords.yaml`:

```yaml
environmental:
  climate:
    - "carbon neutrality"
    - "net zero"
    - "Scope 1"
    - "Scope 2"
    - "Scope 3"
    - "greenhouse gas"
    
social:
  labor:
    - "workplace safety"
    - "labor rights"
    
governance:
  board:
    - "board diversity"
    - "independent directors"
```

### Settings

Runtime settings in `config/settings.yaml`:

```yaml
edgar:
  user_agent: "YourApp your@email.com"  # Required by SEC
  requests_per_second: 10

download:
  concurrency: 5
  max_retries: 3

analysis:
  context_window: 1  # Sentences around match
  max_matches_per_report: 50
```

## Output Formats

### Console Output

```
╭──────────────────────────── ESG Report Analysis ─────────────────────────────╮
│ Microsoft Corporation (MSFT)                                                 │
│ 10-K — 2024-07-30                                                           │
╰──────────────────────────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Category      ┃ Matches ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Environmental │      12 │
│ Social        │      38 │
│ Governance    │       8 │
│ Total         │      58 │
└───────────────┴─────────┘
```

### HTML Report

Generates a standalone HTML file with:
- Summary cards for E/S/G totals
- Sortable filing table
- Detailed matches with highlighted keywords
- Dark theme with modern styling

### CSV Export

Two files:
- `summary.csv` — One row per filing with aggregate counts
- `details.csv` — One row per keyword match with context

## Project Structure

```
esg-report-analyzer/
├── src/esg_analyzer/
│   ├── cli.py              # Typer CLI commands
│   ├── config.py           # Settings & keywords loader
│   ├── scraper/
│   │   ├── edgar.py        # SEC EDGAR API client
│   │   └── downloader.py   # Async file downloader
│   ├── extractor/
│   │   └── pdf.py          # PDF/HTML text extraction
│   ├── analyzer/
│   │   ├── models.py       # Pydantic data models
│   │   └── keywords.py     # Keyword matching engine
│   └── reporter/
│       ├── console.py      # Rich terminal output
│       ├── html.py         # HTML report generator
│       └── csv_export.py   # CSV exporter
├── config/
│   ├── keywords.yaml       # ESG keyword taxonomy
│   └── settings.yaml       # Runtime settings
├── tests/                  # Pytest test suite
└── output/                 # Generated reports
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run linter
ruff check src tests

# Format code
ruff format src tests

# Type check
mypy src
```

## How It Works

1. **SEC EDGAR API**: Uses the official SEC API to search for company filings by CIK (Central Index Key) and form type
2. **Async Downloads**: Downloads multiple filings concurrently with rate limiting to respect SEC's 10 req/sec limit
3. **Text Extraction**: Extracts text from HTML filings using BeautifulSoup, and from PDFs using pypdf
4. **Keyword Matching**: Searches for ESG-related keywords using regex with word boundaries, capturing surrounding context
5. **Report Generation**: Aggregates results and generates formatted output in multiple formats

## Technical Stack

- **httpx** — Async HTTP client for SEC API
- **BeautifulSoup4** — HTML parsing and text extraction
- **pypdf** — PDF text extraction
- **Pydantic** — Data validation and serialization
- **Typer** — CLI framework
- **Rich** — Terminal formatting and progress bars

## Limitations

- SEC filings only (U.S. public companies)
- Keyword matching is literal (no semantic/ML analysis)
- PDF extraction quality depends on document structure
- Rate limited to SEC's 10 requests/second

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Andy Wang — [GitHub](https://github.com/andy808-beep)
