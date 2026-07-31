"""
Store -- persistance des items valides, 3 backends interchangeables.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path


class Store:
    BACKENDS = ("csv", "sqlite", "json")
    @classmethod
    def backend_from_path(cls, path: str) -> str:
        """Déduit le backend à partir de l'extension du fichier."""

        suffix = Path(path).suffix.lower()

        if suffix in (".db", ".sqlite"):
            return "sqlite"

        if suffix == ".csv":
            return "csv"

        if suffix == ".json":
            return "json"

        raise ValueError(
            f"Impossible de déduire le backend depuis l'extension : {path}"
        )

    def __init__(self, backend: str, path: str):
        if backend not in self.BACKENDS:
            raise ValueError(f"Backend inconnu: {backend}")
        self.backend = backend
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.backend == "sqlite":
            self._init_sqlite()

    def _init_sqlite(self):
        with sqlite3.connect(self.path) as cx:
            cx.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    data TEXT NOT NULL
                )
                """
            )
            cx.commit()

    def save(self, items: list[dict]) -> int:
        """Persiste les items. Retourne le nombre d'items REELLEMENT inseres (hors doublons)."""
        if self.backend == "csv":
            return self._save_csv(items)
        if self.backend == "sqlite":
            return self._save_sqlite(items)
        if self.backend == "json":
            return self._save_json(items)
        raise ValueError(f"Backend inconnu: {self.backend}")

    def _save_csv(self, items: list[dict]) -> int:
        if not items:
            return 0
        fichier_existe = self.path.exists() and self.path.stat().st_size > 0
        fieldnames = list(items[0].keys())

        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if not fichier_existe:
                writer.writeheader()
            writer.writerows(items)
        return len(items)

    def _save_sqlite(self, items: list[dict]) -> int:
        """
        Insère les nouvelles URL et met à jour les items existants.

        Le nombre retourné correspond uniquement aux nouvelles lignes.
        """

        inserted = 0

        with sqlite3.connect(self.path) as connection:
            for item in items:
                url = item.get("url")

                if not url:
                    continue

                data = json.dumps(item, ensure_ascii=False)

                existing_item = connection.execute(
                    "SELECT 1 FROM items WHERE url = ?",
                    (url,),
                ).fetchone()

                connection.execute(
                    """
                    INSERT INTO items (url, data)
                    VALUES (?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        data = excluded.data
                    """,
                    (url, data),
                )

                if existing_item is None:
                    inserted += 1

            connection.commit()

        return inserted

    def _save_json(self, items: list[dict]) -> int:
        existants = self._load_all_items() if self.path.exists() else []
        urls_existantes = {it.get("url") for it in existants if it.get("url")}
        nouveaux = [it for it in items if it.get("url") not in urls_existantes]

        tout = existants + nouveaux
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(tout, f, ensure_ascii=False, indent=2)

        return len(nouveaux)

    def count(self) -> int:
        """Retourne le nombre total d'items dans le store."""
        if self.backend == "csv":
            if not self.path.exists():
                return 0
            with open(self.path, "r", encoding="utf-8") as f:
                return max(sum(1 for _ in f) - 1, 0)  # -1 pour l'entete
        if self.backend == "sqlite":
            with sqlite3.connect(self.path) as cx:
                return cx.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        if self.backend == "json":
            return len(self._load_all_items())
        return 0

    def _load_all_items(self) -> list[dict]:
        if self.backend == "csv":
            if not self.path.exists():
                return []
            with open(self.path, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        if self.backend == "sqlite":
            with sqlite3.connect(self.path) as cx:
                rows = cx.execute("SELECT data FROM items").fetchall()
                return [json.loads(r[0]) for r in rows]
        if self.backend == "json":
            if not self.path.exists() or self.path.stat().st_size == 0:
                return []
            with open(self.path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def export_to(self, other_backend: str, path: str) -> int:
        """Exporte tous les items vers un autre backend. Retourne le nb exporte."""
        items = self._load_all_items()
        cible = Store(other_backend, path)
        return cible.save(items)
