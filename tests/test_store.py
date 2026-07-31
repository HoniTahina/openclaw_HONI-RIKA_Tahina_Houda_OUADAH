import json
import pytest
from dataharvest.store import Store


def test_store_invalid_backend_raises():
    with pytest.raises(ValueError):
        Store("xml", "output/test.xml")


def test_store_json_creates_valid_file(tmp_path):
    path = tmp_path / "items.json"
    store = Store("json", str(path))

    n = store.save([{"titre": "A", "url": "https://a.com"}])
    assert n == 1
    assert path.exists()

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1


def test_store_json_no_duplicate_on_same_url(tmp_path):
    path = tmp_path / "items.json"
    store = Store("json", str(path))

    item = {"titre": "A", "url": "https://a.com"}
    store.save([item])
    n2 = store.save([item])

    assert n2 == 0
    assert store.count() == 1


def test_store_sqlite_no_duplicate_on_same_url(tmp_path):
    path = tmp_path / "items.db"
    store = Store("sqlite", str(path))

    item = {"titre": "A", "url": "https://a.com"}
    store.save([item])
    store.save([item])

    assert store.count() == 1


def test_store_csv_creates_file(tmp_path):
    path = tmp_path / "items.csv"
    store = Store("csv", str(path))

    n = store.save([{"titre": "A", "url": "https://a.com"}])
    assert n == 1
    assert path.exists()


def test_store_count_empty_store(tmp_path):
    path = tmp_path / "empty.json"
    store = Store("json", str(path))
    assert store.count() == 0


def test_store_export_to(tmp_path):
    path_json = tmp_path / "items.json"
    path_sqlite = tmp_path / "items.db"

    store_json = Store("json", str(path_json))
    store_json.save([{"titre": "A", "url": "https://a.com"}])

    n = store_json.export_to("sqlite", str(path_sqlite))
    assert n == 1

    store_sqlite = Store("sqlite", str(path_sqlite))
    assert store_sqlite.count() == 1
