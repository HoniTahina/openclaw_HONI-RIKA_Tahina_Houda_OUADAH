from __future__ import annotations
import logging
from urllib.parse import urlparse

logger = logging.getLogger("dataharvest")


class Validator:
    def __init__(self, required_fields: list[str], min_lengths: dict | None = None):
        self.required_fields = required_fields
        self.min_lengths = min_lengths or {}

    def is_valid_url(self, url: str) -> bool:
        
        if not url or not isinstance(url, str):
            return False
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def validate(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        
        valides, rejetes = [], []

        for item in items:
            motif = self._motif_rejet(item)
            if motif:
                logger.warning("Item rejete (%s) : %s", motif, item)
                rejetes.append(item)
            else:
                valides.append(item)

        return valides, rejetes

    def _motif_rejet(self, item: dict) -> str | None:
        for champ in self.required_fields:
            if not item.get(champ):
                return f"champ obligatoire manquant ou vide : {champ}"

        if item.get("url") and not self.is_valid_url(item["url"]):
            return "url invalide"

        for champ, longueur_min in self.min_lengths.items():
            valeur = item.get(champ, "")
            if len(valeur) < longueur_min:
                return f"{champ} trop court (< {longueur_min} caracteres)"

        return None
