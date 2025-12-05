"""Tests for the document extractor module."""

import tempfile
from pathlib import Path

import pytest

from esg_analyzer.extractor import (
    DocumentExtractor,
    ExtractionError,
    HTMLExtractor,
    PDFExtractor,
)


class TestHTMLExtractor:
    """Tests for HTMLExtractor class."""

    def test_extract_simple_html(self) -> None:
        """Test extracting text from simple HTML."""
        extractor = HTMLExtractor()

        html_content = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Annual Report</h1>
            <p>This is a test paragraph about carbon neutrality.</p>
            <p>Another paragraph about sustainability.</p>
        </body>
        </html>
        """

        result = extractor.extract_from_string(html_content, "test.htm")

        assert "Annual Report" in result.content
        assert "carbon neutrality" in result.content
        assert "sustainability" in result.content
        assert "<html>" not in result.content
        assert "<p>" not in result.content

    def test_extract_removes_scripts(self) -> None:
        """Test that script tags are removed."""
        extractor = HTMLExtractor()

        html_content = """
        <html>
        <body>
            <p>Visible text</p>
            <script>alert('hidden');</script>
            <p>More visible text</p>
        </body>
        </html>
        """

        result = extractor.extract_from_string(html_content, "test.htm")

        assert "Visible text" in result.content
        assert "More visible text" in result.content
        assert "alert" not in result.content

    def test_extract_removes_styles(self) -> None:
        """Test that style tags are removed."""
        extractor = HTMLExtractor()

        html_content = """
        <html>
        <head><style>body { color: red; }</style></head>
        <body><p>Content</p></body>
        </html>
        """

        result = extractor.extract_from_string(html_content, "test.htm")

        assert "Content" in result.content
        assert "color: red" not in result.content

    def test_extract_from_file(self, tmp_path: Path) -> None:
        """Test extracting from HTML file."""
        html_file = tmp_path / "test.htm"
        html_file.write_text(
            "<html><body><p>File content about ESG.</p></body></html>"
        )

        extractor = HTMLExtractor()
        result = extractor.extract_from_file(html_file)

        assert "File content about ESG" in result.content
        assert result.filename == "test.htm"

    def test_extract_file_not_found(self) -> None:
        """Test error on missing file."""
        extractor = HTMLExtractor()

        with pytest.raises(ExtractionError):
            extractor.extract_from_file(Path("/nonexistent/file.htm"))

    def test_normalize_whitespace(self) -> None:
        """Test whitespace normalization."""
        extractor = HTMLExtractor(normalize_whitespace=True)

        html_content = """
        <html><body>
            <p>Text   with    extra     spaces.</p>


            <p>And multiple newlines.</p>
        </body></html>
        """

        result = extractor.extract_from_string(html_content, "test.htm")

        # Should not have excessive spaces or newlines
        assert "   " not in result.content


class TestPDFExtractor:
    """Tests for PDFExtractor class."""

    def test_extract_file_not_found(self) -> None:
        """Test error on missing file."""
        extractor = PDFExtractor()

        with pytest.raises(ExtractionError):
            extractor.extract_from_file(Path("/nonexistent/file.pdf"))


class TestDocumentExtractor:
    """Tests for DocumentExtractor class."""

    def test_extract_html_by_extension(self, tmp_path: Path) -> None:
        """Test that .htm files are handled by HTML extractor."""
        html_file = tmp_path / "test.htm"
        html_file.write_text("<html><body><p>HTML content</p></body></html>")

        extractor = DocumentExtractor()
        result = extractor.extract(html_file)

        assert "HTML content" in result.content

    def test_extract_html_extension(self, tmp_path: Path) -> None:
        """Test that .html files are handled."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>Content</p></body></html>")

        extractor = DocumentExtractor()
        result = extractor.extract(html_file)

        assert "Content" in result.content

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        """Test error on unsupported file type."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Plain text")

        extractor = DocumentExtractor()

        with pytest.raises(ExtractionError):
            extractor.extract(txt_file)

    def test_extract_batch(self, tmp_path: Path) -> None:
        """Test batch extraction."""
        # Create test files
        file1 = tmp_path / "test1.htm"
        file1.write_text("<html><body><p>File 1</p></body></html>")

        file2 = tmp_path / "test2.htm"
        file2.write_text("<html><body><p>File 2</p></body></html>")

        extractor = DocumentExtractor()
        results = extractor.extract_batch([file1, file2])

        assert len(results) == 2
        assert "File 1" in results[0].content
        assert "File 2" in results[1].content

    def test_extract_batch_skip_errors(self, tmp_path: Path) -> None:
        """Test batch extraction with skip_errors."""
        file1 = tmp_path / "test1.htm"
        file1.write_text("<html><body><p>Valid file</p></body></html>")

        file2 = tmp_path / "nonexistent.htm"  # Doesn't exist

        extractor = DocumentExtractor()
        results = extractor.extract_batch([file1, file2], skip_errors=True)

        assert len(results) == 1
        assert "Valid file" in results[0].content
