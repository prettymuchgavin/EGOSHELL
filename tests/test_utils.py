"""Tests for utility functions."""

from egoshell.utils import extract_json

def test_extract_json_clean():
    text = '{"tool": "web_search", "args": {"query": "pytest"}}'
    assert extract_json(text) == {"tool": "web_search", "args": {"query": "pytest"}}

def test_extract_json_surrounding_text():
    text = 'Some text before {"tool": "web_search", "args": {"query": "pytest"}} some text after.'
    assert extract_json(text) == {"tool": "web_search", "args": {"query": "pytest"}}

def test_extract_json_nested():
    text = '{"tool": "nested", "args": {"a": {"b": {"c": 1}}}}'
    assert extract_json(text) == {"tool": "nested", "args": {"a": {"b": {"c": 1}}}}

def test_extract_json_braces_in_string():
    text = '{"tool": "diary", "args": {"content": "Braces { } inside string"}}'
    assert extract_json(text) == {"tool": "diary", "args": {"content": "Braces { } inside string"}}

def test_extract_json_escaped_quotes():
    text = '{"tool": "diary", "args": {"content": "Quotes \\" } inside string"}}'
    assert extract_json(text) == {"tool": "diary", "args": {"content": "Quotes \" } inside string"}}

def test_extract_json_invalid():
    assert extract_json('{"tool": "incomplete"') is None
    assert extract_json('plain text') is None
