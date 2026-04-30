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

WATCH_CODES = {"P": "Pendiente", "E": "Para envío al JEE"}
TERMINAL_CODES = {"C"}

AUX_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mesa_eleccion_control (
    codigo_mesa TEXT NOT NULL,
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
    json_path TEXT,
    PRIMARY KEY (codigo_mesa, id_eleccion)
)
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_mec_estado_control ON mesa_eleccion_control (estado_control)",
    "CREATE INDEX IF NOT EXISTS idx_mec_codigo_estado ON mesa_eleccion_control (codigo_estado_acta)",
]

def load_cookie(value: str | None, cookie_file: Path | None) -> str:
    if cookie_file:
        value = cookie_file.read_text(encoding="utf-8").strip()
    value = (value or "").strip()
    if value.lower().startswith("cookie:"):
        value = value.split(":", 1)[1].strip()
    if not value:
        raise SystemExit("Debes pasar --cookie o --cookie-file")
    return value

def extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []

def aggregate_state_from_codes(codes: list[str]) -> str:
    codes = [c.strip() for c in codes if c is not None]
    if any(c == "P" for c in codes):
        return "Pendiente"
    if any(c == "E" for c in codes):
        return "Para envío al JEE"
    if codes and all(c in TERMINAL_CODES for c in codes):
        return "DETAIL_OK"
    return "DETAIL_OK"

def election_control_state(code: str) -> str:
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

def current_watch_state(records: list[dict[str, Any]]) -> tuple[bool, str]:
    codes = [str(r.get("codigoEstadoActa") or "").strip() for r in records]
    state = aggregate_state_from_codes(codes)
    return state in WATCH_CODES.values(), state

