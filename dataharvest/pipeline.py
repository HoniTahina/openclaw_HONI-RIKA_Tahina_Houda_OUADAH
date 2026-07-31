"""
Pipeline -- extraction des donnees structurees depuis le HTML brut.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urljoin

from bs4 import BeautifulSoup


class BasePipeline(ABC):
    @abstractmethod
    def process(self, html: str) -> list[dict]:
        """Retourne TOUJOURS une liste, jamais None."""

    @abstractmethod
    def next_page_url(self, html: str, current_url: str) -> str | None:
        """Retourne l'URL de la page suivante ou None si fin."""


class GenericPipeline(BasePipeline):
    """
    Pipeline generique pilotee entierement par les selecteurs CSS de la
    config -- aucun selecteur n'est code en dur ici.

    Strategie : le premier champ des selectors sert de "reference" pour
    determiner combien d'items il y a sur la page (on suppose que tous
    les champs ont le meme nombre d'occurrences, une par item/carte).
    """

    def __init__(self, selectors: dict, base_url: str = ""):
        self.selectors = selectors
        self.base_url = base_url

    def process(self, html: str) -> list[dict]:
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        champs = list(self.selectors.keys())
        if not champs:
            return []

        premier_champ = champs[0]
        selecteur_ref, _ = self._decomposer_spec(self.selectors[premier_champ])
        elements_reference = soup.select(selecteur_ref)
        if not elements_reference:
            return []

        # on pre-calcule tous les matches par champ une seule fois
        matches_par_champ = {}
        attrs_par_champ = {}
        for champ, spec in self.selectors.items():
            selecteur, attr = self._decomposer_spec(spec)
            matches_par_champ[champ] = soup.select(selecteur)
            attrs_par_champ[champ] = attr

        items = []
        for i in range(len(elements_reference)):
            item = {}
            for champ in champs:
                trouves = matches_par_champ[champ]
                if i >= len(trouves):
                    item[champ] = ""
                    continue
                item[champ] = self._extraire_valeur(trouves[i], champ, attrs_par_champ[champ])
            items.append(item)

        return items

    def _decomposer_spec(self, spec) -> tuple[str, str]:
        """
        Un selecteur peut etre :
          - une simple chaine CSS : "h2.post-title a"  -> extraction texte (ou href si champ 'url')
          - un dict {selector, attr} : {"selector": "p.star-rating", "attr": "class"}
            -> extraction d'un attribut HTML precis (utile quand la donnee
               est encodee dans un attribut plutot que dans le texte visible,
               ex: la note books.toscrape.com est dans class="star-rating Three")
        """
        if isinstance(spec, dict):
            return spec.get("selector") or spec.get("css", ""), spec.get("attr", "text")
        return spec, "text"

    def _extraire_valeur(self, el, champ: str, attr: str = "text") -> str:
        """
        Extrait la valeur pertinente d'un element BeautifulSoup.
        Ne leve jamais d'exception : retourne "" en cas de souci.
        """
        try:
            if attr == "href":
                href = el.get("href")
                return urljoin(self.base_url, href) if href else ""

            if attr == "class":
                classes = el.get("class") or []
                # convention frequente : la 2e classe porte la valeur variable
                # (ex: "star-rating Three" -> "Three")
                return classes[-1] if len(classes) > 1 else " ".join(classes)

            if attr not in ("text", "href", "class"):
                # attribut HTML arbitraire (ex: "datetime", "data-id"...)
                return (el.get(attr) or "").strip()

            # comportement par defaut (attr == "text")
            if champ == "url" and el.name == "a" and el.get("href"):
                return urljoin(self.base_url, el["href"])
            if el.get("datetime"):
                return el["datetime"].strip()
            return el.get_text(strip=True)
        except Exception:
            return ""

    def next_page_url(self, html: str, current_url: str) -> str | None:
        return None


class PaginationPipeline(GenericPipeline):
    """
    Etend GenericPipeline avec la gestion de la pagination : construit
    l'URL de la page suivante selon le pattern de config.pagination, et
    s'arrete quand max_pages est atteint ou que la page ne contient plus
    d'items.
    """

    def __init__(self, selectors: dict, pagination_config, base_url: str = ""):
        super().__init__(selectors, base_url=base_url)
        self.pagination_config = pagination_config
        self._page_actuelle = getattr(pagination_config, "start", 1)

    def next_page_url(self, html: str, current_url: str) -> str | None:
        pattern = getattr(self.pagination_config, "pattern", None)
        max_pages = getattr(self.pagination_config, "max_pages", 1)

        if not pattern:
            return None

        # arreter si la page courante ne contenait deja plus d'items
        if not self.process(html):
            return None

        self._page_actuelle += 1
        if self._page_actuelle > max_pages:
            return None

        chemin = pattern.replace("{n}", str(self._page_actuelle))
        return urljoin(self.base_url or current_url, chemin)