#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

from project_metadata import build_argument_parser

SEARCH_URL = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/actas/buscar/mesa?codigoMesa={codigo}"
DEFAULT_REFERER = "https://resultadoelectoral.onpe.gob.pe/main/actas"
DEFAULT_ACCEPT_LANGUAGE = "es-419,es;q=0.9"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

TARGET_ELECTION = "10"
TARGET_NAME = "Presidencial"

AUX_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mesa_presidencial_control (
    codigo_mesa TEXT PRIMARY KEY,
    id_eleccion TEXT NOT NULL,
    codigo_estado_acta TEXT,
    estado_control TEXT,
    total_votos_validos INTEGER,
    total_votos_emitidos INTEGER,
    total_electores_habiles INTEGER,
    last_seen_sha256 TEXT,
    last_checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_changed_at TEXT,
    change_count INTEGER DEFAULT 0,
    json_path TEXT
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mpc_estado_control ON mesa_presidencial_control (estado_control)",
    "CREATE INDEX IF NOT EXISTS idx_mpc_codigo_estado ON mesa_presidencial_control (codigo_estado_acta)",
]

VALID_ESTADOS = {"Pendiente", "Para envío al JEE"}

def load_cookie(value: str | None, cookie_file: Path | None) -> str:
    if cookie_file:
        value = cookie_file.read_text(encoding="utf-8").strip()
    value = (value or "").strip()
    if value.lower().startswith("cookie:"):
        value = value.split(":", 1)[1].strip()
    if not value:
        raise SystemExit("Debes pasar --cookie o --cookie-file")
    return value

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

def aggregate_state(records: list[dict[str, Any]]) -> str:
    codes = [str(r.get("codigoEstadoActa") or "").strip() for r in records]
    if any(c == "P" for c in codes):
        return "Pendiente"
    if any(c == "E" for c in codes):
        return "Para envío al JEE"
    if codes and all(c == "C" for c in codes):
        return "DETAIL_OK"
    return "DETAIL_OK"

def extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []

