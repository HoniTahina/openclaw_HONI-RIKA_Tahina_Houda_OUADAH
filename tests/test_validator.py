from dataharvest.validator import Validator
def test_validate_rejects_missing_required_field():
    validator = Validator(required_fields=["titre", "url"])
    items = [{"titre": "Test"}]  # url manquant

    valides, rejetes = validator.validate(items)
    assert valides == []
    assert len(rejetes) == 1


def test_validate_rejects_invalid_url():
    validator = Validator(required_fields=["titre", "url"])
    items = [{"titre": "Test", "url": "pas-une-url"}]

    valides, rejetes = validator.validate(items)
    assert valides == []
    assert len(rejetes) == 1


def test_validate_accepts_valid_item():
    validator = Validator(required_fields=["titre", "url"])
    items = [{"titre": "Test", "url": "https://example.com/page"}]

    valides, rejetes = validator.validate(items)
    assert len(valides) == 1
    assert rejetes == []


def test_validate_min_lengths():
    validator = Validator(required_fields=["titre"], min_lengths={"titre": 5})
    items = [{"titre": "abc"}]

    valides, rejetes = validator.validate(items)
    assert valides == []
    assert len(rejetes) == 1


def test_validate_min_lengths_accepts_long_enough():
    validator = Validator(required_fields=["titre"], min_lengths={"titre": 5})
    items = [{"titre": "titre suffisamment long"}]

    valides, rejetes = validator.validate(items)
    assert len(valides) == 1
    assert rejetes == []

def test_is_valid_url():
    validator = Validator(required_fields=[])
    assert validator.is_valid_url("https://example.com") is True
    assert validator.is_valid_url("http://example.com/page") is True
    assert validator.is_valid_url("ftp://example.com") is False
    assert validator.is_valid_url("pas-une-url") is False
    assert validator.is_valid_url("") is False
    assert validator.is_valid_url(None) is False
