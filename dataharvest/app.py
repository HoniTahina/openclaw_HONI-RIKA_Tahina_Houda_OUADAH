from __future__ import annotations
import argparse
import json
import sys
from .config import Config
from .orchestrator import Orchestrator
from .store import Store


def _backend_from_ext(path: str) -> str:
    return Store.backend_from_path(path)


def cmd_crawl(args):
    config = Config(args.config)
    orchestrator = Orchestrator(config)
    rapport = orchestrator.run(dry_run=args.dry_run)
    print(json.dumps(rapport, indent=2, ensure_ascii=False))


def cmd_export(args):
    source_backend = _backend_from_ext(args.from_path)
    cible_backend = _backend_from_ext(args.to_path)

    store = Store(source_backend, args.from_path)
    n = store.export_to(cible_backend, args.to_path)
    print(f"{n} items exportes vers {args.to_path}")


def cmd_validate(args):
    try:
        config = Config(args.config)
        print(f"Configuration valide : {config}")
        print(f"  url : {config.url}")
        print(f"  selectors : {list(config.selectors.keys())}")
        print(f"  pagination : pattern={config.pagination.get('pattern')!r} max_pages={config.pagination.get('max_pages')}")
        print(f"  store backend : {config.store.backend} -> {config.store.path}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration invalide : {e}")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dataharvest", description="DataHarvest -- framework de scraping modulaire")
    sous_parseurs = parser.add_subparsers(dest="command", required=True)

    p_crawl = sous_parseurs.add_parser("crawl", help="Lance le scraping complet")
    p_crawl.add_argument("--config", required=True, help="Chemin du fichier de config YAML/JSON")
    p_crawl.add_argument("--dry-run", action="store_true", help="Fetch + parse la 1ere page uniquement, sans stocker")
    p_crawl.set_defaults(func=cmd_crawl)

    p_export = sous_parseurs.add_parser("export", help="Exporte les items d'un backend vers un autre")
    p_export.add_argument("--from", dest="from_path", required=True)
    p_export.add_argument("--to", dest="to_path", required=True)
    p_export.set_defaults(func=cmd_export)

    p_validate = sous_parseurs.add_parser("validate", help="Valide un fichier de config sans scraper")
    p_validate.add_argument("--config", required=True)
    p_validate.set_defaults(func=cmd_validate)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
