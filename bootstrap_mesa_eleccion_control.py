#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

from project_metadata import build_argument_parser

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS mesa_eleccion_control (
    codigo_mesa TEXT NOT NULL,
    id_eleccion TEXT NOT NULL,
    codigo_estado_acta TEXT,
    estado_control TEXT,
    total_votos_validos INTEGER,
    total_votos_emitidos INTEGER,
    total_electores_habiles INTEGER,
    last_seen_sha256 TEXT,
    last_checked_at TEXT,
    last_changed_at TEXT,
    change_count INTEGER DEFAULT 0,
    json_path TEXT,
    PRIMARY KEY (codigo_mesa, id_eleccion)
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mec_estado_control ON mesa_eleccion_control (estado_control)",
    "CREATE INDEX IF NOT EXISTS idx_mec_codigo_mesa ON mesa_eleccion_control (codigo_mesa)",
    "CREATE INDEX IF NOT EXISTS idx_mec_codigo_estado_acta ON mesa_eleccion_control (codigo_estado_acta)",
]

def state_from_code(code: str) -> str:
    code = (code or "").strip()
    if code == "P":
        return "Pendiente"
    if code == "E":
        return "Para envío al JEE"
    if code == "C":
        return "Contabilizada"
    if code:
        return f"Estado_{code}"
    return "SIN_ESTADO"

def to_int(value):
    if value in (None, "", "None"):
        return None
    try:
        return int(float(value))
    except Exception:
        return None

def main() -> int:
    ap = build_argument_parser(description="Bootstrap de mesa_eleccion_control desde mesas_consolidado.csv")
    ap.add_argument("--csv", default="./data/output/mesas_consolidado.csv")
    ap.add_argument("--db", default="./data/state/onpe_scraper.sqlite")
    ap.add_argument("--truncate", action="store_true", help="Vacía la tabla auxiliar antes de recargar")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    db_path = Path(args.db)
    if not csv_path.exists():
        raise SystemExit(f"No existe el CSV: {csv_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(CREATE_SQL)
    for sql in INDEXES:
        cur.execute(sql)
    if args.truncate:
        cur.execute("DELETE FROM mesa_eleccion_control")
        conn.commit()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = ["codigoMesa", "idEleccion", "codigoEstadoActa"]
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Faltan columnas requeridas en CSV: {missing}")

        rows = 0
        upserts = 0
        for row in reader:
            codigo_mesa = str(row.get("codigoMesa", "")).strip().zfill(6)
            id_eleccion = str(row.get("idEleccion", "")).strip()
            codigo_estado_acta = str(row.get("codigoEstadoActa", "")).strip()
            estado_control = state_from_code(codigo_estado_acta)
            total_votos_validos = to_int(row.get("totalVotosValidos"))
            total_votos_emitidos = to_int(row.get("totalVotosEmitidos"))
            total_electores_habiles = to_int(row.get("totalElectoresHabiles"))

            if not codigo_mesa or not id_eleccion:
                continue

            cur.execute(
                """
                INSERT INTO mesa_eleccion_control (
                    codigo_mesa, id_eleccion, codigo_estado_acta, estado_control,
                    total_votos_validos, total_votos_emitidos, total_electores_habiles,
                    last_checked_at, last_changed_at, change_count, json_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, ?)
                ON CONFLICT(codigo_mesa, id_eleccion) DO UPDATE SET
                    codigo_estado_acta=excluded.codigo_estado_acta,
                    estado_control=excluded.estado_control,
                    total_votos_validos=excluded.total_votos_validos,
                    total_votos_emitidos=excluded.total_votos_emitidos,
                    total_electores_habiles=excluded.total_electores_habiles,
                    last_checked_at=CURRENT_TIMESTAMP
                """,
                (
                    codigo_mesa, id_eleccion, codigo_estado_acta, estado_control,
                    total_votos_validos, total_votos_emitidos, total_electores_habiles,
                    f"./data/raw_json/{codigo_mesa[:3]}/{codigo_mesa}.json",
                ),
            )
            rows += 1
            upserts += 1

    conn.commit()
    print(f"Filas leídas del CSV: {rows}")
    total = cur.execute("SELECT COUNT(*) FROM mesa_eleccion_control").fetchone()[0]
    print(f"Filas en mesa_eleccion_control: {total}")
    print("Resumen por estado_control:")
    for estado, n in cur.execute(
        "SELECT estado_control, COUNT(*) FROM mesa_eleccion_control GROUP BY estado_control ORDER BY estado_control"
    ):
        print(f"  {estado}: {n}")
    conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
