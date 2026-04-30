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

def aggregate_state(records: list[dict[str, Any]]) -> str:
    codes = [str(r.get("codigoEstadoActa") or "").strip() for r in records]
    if any(c == "P" for c in codes):
        return "Pendiente"
    if any(c == "E" for c in codes):
        return "Para envío al JEE"
    if codes and all(c == "C" for c in codes):
        return "DETAIL_OK"
    return "DETAIL_OK"

def election_state(code: str) -> str:
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
    try:
        return json.loads(proc.stdout)
    except Exception as exc:
        snippet = proc.stdout[:200].replace("\n", " ")
        raise RuntimeError(f"Respuesta no JSON para mesa {codigo_mesa}: {exc}; body[:200]={snippet!r}")

def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def current_db_targets(conn: sqlite3.Connection, limit: int | None = None) -> list[str]:
    sql = """
        SELECT DISTINCT codigo_mesa
        FROM mesa_eleccion_control
        WHERE estado_control IN ('Pendiente', 'Para envío al JEE')
        ORDER BY codigo_mesa
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    return [r[0] for r in conn.execute(sql).fetchall()]

def old_snapshot(conn: sqlite3.Connection, codigo_mesa: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id_eleccion, codigo_estado_acta, total_votos_validos, total_votos_emitidos, total_electores_habiles
        FROM mesa_eleccion_control
        WHERE codigo_mesa = ?
        """,
        (codigo_mesa,),
    ).fetchall()
    return {
        str(eid): {
            "codigoEstadoActa": code,
            "totalVotosValidos": tvv,
            "totalVotosEmitidos": tve,
            "totalElectoresHabiles": teh,
        }
        for eid, code, tvv, tve, teh in rows
    }

