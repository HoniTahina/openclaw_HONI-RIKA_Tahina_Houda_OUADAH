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
        # selectors reste un dict simple (pas un Box), comme demande par la spec
        self.selectors = dict(data["selectors"])
        self.fetcher = Box(data["fetcher"])
        self.store = Box(data["store"])

        # row_selector (optionnel) : active le mode "par ligne" de
        # GenericPipeline, plus robuste que la selection a plat quand une
        # meme cellule peut contenir plusieurs elements matchant un
        # selecteur (ex: plusieurs liens/noms alternatifs par ligne).
        self.row_selector = data.get("row_selector")

        # Section optionnelle "validator" : permet a chaque site de definir
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

        # Section optionnelle "detail" : active le pattern liste -> detail.
        # Si presente, l'Orchestrator visitera l'URL de chaque item valide
        # pour en extraire des champs supplementaires (ex: capitale,
        # continent) via dataharvest.detail.DetailExtractor.
        #
        # NB: meme piege que pour "validator" -- pas de Box ici, "selectors"
        # doit rester un vrai dict (avec des dicts imbriques pour les modes
        # avances), pas un objet Box.
        detail_data = data.get("detail")
        if detail_data:
            class _DetailConfig:
                def __init__(self, url_field, selectors):
                    self.url_field = url_field
                    self.selectors = selectors

            self.detail = _DetailConfig(
                url_field=detail_data.get("url_field", "url"),
                selectors=detail_data["selectors"],
            )
        else:
            self.detail = None

        # normalisation des types attendus
        self.fetcher.delay = float(self.fetcher.delay)
        self.fetcher.timeout = float(self.fetcher.timeout)
        self.fetcher.retries = int(self.fetcher.retries)

    def __repr__(self):
        return f"Config(url={self.url!r}, store={self.store.backend!r})"