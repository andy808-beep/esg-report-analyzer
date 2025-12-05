"""PDF and HTML text extraction for SEC filings."""

import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from esg_analyzer.analyzer.models import ExtractedDocument, Filing


class ExtractionError(Exception):
    """Raised when text extraction fails."""


class PDFExtractor:
    """Extract text content from PDF documents.

    Handles SEC filing PDFs, with fallback for encrypted or corrupted files.

    Example:
        extractor = PDFExtractor()
        result = extractor.extract_from_file(Path("filing.pdf"), filing)
        print(result.content[:500])
    """

    def __init__(self, normalize_whitespace: bool = True) -> None:
        """Initialize extractor.

        Args:
            normalize_whitespace: Collapse multiple spaces/newlines into single space
        """
        self.normalize_whitespace = normalize_whitespace

    def extract_from_file(
        self,
        filepath: Path,
        filing: Filing | None = None,
    ) -> ExtractedDocument:
        """Extract text from a PDF file.

        Args:
            filepath: Path to PDF file
            filing: Optional Filing metadata to attach

        Returns:
            ExtractedDocument with extracted text

        Raises:
            ExtractionError: If extraction fails
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise ExtractionError(f"File not found: {filepath}")

        try:
            reader = PdfReader(filepath)
            page_count = len(reader.pages)

            # Extract text from all pages
            text_parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

            content = "\n\n".join(text_parts)

            if self.normalize_whitespace:
                content = self._normalize_text(content)

            # Create a minimal filing if none provided
            if filing is None:
                from esg_analyzer.analyzer.models import Company

                filing = Filing(
                    company=Company(name="Unknown", cik="0000000000"),
                    accession_number="0000000000-00-000000",
                    form_type="Unknown",
                    filing_date=datetime.now().date(),
                    filing_url="https://example.com",  # type: ignore[arg-type]
                )

            return ExtractedDocument(
                filing=filing,
                filename=filepath.name,
                content=content,
                page_count=page_count,
            )

        except PdfReadError as e:
            raise ExtractionError(f"Failed to read PDF {filepath}: {e}") from e
        except Exception as e:
            raise ExtractionError(f"Extraction failed for {filepath}: {e}") from e

    def extract_from_bytes(
        self,
        data: bytes,
        filename: str,
        filing: Filing | None = None,
    ) -> ExtractedDocument:
        """Extract text from PDF bytes.

        Args:
            data: PDF file content as bytes
            filename: Name for the document
            filing: Optional Filing metadata

        Returns:
            ExtractedDocument with extracted text
        """
        import io

        try:
            reader = PdfReader(io.BytesIO(data))
            page_count = len(reader.pages)

            text_parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

            content = "\n\n".join(text_parts)

            if self.normalize_whitespace:
                content = self._normalize_text(content)

            if filing is None:
                from esg_analyzer.analyzer.models import Company

                filing = Filing(
                    company=Company(name="Unknown", cik="0000000000"),
                    accession_number="0000000000-00-000000",
                    form_type="Unknown",
                    filing_date=datetime.now().date(),
                    filing_url="https://example.com",  # type: ignore[arg-type]
                )

            return ExtractedDocument(
                filing=filing,
                filename=filename,
                content=content,
                page_count=page_count,
            )

        except Exception as e:
            raise ExtractionError(f"Extraction failed for {filename}: {e}") from e

    def _normalize_text(self, text: str) -> str:
        """Normalize whitespace in extracted text.

        - Replace multiple spaces with single space
        - Replace multiple newlines with double newline (paragraph break)
        - Strip leading/trailing whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        return text.strip()