def compare(old_map: dict[str, dict[str, Any]], new_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    new_map = {
        str(r.get("idEleccion", "")).strip(): {
            "codigoEstadoActa": str(r.get("codigoEstadoActa", "")).strip(),
            "totalVotosValidos": r.get("totalVotosValidos"),
            "totalVotosEmitidos": r.get("totalVotosEmitidos"),
            "totalElectoresHabiles": r.get("totalElectoresHabiles"),
        }
        for r in new_records if str(r.get("idEleccion", "")).strip()
    }
    changes = []
    for eid in sorted(set(old_map) | set(new_map), key=lambda x: int(x) if x.isdigit() else x):
        o = old_map.get(eid, {})
        n = new_map.get(eid, {})
        if (
            o.get("codigoEstadoActa"), o.get("totalVotosValidos"), o.get("totalVotosEmitidos"), o.get("totalElectoresHabiles")
        ) != (
            n.get("codigoEstadoActa"), n.get("totalVotosValidos"), n.get("totalVotosEmitidos"), n.get("totalElectoresHabiles")
        ):
            changes.append({
                "idEleccion": eid,
                "old_code": o.get("codigoEstadoActa"),
                "new_code": n.get("codigoEstadoActa"),
                "old_totalVotosValidos": o.get("totalVotosValidos"),
                "new_totalVotosValidos": n.get("totalVotosValidos"),
                "old_totalVotosEmitidos": o.get("totalVotosEmitidos"),
                "new_totalVotosEmitidos": n.get("totalVotosEmitidos"),
            })
    return changes

def upsert_aux(conn: sqlite3.Connection, codigo_mesa: str, records: list[dict[str, Any]], sha256: str, json_path: Path) -> tuple[int, int]:
    cur = conn.cursor()
    inserts = 0
    updates = 0
    for r in records:
        eid = str(r.get("idEleccion", "")).strip()
        if not eid:
            continue
        code = str(r.get("codigoEstadoActa", "")).strip()
        state = election_state(code)
        tvv = r.get("totalVotosValidos")
        tve = r.get("totalVotosEmitidos")
        teh = r.get("totalElectoresHabiles")
        old = cur.execute(
            "SELECT codigo_estado_acta, total_votos_validos, total_votos_emitidos, total_electores_habiles FROM mesa_eleccion_control WHERE codigo_mesa=? AND id_eleccion=?",
            (codigo_mesa, eid)
        ).fetchone()
        if old is None:
            cur.execute(
                """
                INSERT INTO mesa_eleccion_control (
                    codigo_mesa,id_eleccion,codigo_estado_acta,estado_control,
                    total_votos_validos,total_votos_emitidos,total_electores_habiles,
                    last_seen_sha256,last_checked_at,last_changed_at,change_count,json_path
                ) VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,1,?)
                """,
                (codigo_mesa,eid,code,state,tvv,tve,teh,sha256,str(json_path))
            )
            inserts += 1
        else:
            changed = old != (code, tvv, tve, teh)
            if changed:
                cur.execute(
                    """
                    UPDATE mesa_eleccion_control
                    SET codigo_estado_acta=?, estado_control=?, total_votos_validos=?, total_votos_emitidos=?,
                        total_electores_habiles=?, last_seen_sha256=?, last_checked_at=CURRENT_TIMESTAMP,
                        last_changed_at=CURRENT_TIMESTAMP, change_count=COALESCE(change_count,0)+1, json_path=?
                    WHERE codigo_mesa=? AND id_eleccion=?
                    """,
                    (code,state,tvv,tve,teh,sha256,str(json_path),codigo_mesa,eid)
                )
                updates += 1
            else:
                cur.execute(
                    """
                    UPDATE mesa_eleccion_control
                    SET estado_control=?, last_seen_sha256=?, last_checked_at=CURRENT_TIMESTAMP, json_path=?
                    WHERE codigo_mesa=? AND id_eleccion=?
                    """,
                    (state,sha256,str(json_path),codigo_mesa,eid)
                )
    conn.commit()
    return inserts, updates

def update_main_mesa(conn: sqlite3.Connection, codigo_mesa: str, status_text: str, json_path: Path) -> None:
    cur = conn.cursor()
    cols = {row[1] for row in cur.execute("PRAGMA table_info(mesas)")}
    set_parts = []
    params = []
    if "status" in cols:
        set_parts.append("status=?")
        params.append(status_text)
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

def main() -> int:
    ap = build_argument_parser(description="Refresca solo mesas pendientes usando índice en SQLite")
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
    ap.add_argument("--report", default="./data/reports/refresh_pending_sqlite_summary.csv")
    args = ap.parse_args()

    outdir = Path(args.out)
    db_path = Path(args.db)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    cookie = load_cookie(args.cookie, args.cookie_file)

    conn = sqlite3.connect(str(db_path))
    try:
        targets = current_db_targets(conn, args.limit)
        print(f"Mesas objetivo desde SQLite (índice): {len(targets)}")
        if not targets:
            return 0

        delay = 1.0 / args.rps if args.rps > 0 else 0.0
        rows = []
        counter = Counter()
        mesas_changed = 0
        elecciones_actualizadas = 0
        inserts_total = 0
        updates_total = 0

        for i, codigo in enumerate(targets, start=1):
            old_map = old_snapshot(conn, codigo)
            print(f"[{i}/{len(targets)}] Mesa {codigo} revisando...")
            payload = fetch_with_curl(codigo, cookie, args.user_agent, args.referer, args.accept_language, args.timeout)
            records = extract_records(payload)
            if not records:
                print(f"    data[] vacía")
                continue
            changes = compare(old_map, records)
            json_path = outdir / "raw_json" / codigo[:3] / f"{codigo}.json"
            sha = write_json(json_path, payload)
            agg_state = aggregate_state(records)
            update_main_mesa(conn, codigo, agg_state, json_path)
            ins, upd = upsert_aux(conn, codigo, records, sha, json_path)
            inserts_total += ins
            updates_total += upd

            if changes:
                mesas_changed += 1
                elecciones_actualizadas += len(changes)
                for ch in changes:
                    counter[f"{ch['idEleccion']}:{ch['old_code']}->{ch['new_code']}"] += 1
                    rows.append({
                        "codigoMesa": codigo,
                        **ch,
                        "sha256": sha,
                    })
                print(f"    CAMBIOS: {len(changes)} elecciones actualizadas; nuevo_estado_agregado={agg_state}")
            else:
                print(f"    Sin cambios; nuevo_estado_agregado={agg_state}")

            if delay > 0 and i < len(targets):
                time.sleep(delay)

    finally:
        conn.close()

    with report_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "codigoMesa","idEleccion","old_code","new_code",
            "old_totalVotosValidos","new_totalVotosValidos",
            "old_totalVotosEmitidos","new_totalVotosEmitidos","sha256"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\nResumen")
    print("-------")
    print(f"Mesas con cambios: {mesas_changed}")
    print(f"Elecciones actualizadas: {elecciones_actualizadas}")
    print(f"Aux inserts={inserts_total} updates={updates_total}")
    print(f"Reporte CSV: {report_path}")
    if counter:
        print("Transiciones detectadas:")
        for k, v in counter.most_common():
            print(f"  {k}: {v}")
    else:
        print("No se detectaron transiciones.")
    print("\nLuego corre:")
    print(f"  python3 onpe_scraper.py --out {outdir} --rebuild-csv")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
