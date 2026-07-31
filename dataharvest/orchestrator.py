"""
Orchestrator -- assemble tous les composants et pilote le scraping complet.

C'est le SEUL composant qui connait tous les autres : Config, Fetcher,
Pipeline, Validator et Store communiquent exclusivement via l'Orchestrator,
jamais directement entre eux.
"""
from __future__ import annotations

import time

from .fetcher import Fetcher
from .middleware import LoggingMiddleware, RetryMiddleware
from .pipeline import PaginationPipeline
from .validator import Validator
from .store import Store
from .detail import DetailExtractor


class Orchestrator:
    def __init__(self, config):
        self.config = config
        self.fetcher = Fetcher(
            config,
            middlewares=[LoggingMiddleware(), RetryMiddleware(config)],
        )
        self.pipeline = PaginationPipeline(
            config.selectors, config.pagination, base_url=config.url,
            row_selector=config.row_selector,
        )
        self.validator = Validator(
            required_fields=config.validator.required_fields,
            min_lengths=config.validator.min_lengths,
        )
        self.store = Store(config.store.backend, config.store.path)

        # Pattern liste -> detail (optionnel) : si active, chaque item
        # valide sera enrichi en visitant sa propre page.
        self.detail_extractor = (
            DetailExtractor(config.detail.selectors) if config.detail else None
        )

    def run(self, dry_run: bool = False) -> dict:
        """Lance le scraping complet (pagination automatique). Retourne un rapport."""
        debut = time.perf_counter()

        pages_scrapees = 0
        items_trouves = 0
        items_valides_total = 0
        items_rejetes_total = 0
        items_stockes_total = 0

        url_courante = self.config.url

        while url_courante:
            html = self.fetcher.fetch(url_courante)
            pages_scrapees += 1

            items = self.pipeline.process(html)
            items_trouves += len(items)

            valides, rejetes = self.validator.validate(items)
            items_valides_total += len(valides)
            items_rejetes_total += len(rejetes)

            # Pattern liste -> detail : enrichir chaque item valide en
            # visitant sa propre page (capitale, continent, etc.)
            if self.detail_extractor and not dry_run:
                for item in valides:
                    url_detail = item.get(self.config.detail.url_field)
                    if not url_detail:
                        continue
                    try:
                        html_detail = self.fetcher.fetch(url_detail)
                        champs_supplementaires = self.detail_extractor.extract(html_detail)
                        item.update(champs_supplementaires)
                    except Exception as e:
                        print(f"Erreur detail sur {url_detail} : {e}")
                    time.sleep(self.config.fetcher.delay)

            if dry_run:
                for item in valides:
                    print(item)
                break

            if valides:
                items_stockes_total += self.store.save(valides)

            url_suivante = self.pipeline.next_page_url(html, url_courante)
            if url_suivante == url_courante:
                break  # securite anti boucle infinie
            url_courante = url_suivante

            if url_courante:
                time.sleep(self.config.fetcher.delay)

        duree = time.perf_counter() - debut

        return self._build_report(
            pages_scrapees,
            items_valides_total,
            items_rejetes_total,
            items_stockes_total,
            items_trouves,
            duree,
        )

    def _build_report(self, fetched, valid, rejected, stored, found, duree) -> dict:
        return {
            "pages_scrapees": fetched,
            "items_trouves": found,
            "items_valides": valid,
            "items_rejetes": rejected,
            "items_stockes": stored,
            "duree_secondes": round(duree, 2),
        }