class HTMLExtractor:
    """Extract text content from HTML documents.

    Handles SEC filing HTML documents (10-K, DEF 14A, etc.).
    Strips HTML tags and extracts readable text content.

    Example:
        extractor = HTMLExtractor()
        result = extractor.extract_from_file(Path("filing.htm"), filing)
    """

    def __init__(self, normalize_whitespace: bool = True) -> None:
        """Initialize extractor.

        Args:
            normalize_whitespace: Collapse multiple spaces/newlines
        """
        self.normalize_whitespace = normalize_whitespace

    def extract_from_file(
        self,
        filepath: Path,
        filing: Filing | None = None,
    ) -> ExtractedDocument:
        """Extract text from an HTML file.

        Args:
            filepath: Path to HTML file
            filing: Optional Filing metadata

        Returns:
            ExtractedDocument with extracted text
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise ExtractionError(f"File not found: {filepath}")

        try:
            # Try different encodings
            content = None
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(filepath, encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise ExtractionError(f"Could not decode {filepath}")

            text = self._extract_text_from_html(content)

            if filing is None:
                from esg_analyzer.analyzer.models import Company

                filing = Filing(
                    company=Company(name="Unknown", cik="0000000000"),
                    accession_number="0000000000-00-000000",
                    form_type="Unknown",
                    filing_date=datetime.now().date(),
                    filing_url="https://example.com",  # type: ignore[arg-type]
                )

            return ExtractedDocument(
                filing=filing,
                filename=filepath.name,
                content=text,
                page_count=None,  # HTML doesn't have pages
            )

        except Exception as e:
            raise ExtractionError(f"Extraction failed for {filepath}: {e}") from e

    def extract_from_string(
        self,
        html_content: str,
        filename: str,
        filing: Filing | None = None,
    ) -> ExtractedDocument:
        """Extract text from HTML string.

        Args:
            html_content: HTML content as string
            filename: Name for the document
            filing: Optional Filing metadata

        Returns:
            ExtractedDocument with extracted text
        """
        text = self._extract_text_from_html(html_content)

        if filing is None:
            from esg_analyzer.analyzer.models import Company

            filing = Filing(
                company=Company(name="Unknown", cik="0000000000"),
                accession_number="0000000000-00-000000",
                form_type="Unknown",
                filing_date=datetime.now().date(),
                filing_url="https://example.com",  # type: ignore[arg-type]
            )

        return ExtractedDocument(
            filing=filing,
            filename=filename,
            content=text,
            page_count=None,
        )

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract readable text from HTML content.

        Removes scripts, styles, and extracts text from remaining elements.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "meta", "link", "head"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        if self.normalize_whitespace:
            text = self._normalize_text(text)

        return text

    def _normalize_text(self, text: str) -> str:
        """Normalize whitespace in extracted text."""
        # Replace multiple spaces with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        # Remove empty lines but keep paragraph breaks
        lines = [line for line in lines if line]
        text = "\n".join(lines)
        return text.strip()


class DocumentExtractor:
    """Unified extractor that handles both PDF and HTML documents.

    Automatically detects file type and uses appropriate extractor.

    Example:
        extractor = DocumentExtractor()
        result = extractor.extract(Path("filing.pdf"), filing)
    """

    def __init__(self, normalize_whitespace: bool = True) -> None:
        """Initialize with both PDF and HTML extractors."""
        self.pdf_extractor = PDFExtractor(normalize_whitespace=normalize_whitespace)
        self.html_extractor = HTMLExtractor(normalize_whitespace=normalize_whitespace)

    def extract(
        self,
        filepath: Path,
        filing: Filing | None = None,
    ) -> ExtractedDocument:
        """Extract text from a document file.

        Automatically detects PDF vs HTML based on file extension.

        Args:
            filepath: Path to document file
            filing: Optional Filing metadata

        Returns:
            ExtractedDocument with extracted text

        Raises:
            ExtractionError: If extraction fails or file type unknown
        """
        filepath = Path(filepath)
        suffix = filepath.suffix.lower()

        if suffix == ".pdf":
            return self.pdf_extractor.extract_from_file(filepath, filing)
        elif suffix in (".htm", ".html"):
            return self.html_extractor.extract_from_file(filepath, filing)
        else:
            raise ExtractionError(f"Unsupported file type: {suffix}")

    def extract_batch(
        self,
        filepaths: list[Path],
        filings: list[Filing] | None = None,
        skip_errors: bool = True,
    ) -> list[ExtractedDocument]:
        """Extract text from multiple documents.

        Args:
            filepaths: List of file paths
            filings: Optional list of Filing metadata (same order as filepaths)
            skip_errors: If True, skip files that fail extraction

        Returns:
            List of ExtractedDocuments (may be shorter than input if skip_errors)
        """
        results: list[ExtractedDocument] = []

        for i, filepath in enumerate(filepaths):
            filing = filings[i] if filings and i < len(filings) else None

            try:
                doc = self.extract(filepath, filing)
                results.append(doc)
            except ExtractionError as e:
                if skip_errors:
                    print(f"Warning: Skipping {filepath}: {e}")
                else:
                    raise

        return results
