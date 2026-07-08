"""Unit tests for the pure text-extraction helpers.

These need no Azure or Meilisearch connection — they exercise the extension
dispatch and plain-text decoding paths that every indexed blob goes through.
"""
from app.extractors import extension_of, is_extractable, extract_text


def test_extension_of():
    assert extension_of("2026/03/invoice-081.pdf") == "pdf"
    assert extension_of("report.FINAL.DOCX") == "docx"
    assert extension_of("no_extension") == ""
    assert extension_of("archive/README") == ""


def test_is_extractable():
    assert is_extractable("notes.txt")
    assert is_extractable("deck.pdf")
    assert is_extractable("contract.docx")
    assert not is_extractable("photo.jpg")
    assert not is_extractable("clip.mp4")


def test_extract_text_plain_and_truncation():
    data = b"hello world, searchable text"
    assert extract_text("a.txt", data, 1000) == "hello world, searchable text"
    # respects the char cap
    assert extract_text("a.txt", data, 5) == "hello"


def test_extract_text_never_raises_on_bad_bytes():
    # invalid utf-8 must degrade gracefully, not blow up the crawl
    assert isinstance(extract_text("a.log", b"\xff\xfe garbage", 1000), str)
    # unknown/binary type yields empty string, never an exception
    assert extract_text("photo.jpg", b"\x00\x01\x02", 1000) == ""
