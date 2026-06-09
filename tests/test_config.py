from glycomass.config import Settings, get_settings


def test_defaults():
    s = Settings()
    assert s.environment == "development"
    assert s.log_json is False


def test_env_prefix_override(monkeypatch):
    monkeypatch.setenv("GLYCOMASS_LOG_JSON", "true")
    monkeypatch.setenv("GLYCOMASS_ENVIRONMENT", "production")
    s = Settings()
    assert s.log_json is True
    assert s.environment == "production"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
