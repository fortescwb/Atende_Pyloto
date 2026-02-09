#!/usr/bin/env python3
"""Migra estados antigos numericos de sessao para strings canonicas.

Uso:
    python scripts/migrate_session_states.py --project-id meu-projeto --apply

Padrao: dry-run (nao escreve nada).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from google.cloud import firestore

OLD_TO_NEW: dict[int, str] = {
    1: "INITIAL",
    2: "TRIAGE",
    3: "COLLECTING_INFO",
    4: "GENERATING_RESPONSE",
    5: "HANDOFF_HUMAN",
    6: "SELF_SERVE_INFO",
    7: "ROUTE_EXTERNAL",
    8: "SCHEDULED_FOLLOWUP",
    9: "TIMEOUT",
    10: "ERROR",
}


@dataclass(frozen=True)
class MigrationStats:
    scanned: int = 0
    updatable: int = 0
    updated: int = 0
    unknown_state: int = 0


def migrate_sessions(project_id: str | None, *, apply: bool) -> MigrationStats:
    client = firestore.Client(project=project_id) if project_id else firestore.Client()
    stats = MigrationStats()

    for doc in client.collection("sessions").stream():
        stats = MigrationStats(
            scanned=stats.scanned + 1,
            updatable=stats.updatable,
            updated=stats.updated,
            unknown_state=stats.unknown_state,
        )
        data = doc.to_dict() or {}
        raw_state = data.get("current_state")
        if not isinstance(raw_state, int):
            continue

        mapped = OLD_TO_NEW.get(raw_state)
        if mapped is None:
            stats = MigrationStats(
                scanned=stats.scanned,
                updatable=stats.updatable,
                updated=stats.updated,
                unknown_state=stats.unknown_state + 1,
            )
            continue

        stats = MigrationStats(
            scanned=stats.scanned,
            updatable=stats.updatable + 1,
            updated=stats.updated,
            unknown_state=stats.unknown_state,
        )
        if apply:
            doc.reference.update({"current_state": mapped})
            stats = MigrationStats(
                scanned=stats.scanned,
                updatable=stats.updatable,
                updated=stats.updated + 1,
                unknown_state=stats.unknown_state,
            )

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-id",
        default=None,
        help="Project ID do Firestore. Se omitido, usa configuracao padrao.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica atualizacoes no Firestore. Sem esta flag executa dry-run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = migrate_sessions(args.project_id, apply=args.apply)
    mode = "apply" if args.apply else "dry-run"
    print(
        f"[{mode}] scanned={stats.scanned} "
        f"updatable={stats.updatable} updated={stats.updated} "
        f"unknown_state={stats.unknown_state}"
    )


if __name__ == "__main__":
    main()
