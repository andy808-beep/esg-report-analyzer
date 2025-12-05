# ESG Report Analyzer

A CLI tool that automatically discovers, downloads, and analyzes corporate ESG/sustainability disclosures from SEC EDGAR filings using keyword extraction.

## Features

- 🔍 **Discover** — Search SEC EDGAR for 10-K filings and proxy statements
- 📥 **Download** — Batch download filings with async concurrency
- 📄 **Extract** — Pull text from PDF and HTML filings
- 🎯 **Analyze** — Match ESG keywords across Environmental, Social, and Governance categories
- 📊 **Report** — Generate console, HTML, or CSV reports with highlighted findings

## Installation

```bash
# Clone the repository
git clone https://github.com/andy808-beep/esg-report-analyzer.git
cd esg-report-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# For development
pip install -e ".[dev]"
```

## Quick Start

```bash
# Run the full pipeline: discover → download → analyze → report
esg-analyzer run --form-type 10-K --year 2023 --limit 50 --format html

# Or run each step individually:

# 1. Discover filings from SEC EDGAR
esg-analyzer discover --form-type 10-K --year 2023 --output filings.json --limit 50

# 2. Download the filings
esg-analyzer download --input filings.json --output-dir ./cache/

# 3. Analyze for ESG keywords
esg-analyzer analyze --input-dir ./cache/ --keywords config/keywords.yaml --output results.json

# 4. Generate a report
esg-analyzer report --input results.json --format html --output report.html
```

## Configuration

### Keyword Taxonomy

Edit `config/keywords.yaml` to customize ESG keywords:

```yaml
environmental:
  climate:
    - "carbon neutrality"
    - "net zero"
    - "Scope 1"
    - "Scope 2"
    - "Scope 3"

social:
  labor:
    - "workplace safety"
    - "labor rights"

governance:
  board:
    - "board diversity"
    - "independent directors"
```

## Project Structure

```
esg-report-analyzer/
├── src/esg_analyzer/
│   ├── cli.py              # Typer CLI commands
│   ├── scraper/            # SEC EDGAR scraping
│   ├── extractor/          # PDF/HTML text extraction
│   ├── analyzer/           # Keyword matching
│   └── reporter/           # Output generation
├── config/
│   └── keywords.yaml       # ESG keyword taxonomy
├── tests/                  # Pytest test suite
└── output/                 # Generated reports
```

## Development

```bash
# Run linter
make lint

# Format code
make format

# Run tests
make test

# Run tests with coverage
make coverage
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Andy Wang — [GitHub](https://github.com/andy808-beep)