def extract_presidencial(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    for r in records:
        if str(r.get("idEleccion", "")).strip() == TARGET_ELECTION:
            return r
    return None

def to_int(value: Any) -> int | None:
    if value in (None, "", "None"):
        return None
    try:
        return int(float(value))
    except Exception:
        return None

def fetch_with_curl(codigo_mesa: str, cookie: str, user_agent: str, referer: str, accept_language: str, timeout: float) -> dict[str, Any]:
    url = SEARCH_URL.format(codigo=codigo_mesa)
    cmd = [
        "curl", "-sS", url,
        "-H", "accept: */*",
        "-H", f"accept-language: {accept_language}",
        "-H", "cache-control: no-cache",
        "-H", "content-type: application/json",
        "-b", cookie,
        "-H", "pragma: no-cache",
        "-H", "priority: u=1, i",
        "-H", f"referer: {referer}",
        "-H", 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "-H", "sec-ch-ua-mobile: ?0",
        "-H", 'sec-ch-ua-platform: "macOS"',
        "-H", "sec-fetch-dest: empty",
        "-H", "sec-fetch-mode: cors",
        "-H", "sec-fetch-site: same-origin",
        "-H", f"user-agent: {user_agent}",
        "--max-time", str(int(timeout)),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"curl falló rc={proc.returncode}: {proc.stderr.strip()}")
    text = proc.stdout
    try:
        return json.loads(text)
    except Exception as exc:
        snippet = text[:200].replace("\\n", " ")
        raise RuntimeError(f"Respuesta no JSON para mesa {codigo_mesa}: {exc}; body[:200]={snippet!r}")

def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def ensure_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(AUX_TABLE_SQL)
    for sql in INDEXES:
        cur.execute(sql)
    conn.commit()

def bootstrap_from_csv(csv_path: Path, conn: sqlite3.Connection, truncate: bool = False) -> None:
    ensure_table(conn)
    cur = conn.cursor()
    if truncate:
        cur.execute("DELETE FROM mesa_presidencial_control")
        conn.commit()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        needed = ["codigoMesa", "idEleccion", "codigoEstadoActa"]
        missing = [c for c in needed if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Faltan columnas requeridas en CSV: {missing}")
        rows = 0
        for row in reader:
            if str(row.get("idEleccion", "")).strip() != TARGET_ELECTION:
                continue
            codigo = str(row.get("codigoMesa", "")).strip().zfill(6)
            code = str(row.get("codigoEstadoActa", "")).strip()
            state = state_from_code(code)
            cur.execute(
                """
                INSERT INTO mesa_presidencial_control (
                    codigo_mesa,id_eleccion,codigo_estado_acta,estado_control,
                    total_votos_validos,total_votos_emitidos,total_electores_habiles,
                    last_checked_at,last_changed_at,change_count,json_path
                ) VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,0,?)
                ON CONFLICT(codigo_mesa) DO UPDATE SET
                    codigo_estado_acta=excluded.codigo_estado_acta,
                    estado_control=excluded.estado_control,
                    total_votos_validos=excluded.total_votos_validos,
                    total_votos_emitidos=excluded.total_votos_emitidos,
                    total_electores_habiles=excluded.total_electores_habiles,
                    last_checked_at=CURRENT_TIMESTAMP
                """,
                (
                    codigo,
                    TARGET_ELECTION,
                    code,
                    state,
                    to_int(row.get("totalVotosValidos")),
                    to_int(row.get("totalVotosEmitidos")),
                    to_int(row.get("totalElectoresHabiles")),
                    f"./data/raw_json/{codigo[:3]}/{codigo}.json",
                ),
            )
            rows += 1
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM mesa_presidencial_control").fetchone()[0]
    print(f"Bootstrap presidencial desde CSV completado. Filas presidenciales leídas: {rows}")
    print(f"Filas en mesa_presidencial_control: {total}")
    for estado, n in conn.execute(
        "SELECT estado_control, COUNT(*) FROM mesa_presidencial_control GROUP BY estado_control ORDER BY estado_control"
    ):
        print(f"  {estado}: {n}")

def current_targets(conn: sqlite3.Connection, estados: list[str], limit: int | None) -> list[str]:
    placeholders = ",".join("?" for _ in estados)
    sql = f"""
        SELECT codigo_mesa
        FROM mesa_presidencial_control
        WHERE estado_control IN ({placeholders})
        ORDER BY codigo_mesa
    """
    params: list[Any] = list(estados)
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    return [r[0] for r in conn.execute(sql, params).fetchall()]

def old_snapshot(conn: sqlite3.Connection, codigo_mesa: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT codigo_estado_acta, total_votos_validos, total_votos_emitidos, total_electores_habiles
        FROM mesa_presidencial_control
        WHERE codigo_mesa = ?
        """,
        (codigo_mesa,),
    ).fetchone()
    if not row:
        return None
    return {
        "codigoEstadoActa": row[0],
        "totalVotosValidos": row[1],
        "totalVotosEmitidos": row[2],
        "totalElectoresHabiles": row[3],
    }

def upsert_presidencial(conn: sqlite3.Connection, codigo_mesa: str, rec: dict[str, Any], sha256: str, json_path: Path) -> tuple[bool, bool]:
    cur = conn.cursor()
    code = str(rec.get("codigoEstadoActa", "")).strip()
    state = state_from_code(code)
    tvv = to_int(rec.get("totalVotosValidos"))
    tve = to_int(rec.get("totalVotosEmitidos"))
    teh = to_int(rec.get("totalElectoresHabiles"))

    old = cur.execute(
        """
        SELECT codigo_estado_acta, total_votos_validos, total_votos_emitidos, total_electores_habiles
        FROM mesa_presidencial_control
        WHERE codigo_mesa = ?
        """,
        (codigo_mesa,),
    ).fetchone()

    inserted = False
    changed = False

    if old is None:
        cur.execute(
            """
            INSERT INTO mesa_presidencial_control (
                codigo_mesa,id_eleccion,codigo_estado_acta,estado_control,
                total_votos_validos,total_votos_emitidos,total_electores_habiles,
                last_seen_sha256,last_checked_at,last_changed_at,change_count,json_path
            ) VALUES (?,?,?,?,?,?,?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, ?)
            """,
            (codigo_mesa, TARGET_ELECTION, code, state, tvv, tve, teh, sha256, str(json_path)),
        )
        inserted = True
        changed = True
    else:
        changed = old != (code, tvv, tve, teh)
        if changed:
            cur.execute(
                """
                UPDATE mesa_presidencial_control
                SET codigo_estado_acta=?, estado_control=?, total_votos_validos=?, total_votos_emitidos=?,
                    total_electores_habiles=?, last_seen_sha256=?, last_checked_at=CURRENT_TIMESTAMP,
                    last_changed_at=CURRENT_TIMESTAMP, change_count=COALESCE(change_count,0)+1, json_path=?
                WHERE codigo_mesa=?
                """,
                (code, state, tvv, tve, teh, sha256, str(json_path), codigo_mesa),
            )
        else:
            cur.execute(
                """
                UPDATE mesa_presidencial_control
                SET estado_control=?, last_seen_sha256=?, last_checked_at=CURRENT_TIMESTAMP, json_path=?
                WHERE codigo_mesa=?
                """,
                (state, sha256, str(json_path), codigo_mesa),
            )
    conn.commit()
    return inserted, changed

def update_main_mesa(conn: sqlite3.Connection, codigo_mesa: str, all_records: list[dict[str, Any]], json_path: Path) -> None:
    cur = conn.cursor()
    cols = {row[1] for row in cur.execute("PRAGMA table_info(mesas)")}
    agg_state = aggregate_state(all_records)
    set_parts = []
    params: list[Any] = []
    if "status" in cols:
        set_parts.append("status=?")
        params.append(agg_state)
    if "ultimo_error" in cols:
        set_parts.append("ultimo_error=NULL")
    if "json_path" in cols:
        set_parts.append("json_path=?")
        params.append(str(json_path))
    if set_parts:
        sql = f"UPDATE mesas SET {', '.join(set_parts)} WHERE codigo_mesa=?"
        params.append(codigo_mesa)
        cur.execute(sql, params)
        conn.commit()

def parse_estados(raw: list[str]) -> list[str]:
    if not raw:
        return ["Pendiente", "Para envío al JEE"]
    estados = []
    for item in raw:
        for part in str(item).split(","):
            val = part.strip()
            if not val:
                continue
            if val not in VALID_ESTADOS:
                raise SystemExit(f"Estado no válido: {val}. Usa 'Pendiente' y/o 'Para envío al JEE'")
            estados.append(val)
    if not estados:
        raise SystemExit("No se recibió ningún estado válido.")
    seen = []
    for e in estados:
        if e not in seen:
            seen.append(e)
    return seen

def main() -> int:
    ap = build_argument_parser(description="Refresh incremental solo de Presidencial (idEleccion=10) con filtro por estado")
    ap.add_argument("--out", default="./data")
    ap.add_argument("--db", default="./data/state/onpe_scraper.sqlite")
    ap.add_argument("--cookie", default=None)
    ap.add_argument("--cookie-file", type=Path, default=None)
    ap.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    ap.add_argument("--referer", default=DEFAULT_REFERER)
    ap.add_argument("--accept-language", default=DEFAULT_ACCEPT_LANGUAGE)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--rps", type=float, default=0.5)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--estado", action="append", default=[], help="Estado(s) a refrescar: 'Pendiente' y/o 'Para envío al JEE'. Puede repetirse o pasar separados por coma.")
    ap.add_argument("--bootstrap-from-csv", action="store_true")
    ap.add_argument("--csv", default="./data/output/mesas_consolidado.csv")
    ap.add_argument("--truncate-bootstrap", action="store_true")
    ap.add_argument("--report", default="./data/reports/refresh_presidencial_summary.csv")
    args = ap.parse_args()

    outdir = Path(args.out)
    db_path = Path(args.db)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    ensure_table(conn)

    if args.bootstrap_from_csv:
        bootstrap_from_csv(Path(args.csv), conn, truncate=args.truncate_bootstrap)
        conn.close()
        return 0

    estados = parse_estados(args.estado)
    cookie = load_cookie(args.cookie, args.cookie_file)
    targets = current_targets(conn, estados, args.limit)
    print(f"Mesas objetivo desde SQLite para {TARGET_NAME} con estados {estados}: {len(targets)}")
    if not targets:
        conn.close()
        return 0

    delay = 1.0 / args.rps if args.rps > 0 else 0.0
    rows = []
    counter = Counter()
    mesas_changed = 0
    inserted_total = 0
    changed_total = 0
    errors = 0

    try:
        for i, codigo in enumerate(targets, start=1):
            print(f"[{i}/{len(targets)}] Mesa {codigo} revisando {TARGET_NAME}...")
            try:
                old = old_snapshot(conn, codigo) or {}
                payload = fetch_with_curl(codigo, cookie, args.user_agent, args.referer, args.accept_language, args.timeout)
                all_records = extract_records(payload)
                rec = extract_presidencial(all_records)
                if not rec:
                    print("    Sin registro presidencial en respuesta")
                    continue
                json_path = outdir / "raw_json" / codigo[:3] / f"{codigo}.json"
                sha = write_json(json_path, payload)
                update_main_mesa(conn, codigo, all_records, json_path)
                inserted, changed = upsert_presidencial(conn, codigo, rec, sha, json_path)
                inserted_total += 1 if inserted else 0
                changed_total += 1 if changed else 0

                new_code = str(rec.get("codigoEstadoActa", "")).strip()
                new_tvv = to_int(rec.get("totalVotosValidos"))
                new_tve = to_int(rec.get("totalVotosEmitidos"))
                new_teh = to_int(rec.get("totalElectoresHabiles"))

                if (
                    old.get("codigoEstadoActa"), old.get("totalVotosValidos"),
                    old.get("totalVotosEmitidos"), old.get("totalElectoresHabiles")
                ) != (new_code, new_tvv, new_tve, new_teh):
                    mesas_changed += 1
                    trans = f"{old.get('codigoEstadoActa')}->{new_code}"
                    counter[trans] += 1
                    rows.append({
                        "codigoMesa": codigo,
                        "idEleccion": TARGET_ELECTION,
                        "old_code": old.get("codigoEstadoActa"),
                        "new_code": new_code,
                        "old_totalVotosValidos": old.get("totalVotosValidos"),
                        "new_totalVotosValidos": new_tvv,
                        "old_totalVotosEmitidos": old.get("totalVotosEmitidos"),
                        "new_totalVotosEmitidos": new_tve,
                        "old_totalElectoresHabiles": old.get("totalElectoresHabiles"),
                        "new_totalElectoresHabiles": new_teh,
                        "sha256": sha,
                    })
                    print(f"    CAMBIOS: presidencial {trans}")
                else:
                    print(f"    Sin cambios; estado_presidencial={state_from_code(new_code)}")
            except Exception as exc:
                errors += 1
                print(f"    ERROR: {exc}")

            if delay > 0 and i < len(targets):
                time.sleep(delay)
    finally:
        conn.close()

    with report_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "codigoMesa","idEleccion","old_code","new_code",
            "old_totalVotosValidos","new_totalVotosValidos",
            "old_totalVotosEmitidos","new_totalVotosEmitidos",
            "old_totalElectoresHabiles","new_totalElectoresHabiles","sha256"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\nResumen")
    print("-------")
    print(f"Estados filtrados: {estados}")
    print(f"Mesas revisadas: {len(targets)}")
    print(f"Mesas con cambios presidenciales: {mesas_changed}")
    print(f"Insertadas nuevas filas presidenciales: {inserted_total}")
    print(f"Filas presidenciales con cambio: {changed_total}")
    print(f"Errores por mesa: {errors}")
    print(f"Reporte CSV: {report_path}")
    if counter:
        print("Transiciones presidenciales detectadas:")
        for k, v in counter.most_common():
            print(f"  {k}: {v}")
    else:
        print("No se detectaron transiciones presidenciales.")
    print("\nLuego corre:")
    print(f"  python3 onpe_scraper.py --out {outdir} --rebuild-csv")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
