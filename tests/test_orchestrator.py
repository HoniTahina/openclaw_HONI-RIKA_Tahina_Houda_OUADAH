from unittest.mock import patch, MagicMock

import yaml

from dataharvest.config import Config
from dataharvest.orchestrator import Orchestrator


VALID_CONFIG = {
    "url": "https://example.com/",
    "pagination": {"pattern": None, "start": 1, "max_pages": 1},
    "selectors": {"titre": "h2.post-title a", "url": "h2.post-title a"},
    "fetcher": {"delay": 0.001, "retries": 1, "timeout": 5, "user_agent": "Test/1.0"},
    "store": {"backend": "json", "path": "output/test_orchestrator.json"},
}

HTML_SAMPLE = """
<html><body>
<h2 class="post-title"><a href="/a1">Article un</a></h2>
<h2 class="post-title"><a href="/a2">Article deux</a></h2>
</body></html>
"""


def make_config(tmp_path):
    data = dict(VALID_CONFIG)
    data["store"] = {"backend": "json", "path": str(tmp_path / "out.json")}
    fichier = tmp_path / "config.yaml"
    fichier.write_text(yaml.safe_dump(data), encoding="utf-8")
    return Config(str(fichier))


def test_orchestrator_run_returns_expected_keys(tmp_path):
    config = make_config(tmp_path)
    orchestrator = Orchestrator(config)

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = HTML_SAMPLE

    with patch.object(orchestrator.fetcher.session, "get", return_value=fake_response):
        rapport = orchestrator.run()

    for cle in ["pages_scrapees", "items_trouves", "items_valides", "items_rejetes", "items_stockes", "duree_secondes"]:
        assert cle in rapport

    assert rapport["pages_scrapees"] == 1
    assert rapport["items_trouves"] == 2
    assert rapport["items_valides"] == 2
    assert rapport["items_stockes"] == 2


def test_orchestrator_dry_run_does_not_store(tmp_path):
    config = make_config(tmp_path)
    orchestrator = Orchestrator(config)

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = HTML_SAMPLE

    with patch.object(orchestrator.fetcher.session, "get", return_value=fake_response):
        orchestrator.run(dry_run=True)

    assert orchestrator.store.count() == 0


def test_orchestrator_detail_pattern_enriches_items(tmp_path):
    data = dict(VALID_CONFIG)
    data["store"] = {"backend": "json", "path": str(tmp_path / "out_detail.json")}
    data["detail"] = {
        "url_field": "url",
        "selectors": {"extra": {"mode": "label_lookup", "label": "Info"}},
    }
    fichier = tmp_path / "config_detail.yaml"
    fichier.write_text(yaml.safe_dump(data), encoding="utf-8")
    config = Config(str(fichier))
    orchestrator = Orchestrator(config)

    html_liste = HTML_SAMPLE
    html_detail = "<table><tr><th>Info</th><td>valeur trouvee</td></tr></table>"

    reponses = [html_liste, html_detail, html_detail]

    def fake_get(*args, **kwargs):
        r = MagicMock()
        r.status_code = 200
        r.text = reponses.pop(0)
        return r

    with patch.object(orchestrator.fetcher.session, "get", side_effect=fake_get):
        rapport = orchestrator.run()

    assert rapport["items_stockes"] == 2

    import json
    stockes = json.load(open(tmp_path / "out_detail.json"))
    assert all(item["extra"] == "valeur trouvee" for item in stockes)