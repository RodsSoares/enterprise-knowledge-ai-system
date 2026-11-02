from pathlib import Path
from unittest.mock import Mock

import pytest

from app.ingestion.ingestion_router import IngestionRouter, SUPPORTED_SUFFIXES
from app.ingestion.schemas import NormalizedContent, TextBlock


def normalized_content() -> NormalizedContent:
    return NormalizedContent(
        blocks=(
            TextBlock(
                block_id="text-00000",
                order=0,
                kind="paragraph",
                text="Canonical content.",
            ),
        )
    )


@pytest.mark.parametrize(
    "filename",
    [
        "policy.pdf",
        "procedure.docx",
        "matrix.xlsx",
        "training.pptx",
        "guideline.md",
    ],
)
def test_router_exposes_supported_formats_without_parser_details(filename):
    router = IngestionRouter(document_parser=Mock())

    assert router.supports(Path(filename)) is True


def test_router_support_check_is_case_insensitive():
    router = IngestionRouter(document_parser=Mock())

    assert router.supports(Path("POLICY.PDF")) is True
    assert router.supports(Path("MATRIX.XLSX")) is True


def test_router_rejects_unknown_extension_before_dispatch(tmp_path):
    source = tmp_path / "evidence.csv"
    source.write_text("a,b\n1,2", encoding="utf-8")
    parser = Mock()
    router = IngestionRouter(document_parser=parser)

    with pytest.raises(ValueError, match="Unsupported ingestion format"):
        router.parse(source)

    parser.parse.assert_not_called()


def test_router_rejects_non_path_input():
    router = IngestionRouter(document_parser=Mock())

    with pytest.raises(TypeError, match="pathlib.Path"):
        router.parse("policy.pdf")  # type: ignore[arg-type]


def test_router_rejects_missing_file(tmp_path):
    router = IngestionRouter(document_parser=Mock())

    with pytest.raises(FileNotFoundError):
        router.parse(tmp_path / "missing.pdf")


def test_router_dispatches_and_returns_canonical_contract(tmp_path):
    source = tmp_path / "policy.pdf"
    source.write_bytes(b"placeholder")
    expected = normalized_content()
    parser = Mock()
    parser.parse.return_value = expected
    router = IngestionRouter(document_parser=parser)

    actual = router.parse(source)

    parser.parse.assert_called_once_with(source)
    assert actual is expected


def test_router_rejects_noncanonical_parser_output(tmp_path):
    source = tmp_path / "policy.pdf"
    source.write_bytes(b"placeholder")
    parser = Mock()
    parser.parse.return_value = object()
    router = IngestionRouter(document_parser=parser)

    with pytest.raises(TypeError, match="NormalizedContent"):
        router.parse(source)


def test_supported_suffixes_match_public_contract():
    assert SUPPORTED_SUFFIXES == frozenset(
        {".pdf", ".docx", ".xlsx", ".pptx", ".md"}
    )
