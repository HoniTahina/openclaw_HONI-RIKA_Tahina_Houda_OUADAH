import argparse
from unittest.mock import patch, MagicMock
import pytest
import yaml
from dataharvest.app import cmd_crawl, cmd_export, cmd_validate, build_parser, _backend_from_ext
from dataharvest.store import Store


VALID_CONFIG = {
    "url": "https://example.com/",
    "pagination": {"pattern": None, "start": 1, "max_pages": 1},
    "selectors": {"titre": "h2 a", "url": "h2 a"},
    "fetcher": {"delay": 0.001, "retries": 1, "timeout": 5, "user_agent": "Test/1.0"},
    "store": {"backend": "json", "path": "output/test_app.json"},
}


def make_config_file(tmp_path, data=None):
    data = data or VALID_CONFIG
    fichier = tmp_path / "config.yaml"
    fichier.write_text(yaml.safe_dump(data), encoding="utf-8")
    return str(fichier)


def test_backend_from_ext():
    assert _backend_from_ext("out.csv") == "csv"
    assert _backend_from_ext("out.json") == "json"
    assert _backend_from_ext("out.db") == "sqlite"
    with pytest.raises(ValueError):
        _backend_from_ext("out.xyz")


def test_build_parser_crawl():
    parser = build_parser()
    args = parser.parse_args(["crawl", "--config", "conf.yaml"])
    assert args.command == "crawl"
    assert args.config == "conf.yaml"
    assert args.dry_run is False


def test_build_parser_dry_run_flag():
    parser = build_parser()
    args = parser.parse_args(["crawl", "--config", "conf.yaml", "--dry-run"])
    assert args.dry_run is True


def test_cmd_validate_valid_config(tmp_path, capsys):
    chemin = make_config_file(tmp_path)
    args = argparse.Namespace(config=chemin)

    cmd_validate(args)

    sortie = capsys.readouterr().out
    assert "Configuration valide" in sortie


def test_cmd_validate_invalid_config(tmp_path, capsys):
    args = argparse.Namespace(config=str(tmp_path / "nexiste_pas.yaml"))

    with pytest.raises(SystemExit):
        cmd_validate(args)

    sortie = capsys.readouterr().out
    assert "Configuration invalide" in sortie


def test_cmd_export(tmp_path, capsys):
    path_json = tmp_path / "in.json"
    path_csv = tmp_path / "out.csv"

    store = Store("json", str(path_json))
    store.save([{"titre": "A", "url": "https://a.com"}])

    args = argparse.Namespace(from_path=str(path_json), to_path=str(path_csv))
    cmd_export(args)

    assert path_csv.exists()
    sortie = capsys.readouterr().out
    assert "items exportes" in sortie


def test_cmd_crawl_dry_run(tmp_path, capsys):
    data = dict(VALID_CONFIG)
    data["store"] = {"backend": "json", "path": str(tmp_path / "out.json")}
    chemin = make_config_file(tmp_path, data)

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "<html><h2 a><a href='/a'>Item</a></h2></html>"

    args = argparse.Namespace(config=chemin, dry_run=True)

    with patch("requests.Session.get", return_value=fake_response):
        cmd_crawl(args)

    sortie = capsys.readouterr().out
    assert "pages_scrapees" in sortie
