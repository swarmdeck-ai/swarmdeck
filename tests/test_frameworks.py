"""Tests for framework detection."""

from unittest.mock import patch

from swarmdeck.frameworks import detect
from swarmdeck.frameworks.crewai import detect as detect_crewai
from swarmdeck.frameworks.langgraph import detect as detect_langgraph
from swarmdeck.frameworks.autogen import detect as detect_autogen


def test_detect_returns_list():
    result = detect()
    assert isinstance(result, list)


def test_detect_crewai_not_installed():
    with patch("importlib.util.find_spec", return_value=None):
        assert detect_crewai() is None


def test_detect_langgraph_not_installed():
    with patch("importlib.util.find_spec", return_value=None):
        assert detect_langgraph() is None


def test_detect_autogen_not_installed():
    with patch("importlib.util.find_spec", return_value=None):
        assert detect_autogen() is None
