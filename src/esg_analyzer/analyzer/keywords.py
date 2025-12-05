"""Keyword matching engine for ESG analysis."""

import re
from collections import defaultdict
from pathlib import Path

from esg_analyzer.analyzer.models import (
    AnalysisResult,
    ESGCategory,
    ExtractedDocument,
    KeywordMatch,
)
from esg_analyzer.config import load_keywords


class KeywordAnalyzer:
    """Analyze documents for ESG-related keywords.

    Loads keyword taxonomy from YAML config and matches keywords
    in document text, extracting context around each match.

    Example:
        analyzer = KeywordAnalyzer()
        result = analyzer.analyze(extracted_document)

        for match in result.matches:
            print(f"{match.category}/{match.subcategory}: {match.keyword}")
            print(f"  Context: {match.context[:100]}...")
    """

    def __init__(
        self,
        keywords_path: Path | None = None,
        context_window: int = 1,
        max_matches: int = 50,
        case_sensitive: bool = False,
    ) -> None:
        """Initialize keyword analyzer.

        Args:
            keywords_path: Path to keywords.yaml file
            context_window: Number of sentences before/after match to include
            max_matches: Maximum matches to return per document
            case_sensitive: Whether matching is case-sensitive
        """
        self.keywords = load_keywords(keywords_path)
        self.context_window = context_window
        self.max_matches = max_matches
        self.case_sensitive = case_sensitive

        # Build compiled patterns for efficient matching
        self._patterns: dict[str, list[tuple[re.Pattern[str], str, str]]] = {}
        self._build_patterns()

    def _build_patterns(self) -> None:
        """Build compiled regex patterns for all keywords."""
        flags = 0 if self.case_sensitive else re.IGNORECASE

        for category, subcategories in self.keywords.items():
            self._patterns[category] = []
            for subcategory, keyword_list in subcategories.items():
                for keyword in keyword_list:
                    # Use word boundaries to avoid partial matches
                    # Escape special regex characters in keyword
                    pattern = re.compile(
                        r"\b" + re.escape(keyword) + r"\b",
                        flags,
                    )
                    self._patterns[category].append((pattern, subcategory, keyword))

    def analyze(self, document: ExtractedDocument) -> AnalysisResult:
        """Analyze a document for ESG keywords.

        Args:
            document: Extracted document to analyze

        Returns:
            AnalysisResult with all matches and statistics
        """
        text = document.content
        sentences = self._split_sentences(text)

        matches: list[KeywordMatch] = []
        seen_contexts: set[str] = set()  # Deduplicate by context

        # Track counts
        category_counts: dict[ESGCategory, int] = defaultdict(int)
        subcategory_counts: dict[str, int] = defaultdict(int)

        # Search for each keyword pattern
        for category, patterns in self._patterns.items():
            esg_category = ESGCategory(category)

            for pattern, subcategory, keyword in patterns:
                # Find all sentences containing this keyword
                for i, sentence in enumerate(sentences):
                    if pattern.search(sentence):
                        # Build context with surrounding sentences
                        start_idx = max(0, i - self.context_window)
                        end_idx = min(len(sentences), i + self.context_window + 1)
                        context = " ".join(sentences[start_idx:end_idx])

                        # Deduplicate by context
                        context_key = context[:200]  # First 200 chars as key
                        if context_key in seen_contexts:
                            continue
                        seen_contexts.add(context_key)

                        # Create match
                        match = KeywordMatch(
                            keyword=keyword,
                            category=esg_category,
                            subcategory=subcategory,
                            sentence=sentence.strip(),
                            context=context.strip(),
                            page_number=None,  # Could be added with page-aware extraction
                        )
                        matches.append(match)

                        # Update counts
                        category_counts[esg_category] += 1
                        subcategory_counts[subcategory] += 1

                        # Check limit
                        if len(matches) >= self.max_matches:
                            break

                if len(matches) >= self.max_matches:
                    break
            if len(matches) >= self.max_matches:
                break

        return AnalysisResult(
            filing=document.filing,
            total_matches=len(matches),
            matches_by_category=dict(category_counts),
            matches_by_subcategory=dict(subcategory_counts),
            matches=matches,
        )

    def analyze_batch(
        self,
        documents: list[ExtractedDocument],
    ) -> list[AnalysisResult]:
        """Analyze multiple documents.

        Args:
            documents: List of extracted documents

        Returns:
            List of AnalysisResults
        """
        return [self.analyze(doc) for doc in documents]

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Uses a simple regex-based approach that handles common cases:
        - Period, question mark, exclamation followed by space and capital
        """
        # Simple sentence splitting on . ! ? followed by space and capital letter
        # This is a simplified approach that works for most cases
        pattern = r"(?<=[.!?])\s+(?=[A-Z])"

        sentences = re.split(pattern, text)

        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def get_keyword_count(self) -> dict[str, dict[str, int]]:
        """Get count of keywords by category and subcategory.

        Returns:
            Nested dict: category -> subcategory -> keyword count
        """
        counts: dict[str, dict[str, int]] = {}
        for category, subcategories in self.keywords.items():
            counts[category] = {}
            for subcategory, keyword_list in subcategories.items():
                counts[category][subcategory] = len(keyword_list)
        return counts

    def get_all_keywords(self) -> list[str]:
        """Get flat list of all keywords.

        Returns:
            List of all keywords across all categories
        """
        all_keywords: list[str] = []
        for subcategories in self.keywords.values():
            for keyword_list in subcategories.values():
                all_keywords.extend(keyword_list)
        return all_keywords


def quick_analyze(
    text: str,
    keywords_path: Path | None = None,
) -> dict[str, list[str]]:
    """Quick keyword analysis without full document structure.

    Useful for testing or simple analysis.

    Args:
        text: Text to analyze
        keywords_path: Optional path to keywords file

    Returns:
        Dict mapping categories to list of found keywords
    """
    keywords = load_keywords(keywords_path)
    found: dict[str, list[str]] = defaultdict(list)

    for category, subcategories in keywords.items():
        for keyword_list in subcategories.values():
            for keyword in keyword_list:
                pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
                if pattern.search(text) and keyword not in found[category]:
                    found[category].append(keyword)

    return dict(found)
