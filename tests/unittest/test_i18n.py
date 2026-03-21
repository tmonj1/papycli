"""i18n モジュールのテスト。"""

import pytest

from papycli.i18n import h, is_japanese


def test_is_japanese_lang(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert is_japanese() is True


def test_is_japanese_lc_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LC_ALL", "ja_JP.UTF-8")
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert is_japanese() is True


def test_is_japanese_lc_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LC_MESSAGES", "ja")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    assert is_japanese() is True


def test_is_japanese_lc_all_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """LC_ALL=C が設定されていれば LANG=ja でも英語になる。"""
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert is_japanese() is False


def test_is_japanese_english(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert is_japanese() is False


def test_is_japanese_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    assert is_japanese() is False


def test_h_returns_english_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    assert h("English", "日本語") == "English"


def test_h_returns_japanese_when_locale_is_ja(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert h("English", "日本語") == "日本語"
