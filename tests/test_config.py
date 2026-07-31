import json

import pytest
import yaml

from dataharvest.config import Config


VALID_CONFIG = {
    "url": "https://example.com/",
    "pagination": {"pattern": "/page/{n}/", "start": 1, "max_pages": 3},
    "selectors": {"titre": "h2 a", "url": "h2 a"},
    "fetcher": {"delay": 1.5, "retries": 3, "timeout": 10, "user_agent": "Test/1.0"},
    "store": {"backend": "json", "path": "output/test.json"},
}


def test_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        Config("fichier_qui_nexiste_pas.yaml")


def test_config_missing_required_key(tmp_path):
    data = dict(VALID_CONFIG)
    del data["selectors"]
    fichier = tmp_path / "bad.yaml"
    fichier.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError):
        Config(str(fichier))


def test_config_loads_yaml_valid(tmp_path):
    fichier = tmp_path / "good.yaml"
    fichier.write_text(yaml.safe_dump(VALID_CONFIG), encoding="utf-8")

    config = Config(str(fichier))
    assert config.url == "https://example.com/"
    assert isinstance(config.fetcher.delay, float)
    assert config.fetcher.delay == 1.5
    assert isinstance(config.selectors, dict)


def test_config_loads_json_valid(tmp_path):
    fichier = tmp_path / "good.json"
    fichier.write_text(json.dumps(VALID_CONFIG), encoding="utf-8")

    config = Config(str(fichier))
    assert config.store.backend == "json"


def test_config_unsupported_extension(tmp_path):
    fichier = tmp_path / "config.txt"
    fichier.write_text("url: https://example.com", encoding="utf-8")

    with pytest.raises(ValueError):
        Config(str(fichier))


def test_config_pagination_attributes(tmp_path):
    fichier = tmp_path / "good.yaml"
    fichier.write_text(yaml.safe_dump(VALID_CONFIG), encoding="utf-8")

    config = Config(str(fichier))
    assert config.pagination.pattern == "/page/{n}/"
    assert config.pagination.max_pages == 3