"""
Config -- chargement et validation de la configuration YAML/JSON.

La classe Config charge un fichier de configuration et expose ses valeurs
sous forme d'attributs (config.url, config.fetcher.delay, etc.), plutot
que via un dict brut, pour une utilisation plus lisible dans le reste du
framework.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

REQUIRED_KEYS = ["url", "pagination", "selectors", "fetcher", "store"]


class Box:
    """
    Convertit recursivement un dict en objet accessible par attribut.

    Permet d'ecrire config.fetcher.delay plutot que
    config["fetcher"]["delay"], tout en gardant un dict simple en interne.
    """

    def __init__(self, data: dict):
        self._data = data
        for key, value in data.items():
            if isinstance(value, dict):
                value = Box(value)
            setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __repr__(self):
        return f"Box({self._data})"

    def __eq__(self, other):
        if isinstance(other, Box):
            return self._data == other._data
        return NotImplemented


class Config:
    """Charge un fichier YAML ou JSON et expose ses valeurs comme attributs."""

    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Fichier de configuration introuvable : {path}")

        suffix = self.path.suffix.lower()
        with open(self.path, "r", encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif suffix == ".json":
                data = json.load(f)
            else:
                raise ValueError(
                    f"Extension de fichier non supportee : {suffix} "
                    "(attendu : .yaml, .yml ou .json)"
                )

        if not isinstance(data, dict):
            raise ValueError("Le fichier de configuration doit contenir un objet racine (dict)")

        missing = [k for k in REQUIRED_KEYS if k not in data]
        if missing:
            raise ValueError(f"Cle(s) obligatoire(s) manquante(s) dans la config : {missing}")

        self._raw = data
        self.url = data["url"]
        self.pagination = Box(data["pagination"])
        self.selectors = dict(data["selectors"])
        self.fetcher = Box(data["fetcher"])
        self.store = Box(data["store"])

        # "validator" : permet a chaque site de definir
        # ses propres champs obligatoires (ex: "citation" au lieu de "titre"
        # pour quotes.toscrape.com). Valeurs par defaut si absente, pour
        # rester compatible avec les configs existantes.
        #
        # NB: on n'utilise PAS Box ici, car Box convertirait recursivement
        # min_lengths (un dict) en objet Box, cassant Validator qui attend
        # un vrai dict (appel a .items() dessus).
        validator_defaut = {"required_fields": ["titre", "url"], "min_lengths": {}}
        validator_data = {**validator_defaut, **(data.get("validator") or {})}

        class _ValidatorConfig:
            def __init__(self, required_fields, min_lengths):
                self.required_fields = required_fields
                self.min_lengths = min_lengths

        self.validator = _ValidatorConfig(
            required_fields=validator_data["required_fields"],
            min_lengths=validator_data["min_lengths"],
        )

        # normalisation des types attendus
        self.fetcher.delay = float(self.fetcher.delay)
        self.fetcher.timeout = float(self.fetcher.timeout)
        self.fetcher.retries = int(self.fetcher.retries)

    def __repr__(self):
        return f"Config(url={self.url!r}, store={self.store.backend!r})"