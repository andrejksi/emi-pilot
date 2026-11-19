from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

    a: dict[str, list[str]] = {}
    b: dict[str, list[dict[str, str]]] = {}


def test_nested_env_value_decodes_to_list_of_dicts(monkeypatch):
    """New: APP_B__X JSON-decodes a list of dictionaries into the outer dictionary's x entry (A1)."""
    monkeypatch.setenv("APP_A__X", '["v"]')
    monkeypatch.setenv("APP_B__X", '[{"k": "v"}]')

    assert Settings().b == {"x": [{"k": "v"}]}


def test_nested_env_value_still_decodes_to_list_of_strings(monkeypatch):
    """Guard: APP_A__X continues to JSON-decode a list of strings into the dictionary's x entry (A2)."""
    monkeypatch.setenv("APP_A__X", '["v"]')
    monkeypatch.delenv("APP_B__X", raising=False)

    assert Settings().a == {"x": ["v"]}
