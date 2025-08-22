import os
import sys
import re
import pytest

# Import from the package
from search_s3.core import (
    compile_pattern, matches_pattern, format_size, truncate_text,
    parse_arguments, display_results, get_terminal_width
)


def test_compile_pattern_literal():
    pattern = compile_pattern("abc", "literal")
    assert pattern == "abc"


def test_compile_pattern_regex_case_sensitive():
    pattern = compile_pattern("a.+c", "case_sensitive")
    assert isinstance(pattern, re.Pattern)
    assert pattern.pattern == "a.+c"


def test_compile_pattern_regex_case_insensitive():
    pattern = compile_pattern("ABC", "case_insensitive")
    assert pattern.flags & re.IGNORECASE


def test_matches_pattern_literal():
    pattern = "foo"
    assert matches_pattern("foobar", pattern, "literal")
    assert not matches_pattern("bar", pattern, "literal")


def test_matches_pattern_regex():
    pattern = re.compile(r"foo.+")
    assert matches_pattern("foobar", pattern, "case_sensitive")


def test_format_size():
    assert format_size(1023) == "1023.0B"
    assert format_size(1024) == "1.0KB"
    assert format_size(1024 * 1024) == "1.0MB"


def test_truncate_text():
    assert truncate_text("hello", 10) == "hello"
    assert truncate_text("hello world", 8) == "hello..."


def test_parse_arguments_positional(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["search_s3.py", "term", "bucket"])
    term, bucket, raw, stacked, csv, csv_file, term_excl, bucket_excl, regex_mode = parse_arguments()
    assert term == "term"
    assert bucket == "bucket"
    assert not raw
    assert regex_mode == "literal"


def test_parse_arguments_flags(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["search_s3.py", "--term", "t", "--bucket", "b", "--regex-ignore-case"])
    term, bucket, raw, stacked, csv, csv_file, term_excl, bucket_excl, regex_mode = parse_arguments()
    assert term == "t"
    assert bucket == "b"
    assert regex_mode == "case_insensitive"


def test_parse_arguments_missing_term(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["search_s3.py"])
    with pytest.raises(SystemExit):
        parse_arguments()


def test_display_results_raw(capsys):
    results = [{
        "Bucket": "bucket",
        "Key": "key",
        "Size": 1024,
        "LastModified": "2024-01-01T00:00:00",
        "StorageClass": "STANDARD",
    }]
    display_results(results, raw_output=True)
    captured = capsys.readouterr().out
    assert "Bucket\tKey\tSize\tLastModified\tStorageClass" in captured
    assert "bucket\tkey\t1.0KB\t2024-01-01T00:00:00\tSTANDARD" in captured


def test_display_results_table(monkeypatch, capsys):
    results = [{
        "Bucket": "bucket",
        "Key": "key",
        "Size": 1024,
        "LastModified": "2024-01-01T00:00:00",
        "StorageClass": "STANDARD",
    }]
    monkeypatch.setattr(sys.modules[__name__], "get_terminal_width", lambda: 80)
    display_results(results)
    captured = capsys.readouterr().out
    assert "Bucket" in captured
    assert "key" in captured
