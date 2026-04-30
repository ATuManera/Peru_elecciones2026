#!/usr/bin/env python3
"""Corrige la base SQLite del scraper ONPE marcando como NOT_FOUND
cualquier fila fuera de los rangos válidos conocidos.

Rangos válidos conocidos:
- 000001 .. 088064
- 900001 .. 904703

Qué hace:
1. Crea backup .pre_fix_all_outside_ranges.bak si no existe.
2. Muestra resumen previo.
3. En --apply, cambia a NOT_FOUND los registros fuera de los rangos válidos
   cuyo status esté en PENDING / FAILED_TEMP / FAILED_FINAL / INVALID_RESPONSE.
4. Mantiene intactos los DETAIL_OK ya descargados.
5. Muestra resumen posterior y chequeos.

Uso:
    python3 fix_onpe_sqlite_all_outside_ranges.py --db ./data/state/onpe_scraper.sqlite
    python3 fix_onpe_sqlite_all_outside_ranges.py --db ./data/state/onpe_scraper.sqlite --apply
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path

from project_metadata import build_argument_parser

VALID_RANGES = (("000001", "088064"), ("900001", "904703"))
MUTABLE_STATUSES = ("PENDING", "FAILED_TEMP", "FAILED_FINAL", "INVALID_RESPONSE")
BACKUP_SUFFIX = ".pre_fix_all_outside_ranges.bak"


def q1(cur: sqlite3.Cursor, sql: str, params: tuple = ()) -> int:
    row = cur.execute(sql, params).fetchone()
    return int(row[0] if row and row[0] is not None else 0)


def print_status_summary(cur: sqlite3.Cursor) -> None:
    rows = cur.execute(
        "SELECT status, COUNT(*) FROM mesas GROUP BY status ORDER BY status"
    ).fetchall()
    for status, count in rows:
        print(f"{status}: {count}")


def main() -> int:
    parser = build_argument_parser(
        description="Corrige SQLite marcando como NOT_FOUND filas fuera de rangos válidos"
    )
    parser.add_argument("--db", required=True, type=Path, help="Ruta al archivo SQLite")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios")
    args = parser.parse_args()

    db_path = args.db
    if not db_path.exists():
        raise SystemExit(f"No existe la base: {db_path}")

    backup_path = db_path.with_name(db_path.name + BACKUP_SUFFIX)
    if backup_path.exists():
        print(f"Backup ya existía: {backup_path}")
    else:
        shutil.copy2(db_path, backup_path)
        print(f"Backup creado: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    try:
        total = q1(cur, "SELECT COUNT(*) FROM mesas")
        outside_total = q1(
            cur,
            """
            SELECT COUNT(*)
            FROM mesas
            WHERE NOT (
                codigo_mesa BETWEEN ? AND ?
                OR codigo_mesa BETWEEN ? AND ?
            )
            """,
            (VALID_RANGES[0][0], VALID_RANGES[0][1], VALID_RANGES[1][0], VALID_RANGES[1][1]),
        )
        outside_mutable = q1(
            cur,
            """
            SELECT COUNT(*)
            FROM mesas
            WHERE NOT (
                codigo_mesa BETWEEN ? AND ?
                OR codigo_mesa BETWEEN ? AND ?
            )
              AND status IN (?, ?, ?, ?)
            """,
            (
                VALID_RANGES[0][0], VALID_RANGES[0][1],
                VALID_RANGES[1][0], VALID_RANGES[1][1],
                *MUTABLE_STATUSES,
            ),
        )
        detail_ok_outside = q1(
            cur,
            """
            SELECT COUNT(*)
            FROM mesas
            WHERE NOT (
                codigo_mesa BETWEEN ? AND ?
                OR codigo_mesa BETWEEN ? AND ?
            )
              AND status = 'DETAIL_OK'
            """,
            (VALID_RANGES[0][0], VALID_RANGES[0][1], VALID_RANGES[1][0], VALID_RANGES[1][1]),
        )

        print("Resumen previo")
        print("--------------")
        print(f"total filas mesas: {total}")
        print(f"fuera de rangos válidos conocidos: {outside_total}")
        print(f"fuera de rangos válidos con status corregible: {outside_mutable}")
        print(f"fuera de rangos válidos con DETAIL_OK: {detail_ok_outside}")
        print()

        if not args.apply:
            print("Modo preview. Para aplicar, vuelve a correr con --apply")
            return 0

        cur.execute("BEGIN")
        cur.execute(
            """
            UPDATE mesas
            SET status = 'NOT_FOUND',
                ultimo_error = NULL,
                observaciones = CASE
                    WHEN observaciones IS NULL OR TRIM(observaciones) = '' THEN
                        'Corregido: fuera de rangos válidos conocidos (000001-088064, 900001-904703)'
                    ELSE
                        observaciones || ' | Corregido: fuera de rangos válidos conocidos (000001-088064, 900001-904703)'
                END
            WHERE NOT (
                codigo_mesa BETWEEN ? AND ?
                OR codigo_mesa BETWEEN ? AND ?
            )
              AND status IN (?, ?, ?, ?)
            """,
            (
                VALID_RANGES[0][0], VALID_RANGES[0][1],
                VALID_RANGES[1][0], VALID_RANGES[1][1],
                *MUTABLE_STATUSES,
            ),
        )
        updated = cur.rowcount
        conn.commit()

        print(f"Filas actualizadas: {updated}")
        print()

        print("Resumen posterior")
        print("-----------------")
        print_status_summary(cur)
        print()

        outside_pending = q1(
            cur,
            """
            SELECT COUNT(*)
            FROM mesas
            WHERE NOT (
                codigo_mesa BETWEEN ? AND ?
                OR codigo_mesa BETWEEN ? AND ?
            )
              AND status = 'PENDING'
            """,
            (VALID_RANGES[0][0], VALID_RANGES[0][1], VALID_RANGES[1][0], VALID_RANGES[1][1]),
        )
        outside_not_found = q1(
            cur,
            """
            SELECT COUNT(*)
            FROM mesas
            WHERE NOT (
                codigo_mesa BETWEEN ? AND ?
                OR codigo_mesa BETWEEN ? AND ?
            )
              AND status = 'NOT_FOUND'
            """,
            (VALID_RANGES[0][0], VALID_RANGES[0][1], VALID_RANGES[1][0], VALID_RANGES[1][1]),
        )
        detail_ok_total = q1(cur, "SELECT COUNT(*) FROM mesas WHERE status = 'DETAIL_OK'")

        print("Chequeos clave")
        print("-------------")
        print(f"fuera de rangos pendientes: {outside_pending}")
        print(f"fuera de rangos not_found: {outside_not_found}")
        print(f"detail_ok total: {detail_ok_total}")

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
