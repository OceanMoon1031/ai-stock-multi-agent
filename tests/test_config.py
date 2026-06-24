"""Tests for configuration and Grok client setup."""

import pytest

from utils.config import ConfigurationError, PLACEHOLDER_API_KEY, get_grok_client, get_settings


def test_get_settings_reads_env(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key-123")
    monkeypatch.setenv("XAI_MODEL", "grok-4.1-fast")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.xai_api_key == "test-key-123"
    assert settings.xai_model == "grok-4.1-fast"

    get_settings.cache_clear()


def test_get_grok_client_raises_without_api_key(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError, match="XAI_API_KEY"):
        get_grok_client()

    get_settings.cache_clear()


def test_get_grok_client_raises_with_placeholder(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", PLACEHOLDER_API_KEY)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError, match="XAI_API_KEY"):
        get_grok_client()

    get_settings.cache_clear()