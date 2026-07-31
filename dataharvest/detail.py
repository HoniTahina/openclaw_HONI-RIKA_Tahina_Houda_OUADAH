"""
detail.py -- Extension du framework pour le pattern "liste -> detail".

Certains sites (ex: Wikipedia) affichent l'essentiel sur une page liste,
mais des champs supplementaires (capitale, continent...) ne sont
disponibles que sur la fiche individuelle de chaque item. DetailExtractor
va chercher ces champs sur une page HTML donnee (la fiche), avec 3 modes
de selection possibles :

- "css" (par defaut) : selecteur CSS classique, comme dans GenericPipeline
  (supporte aussi {selector, attr} pour lire un attribut precis)
- "label_lookup" : cherche une ligne <tr> dont le <th> contient un
  libelle donne (ex: "Capitale"), et retourne le contenu du <td> associe.
  Utile pour les tableaux "infobox" de type libelle/valeur, tres courants
  sur Wikipedia et les sites de fiches produit/entreprise.
- "category_pattern" : cherche parmi les <link rel="mw:PageProp/Category">
  (categories Wikipedia, rendu Parsoid) celle qui correspond a un motif
  regex donne, et retourne le nom associe. Tres specifique a Wikipedia.
"""
from __future__ import annotations

import re
from urllib.parse import unquote

from bs4 import BeautifulSoup


class DetailExtractor:
    def __init__(self, selectors: dict):
        self.selectors = selectors

    def extract(self, html: str) -> dict:
        if not html:
            return {champ: "" for champ in self.selectors}

        soup = BeautifulSoup(html, "lxml")
        resultat = {}
        for champ, spec in self.selectors.items():
            resultat[champ] = self._extraire_champ(soup, spec)
        return resultat

    def _extraire_champ(self, soup: BeautifulSoup, spec) -> str:
        if not isinstance(spec, dict):
            spec = {"mode": "css", "selector": spec}

        mode = spec.get("mode", "css")

        try:
            if mode == "css":
                return self._mode_css(soup, spec)
            if mode == "label_lookup":
                return self._mode_label_lookup(soup, spec)
            if mode == "category_pattern":
                return self._mode_category_pattern(soup, spec)
        except Exception:
            return ""

        return ""

    def _mode_css(self, soup: BeautifulSoup, spec: dict) -> str:
        selecteur = spec.get("selector", "")
        attr = spec.get("attr", "text")
        el = soup.select_one(selecteur)
        if not el:
            return ""
        if attr == "text":
            return el.get_text(strip=True)
        if attr == "href":
            return el.get("href", "")
        if attr == "class":
            classes = el.get("class") or []
            return classes[-1] if len(classes) > 1 else " ".join(classes)
        return (el.get(attr) or "").strip()

    def _mode_label_lookup(self, soup: BeautifulSoup, spec: dict) -> str:
        """Cherche un <tr> dont le <th> contient le libelle donne."""
        label = spec.get("label", "").strip().lower()
        for tr in soup.select("tr"):
            th, td = tr.find("th"), tr.find("td")
            if th and td and label in th.get_text(strip=True).lower():
                lien = td.find("a")
                return lien.get_text(strip=True) if lien else td.get_text(" ", strip=True)
        return ""

    def _mode_category_pattern(self, soup: BeautifulSoup, spec: dict) -> str:
        """Cherche parmi les <link rel='mw:PageProp/Category'> un motif regex."""
        patterns = spec.get("patterns", {})
        liens = soup.find_all("link", rel=lambda r: r and "Category" in r)
        for lien in liens:
            href = unquote(lien.get("href", ""))
            for nom, motif in patterns.items():
                if re.search(motif, href):
                    return nom
        return ""