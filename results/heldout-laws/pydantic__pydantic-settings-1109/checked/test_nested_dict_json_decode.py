from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

    a: dict[str, list[str]] = {}
    b: dict[str, list[dict[str, str]]] = {}


def test_dict_of_list_of_dict_env_value_is_json_decoded(monkeypatch):
    """New: APP_B__X='[{"k": "v"}]' gives b == {"x": [{"k": "v"}]} for b: dict[str, list[dict[str, str]]] (A1)."""
    monkeypatch.setenv("APP_B__X", '[{"k": "v"}]')
    assert Settings().b == {"x": [{"k": "v"}]}


def test_dict_of_list_of_str_env_value_is_json_decoded(monkeypatch):
    """Guard: APP_A__X='["v"]' still gives a == {"x": ["v"]} for a: dict[str, list[str]] (A2)."""
    monkeypatch.setenv("APP_A__X", '["v"]')
    assert Settings().a == {"x": ["v"]}


def test_both_fields_decoded_together(monkeypatch):
    """New: with APP_A__X='["v"]' and APP_B__X='[{"k": "v"}]' both set, Settings() gives a == {"x": ["v"]} and b == {"x": [{"k": "v"}]} (A1, A2)."""
    monkeypatch.setenv("APP_A__X", '["v"]')
    monkeypatch.setenv("APP_B__X", '[{"k": "v"}]')
    s = Settings()
    assert (s.a, s.b) == ({"x": ["v"]}, {"x": [{"k": "v"}]})
