from __future__ import annotations

from core.config import load_app_config


def test_load_app_config_from_example() -> None:
    config = load_app_config("config.example.yaml")
    assert config["app"]["interface"] == "streamlit"
    assert config["app"]["logging_enabled"] is True
    assert config["logging"]["schema"] == "wvs"
