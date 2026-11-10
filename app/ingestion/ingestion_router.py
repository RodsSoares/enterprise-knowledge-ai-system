"""Public ingestion facade for heterogeneous enterprise documents.

Downstream consumers submit a source path without knowing which parser or
enricher is used internally. Format-specific infrastructure remains private to
the ingestion layer.
"""

from pathlib import Path

from app.ingestion.docling_parser import DoclingParser
from app.ingestion.document_parser import DocumentParser
from app.ingestion.pptx_native_enricher import PptxNativeEnricher
from app.ingestion.schemas import NormalizedContent
from app.ingestion.xlsx_parser import XlsxParser


SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".xlsx", ".pptx", ".md", ".txt"})


class IngestionRouter:
    """Single public entry point for physical document parsing."""

    def __init__(self, document_parser: DocumentParser | None = None) -> None:
        self._document_parser = document_parser or DocumentParser(
            docling_parser=DoclingParser(),
            xlsx_parser=XlsxParser(),
            pptx_native_enricher=PptxNativeEnricher(),
        )

    @property
    def supported_suffixes(self) -> frozenset[str]:
        """Return formats currently materialized by the ingestion implementation."""
        return SUPPORTED_SUFFIXES

    def supports(self, source_path: Path) -> bool:
        """Return whether the file extension has a configured ingestion route."""
        if not isinstance(source_path, Path):
            raise TypeError("source_path must be a pathlib.Path.")
        return source_path.suffix.lower() in SUPPORTED_SUFFIXES

    def parse(self, source_path: Path) -> NormalizedContent:
        """Parse one supported source through the appropriate internal route."""
        if not isinstance(source_path, Path):
            raise TypeError("source_path must be a pathlib.Path.")
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        if not source_path.is_file():
            raise ValueError(f"Ingestion source must be a file: {source_path}")

        suffix = source_path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
            raise ValueError(
                f"Unsupported ingestion format: {suffix or '<none>'}. "
                f"Supported formats: {supported}"
            )

        content = self._document_parser.parse(source_path)
        if not isinstance(content, NormalizedContent):
            raise TypeError(
                "Ingestion route must return a NormalizedContent instance."
            )
        return content