def compare_records(old_records: list[dict[str, Any]], new_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    old_map = {str(r.get("idEleccion", "")).strip(): r for r in old_records if str(r.get("idEleccion", "")).strip()}
    new_map = {str(r.get("idEleccion", "")).strip(): r for r in new_records if str(r.get("idEleccion", "")).strip()}
    changes: list[dict[str, Any]] = []
    keys = sorted(set(old_map) | set(new_map), key=lambda x: int(x) if x.isdigit() else x)
    for eid in keys:
        old = old_map.get(eid, {})
        new = new_map.get(eid, {})
        old_code = str(old.get("codigoEstadoActa", "")).strip()
        new_code = str(new.get("codigoEstadoActa", "")).strip()
        old_votes = old.get("totalVotosValidos")
        new_votes = new.get("totalVotosValidos")
        old_emit = old.get("totalVotosEmitidos")
        new_emit = new.get("totalVotosEmitidos")
        old_hab = old.get("totalElectoresHabiles")
        new_hab = new.get("totalElectoresHabiles")
        if (old_code, old_votes, old_emit, old_hab) != (new_code, new_votes, new_emit, new_hab):
            changes.append(
                {
                    "idEleccion": eid,
                    "old_code": old_code,
                    "new_code": new_code,
                    "old_totalVotosValidos": old_votes,
                    "new_totalVotosValidos": new_votes,
                    "old_totalVotosEmitidos": old_emit,
                    "new_totalVotosEmitidos": new_emit,
                    "old_totalElectoresHabiles": old_hab,
                    "new_totalElectoresHabiles": new_hab,
                }
            )
    return changes

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
        snippet = text[:200].replace("\n", " ")
        raise RuntimeError(f"Respuesta no JSON para mesa {codigo_mesa}: {exc}; body[:200]={snippet!r}")

def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def discover_watched_mesas(outdir: Path) -> list[tuple[str, Path, list[dict[str, Any]]]]:
    results: list[tuple[str, Path, list[dict[str, Any]]]] = []
    root = outdir / "raw_json"
    if not root.exists():
        return results
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        records = extract_records(payload)
        if not records:
            continue
        codigo = str((records[0].get("codigoMesa") or payload.get("codigoMesa") or path.stem)).zfill(6)
        watch, _ = current_watch_state(records)
        if watch:
            results.append((codigo, path, records))
    return results

def ensure_aux_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(AUX_TABLE_SQL)
    for sql in INDEX_SQL:
        cur.execute(sql)
    conn.commit()

def update_aggregate_row(conn: sqlite3.Connection, codigo_mesa: str, status_text: str, json_path: Path) -> None:
    cur = conn.cursor()
    cols = {row[1] for row in cur.execute("PRAGMA table_info(mesas)")}
    set_parts = []
    params: list[Any] = []

    if "status" in cols:
        set_parts.append("status = ?")
        params.append(status_text)
    if "ultimo_error" in cols:
        set_parts.append("ultimo_error = NULL")
    if "json_path" in cols:
        set_parts.append("json_path = ?")
        params.append(str(json_path))
    if "observaciones" in cols:
        set_parts.append(
            "observaciones = CASE "
            "WHEN observaciones IS NULL OR TRIM(observaciones) = '' THEN ? "
            "ELSE observaciones || ' | ' || ? END"
        )
        msg = f"Refrescado incrementalmente; estado agregado={status_text}"
        params.extend([msg, msg])

    if set_parts:
        sql = f"UPDATE mesas SET {', '.join(set_parts)} WHERE codigo_mesa = ?"
        params.append(codigo_mesa)
        cur.execute(sql, params)

def upsert_aux_rows(conn: sqlite3.Connection, codigo_mesa: str, records: list[dict[str, Any]], sha256: str, json_path: Path) -> tuple[int, int]:
    cur = conn.cursor()
    ensure_aux_table(conn)
    changes = 0
    inserts = 0
    for rec in records:
        eid = str(rec.get("idEleccion", "")).strip()
        if not eid:
            continue
        code = str(rec.get("codigoEstadoActa", "")).strip()
        state = election_control_state(code)
        tvv = rec.get("totalVotosValidos")
        tve = rec.get("totalVotosEmitidos")
        teh = rec.get("totalElectoresHabiles")

        old = cur.execute(
            """
            SELECT codigo_estado_acta, total_votos_validos, total_votos_emitidos, total_electores_habiles
            FROM mesa_eleccion_control
            WHERE codigo_mesa = ? AND id_eleccion = ?
            """,
            (codigo_mesa, eid),
        ).fetchone()

        if old is None:
            cur.execute(
                """
                INSERT INTO mesa_eleccion_control (
                    codigo_mesa, id_eleccion, codigo_estado_acta, estado_control,
                    total_votos_validos, total_votos_emitidos, total_electores_habiles,
                    last_seen_sha256, last_checked_at, last_changed_at, change_count, json_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, ?)
                """,
                (codigo_mesa, eid, code, state, tvv, tve, teh, sha256, str(json_path)),
            )
            inserts += 1
            changes += 1
        else:
            old_code, old_tvv, old_tve, old_teh = old
            changed = (old_code, old_tvv, old_tve, old_teh) != (code, tvv, tve, teh)
            if changed:
                cur.execute(
                    """
                    UPDATE mesa_eleccion_control
                    SET codigo_estado_acta = ?,
                        estado_control = ?,
                        total_votos_validos = ?,
                        total_votos_emitidos = ?,
                        total_electores_habiles = ?,
                        last_seen_sha256 = ?,
                        last_checked_at = CURRENT_TIMESTAMP,
                        last_changed_at = CURRENT_TIMESTAMP,
                        change_count = COALESCE(change_count, 0) + 1,
                        json_path = ?
                    WHERE codigo_mesa = ? AND id_eleccion = ?
                    """,
                    (code, state, tvv, tve, teh, sha256, str(json_path), codigo_mesa, eid),
                )
                changes += 1
            else:
                cur.execute(
                    """
                    UPDATE mesa_eleccion_control
                    SET estado_control = ?,
                        last_seen_sha256 = ?,
                        last_checked_at = CURRENT_TIMESTAMP,
                        json_path = ?
                    WHERE codigo_mesa = ? AND id_eleccion = ?
                    """,
                    (state, sha256, str(json_path), codigo_mesa, eid),
                )
    conn.commit()
    return inserts, changes

def main() -> int:
    ap = build_argument_parser(description="V2 refresca mesas con P/E y mantiene tabla auxiliar mesa+idEleccion.")
    ap.add_argument("--out", default="./data", help="Directorio base")
    ap.add_argument("--cookie", default=None, help="Cookie completa")
    ap.add_argument("--cookie-file", type=Path, default=None, help="Archivo con cookie completa")
    ap.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    ap.add_argument("--referer", default=DEFAULT_REFERER)
    ap.add_argument("--accept-language", default=DEFAULT_ACCEPT_LANGUAGE)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--rps", type=float, default=0.5)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    outdir = Path(args.out)
    cookie = load_cookie(args.cookie, args.cookie_file)
    db_path = outdir / "state" / "onpe_scraper.sqlite"
    report_path = Path(args.report) if args.report else (outdir / "reports" / "refresh_pending_summary_v2.csv")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    watched = discover_watched_mesas(outdir)
    if args.limit:
        watched = watched[:args.limit]

    print(f"Mesas con alguna elección en P/E detectadas localmente: {len(watched)}")
    if not watched:
        return 0

    delay = 1.0 / args.rps if args.rps > 0 else 0.0
    summary_rows: list[dict[str, Any]] = []
    change_counter = Counter()
    mesas_changed = 0
    elecciones_actualizadas = 0
    aux_inserts_total = 0
    aux_changes_total = 0

    conn = sqlite3.connect(str(db_path))
    ensure_aux_table(conn)

    try:
        for idx, (codigo, path, old_records) in enumerate(watched, start=1):
            _, old_state = current_watch_state(old_records)
            print(f"[{idx}/{len(watched)}] Mesa {codigo} estado_local={old_state} revisando...")
            if args.dry_run:
                continue
            new_payload = fetch_with_curl(codigo, cookie, args.user_agent, args.referer, args.accept_language, args.timeout)
            new_records = extract_records(new_payload)
            if not new_records:
                raise RuntimeError(f"Mesa {codigo} devolvió data[] vacía")
            changes = compare_records(old_records, new_records)
            _, new_state = current_watch_state(new_records)
            sha = write_json(path, new_payload)
            update_aggregate_row(conn, codigo, new_state, path)
            aux_inserts, aux_changes = upsert_aux_rows(conn, codigo, new_records, sha, path)
            aux_inserts_total += aux_inserts
            aux_changes_total += aux_changes

            if changes:
                mesas_changed += 1
                elecciones_actualizadas += len(changes)
                for ch in changes:
                    key = f"{ch['idEleccion']}:{ch['old_code']}->{ch['new_code']}"
                    change_counter[key] += 1
                    summary_rows.append(
                        {
                            "codigoMesa": codigo,
                            "idEleccion": ch["idEleccion"],
                            "old_code": ch["old_code"],
                            "new_code": ch["new_code"],
                            "old_totalVotosValidos": ch["old_totalVotosValidos"],
                            "new_totalVotosValidos": ch["new_totalVotosValidos"],
                            "old_totalVotosEmitidos": ch["old_totalVotosEmitidos"],
                            "new_totalVotosEmitidos": ch["new_totalVotosEmitidos"],
                            "old_totalElectoresHabiles": ch["old_totalElectoresHabiles"],
                            "new_totalElectoresHabiles": ch["new_totalElectoresHabiles"],
                            "sha256": sha,
                        }
                    )
                print(f"    CAMBIOS: {len(changes)} elecciones actualizadas; nuevo_estado_agregado={new_state}")
            else:
                print(f"    Sin cambios; nuevo_estado_agregado={new_state}")

            if delay > 0 and idx < len(watched):
                time.sleep(delay)
    finally:
        conn.close()

    with report_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "codigoMesa", "idEleccion", "old_code", "new_code",
            "old_totalVotosValidos", "new_totalVotosValidos",
            "old_totalVotosEmitidos", "new_totalVotosEmitidos",
            "old_totalElectoresHabiles", "new_totalElectoresHabiles", "sha256"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\nResumen")
    print("-------")
    print(f"Mesas revisadas: {len(watched)}")
    print(f"Mesas con cambios: {mesas_changed}")
    print(f"Elecciones actualizadas: {elecciones_actualizadas}")
    print(f"Filas insertadas/actualizadas en tabla auxiliar: inserts={aux_inserts_total}, cambios={aux_changes_total}")
    print(f"Reporte CSV: {report_path}")
    if change_counter:
        print("Transiciones detectadas:")
        for k, v in change_counter.most_common():
            print(f"  {k}: {v}")
    else:
        print("No se detectaron transiciones de estado ni cambios de totales.")
    print("\nTabla auxiliar creada/actualizada: mesa_eleccion_control")
    print("Luego corre:")
    print(f"  python3 onpe_scraper.py --out {outdir} --rebuild-csv")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
