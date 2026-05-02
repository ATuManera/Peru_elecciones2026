#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 A Tu Manera Digital - Fernando Gallarday
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import random
import sqlite3
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

try:
    import httpx  # type: ignore
except ModuleNotFoundError:
    httpx = None

import urllib.error
import urllib.parse
import urllib.request

from project_metadata import HELP_EPILOG

TZ_LIMA = ZoneInfo("America/Lima")
SEARCH_URL = (
    "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/actas/buscar/mesa"
)
DETAIL_URL_TEMPLATE = (
    "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/actas/{internal_id}"
)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)
DEFAULT_REFERER = "https://resultadoelectoral.onpe.gob.pe/main/actas"
DEFAULT_ACCEPT_LANGUAGE = "es-419,es;q=0.9"
DEFAULT_ACCEPT = "*/*"
DEFAULT_CONTENT_TYPE = "application/json"
DEFAULT_CACHE_CONTROL = "no-cache"
DEFAULT_PRAGMA = "no-cache"
DEFAULT_SEC_FETCH_DEST = "empty"
DEFAULT_SEC_FETCH_MODE = "cors"
DEFAULT_SEC_FETCH_SITE = "same-origin"
DEFAULT_SEC_CH_UA = '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"'
DEFAULT_SEC_CH_UA_MOBILE = "?0"
DEFAULT_SEC_CH_UA_PLATFORM = '"macOS"'
BASE_COLUMNS = [
    "codigoMesa",
    "id",
    "idEleccion",
    "ubigeoNivel01",
    "ubigeoNivel02",
    "ubigeoNivel03",
    "centroPoblado",
    "nombreLocalVotacion",
    "totalElectoresHabiles",
    "totalVotosEmitidos",
    "totalVotosValidos",
    "estadoActa",
    "estadoComputo",
    "codigoEstadoActa",
    "descripcionEstadoActa",
    "estadoActaResolucion",
    "estadoDescripcionActaResolucion",
    "descripcionSubEstadoActa",
]
ALLOWED_RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}

STATUS_PENDING = "PENDING"
STATUS_SEARCH_OK = "SEARCH_OK"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_DETAIL_OK = "DETAIL_OK"
STATUS_FAILED_TEMP = "FAILED_TEMP"
STATUS_FAILED_FINAL = "FAILED_FINAL"
STATUS_INVALID_RESPONSE = "INVALID_RESPONSE"
STATUS_SKIPPED_ALREADY_DONE = "SKIPPED_ALREADY_DONE"

@dataclass(slots=True)
class Config:
    start: int
    end: int
    out_dir: Path
    workers: int
    timeout: float
    connect_timeout: float
    read_timeout: float
    max_retries: int
    base_delay: float
    rps: float
    resume: bool
    dry_run: bool
    user_agent: str
    cookie: str
    referer: str
    accept_language: str
    only_failed: bool
    rebuild_csv: bool
    log_level: str


class RateLimiter:
    def __init__(self, rate_per_second: float) -> None:
        self.rate_per_second = max(rate_per_second, 0.01)
        self.interval = 1.0 / self.rate_per_second
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            if now < self.next_allowed:
                sleep_for = self.next_allowed - now
                time.sleep(sleep_for)
                now = time.monotonic()
            self.next_allowed = max(self.next_allowed + self.interval, now + self.interval)


class SQLiteState:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=60000")
        return conn

    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS mesas (
                    codigo_mesa TEXT PRIMARY KEY,
                    id_interno TEXT,
                    status TEXT NOT NULL,
                    intentos INTEGER NOT NULL DEFAULT 0,
                    ultimo_error TEXT,
                    ts_inicio TEXT,
                    ts_fin TEXT,
                    json_path TEXT,
                    sha256 TEXT,
                    file_size_bytes INTEGER,
                    search_url TEXT,
                    detail_url TEXT,
                    http_status_search INTEGER,
                    http_status_detail INTEGER,
                    observaciones TEXT,
                    downloaded_at TEXT,
                    timezone TEXT,
                    skipped INTEGER NOT NULL DEFAULT 0,
                    last_updated TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_mesa TEXT NOT NULL,
                    id_interno TEXT,
                    tipo_anomalia TEXT NOT NULL,
                    detalle TEXT,
                    severity TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_mesas_status ON mesas(status);
                CREATE INDEX IF NOT EXISTS idx_anom_codigo ON anomalies(codigo_mesa);
                """
            )
            conn.commit()
        finally:
            conn.close()

    def seed_range(self, start: int, end: int) -> None:
        now = now_lima_iso()
        conn = self.conn()
        with self._write_lock:
            conn.executemany(
                """
                INSERT OR IGNORE INTO mesas(codigo_mesa, status, last_updated)
                VALUES (?, ?, ?)
                """,
                ((format_codigo_mesa(i), STATUS_PENDING, now) for i in range(start, end + 1)),
            )
            conn.commit()

    def fetch_codes(self, start: int, end: int, resume: bool, only_failed: bool) -> list[str]:
        conn = self.conn()
        start_code = format_codigo_mesa(start)
        end_code = format_codigo_mesa(end)
        if only_failed:
            rows = conn.execute(
                """
                SELECT codigo_mesa FROM mesas
                WHERE codigo_mesa BETWEEN ? AND ?
                  AND status IN (?, ?)
                ORDER BY codigo_mesa
                """,
                (start_code, end_code, STATUS_FAILED_TEMP, STATUS_FAILED_FINAL),
            ).fetchall()
            return [r[0] for r in rows]
        if not resume:
            return [format_codigo_mesa(i) for i in range(start, end + 1)]
        rows = conn.execute(
            """
            SELECT codigo_mesa FROM mesas
            WHERE codigo_mesa BETWEEN ? AND ?
              AND status NOT IN (?, ?, ?)
            ORDER BY codigo_mesa
            """,
            (start_code, end_code, STATUS_DETAIL_OK, STATUS_NOT_FOUND, STATUS_SKIPPED_ALREADY_DONE),
        ).fetchall()
        return [r[0] for r in rows]

    def get_row(self, codigo_mesa: str) -> Optional[sqlite3.Row]:
        return self.conn().execute(
            "SELECT * FROM mesas WHERE codigo_mesa = ?", (codigo_mesa,)
        ).fetchone()

    def mark_in_progress(self, codigo_mesa: str) -> None:
        now = now_lima_iso()
        conn = self.conn()
        with self._write_lock:
            conn.execute(
                """
                INSERT INTO mesas(codigo_mesa, status, intentos, ts_inicio, last_updated)
                VALUES(?, ?, 1, ?, ?)
                ON CONFLICT(codigo_mesa) DO UPDATE SET
                    intentos = mesas.intentos + 1,
                    ts_inicio = COALESCE(mesas.ts_inicio, excluded.ts_inicio),
                    last_updated = excluded.last_updated
                """,
                (codigo_mesa, STATUS_PENDING, now, now),
            )
            conn.commit()

    def update_result(self, codigo_mesa: str, **fields: Any) -> None:
        fields["last_updated"] = now_lima_iso()
        sets = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [codigo_mesa]
        conn = self.conn()
        with self._write_lock:
            conn.execute(
                f"UPDATE mesas SET {sets} WHERE codigo_mesa = ?",
                values,
            )
            conn.commit()

    def add_anomaly(
        self,
        codigo_mesa: str,
        id_interno: Optional[str],
        tipo_anomalia: str,
        detalle: str,
        severity: str,
    ) -> None:
        conn = self.conn()
        with self._write_lock:
            conn.execute(
                """
                INSERT INTO anomalies(
                    codigo_mesa, id_interno, tipo_anomalia, detalle, severity, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (codigo_mesa, id_interno, tipo_anomalia, detalle, severity, now_lima_iso()),
            )
            conn.commit()

    def iter_downloaded_rows(self) -> Iterable[sqlite3.Row]:
        cursor = self.conn().execute(
            """
            SELECT * FROM mesas
            WHERE json_path IS NOT NULL
              AND json_path != ''
              AND status NOT IN (?, ?, ?)
            ORDER BY codigo_mesa
            """,
            (STATUS_NOT_FOUND, STATUS_INVALID_RESPONSE, STATUS_FAILED_FINAL),
        )
        yield from cursor

    def summary_counts(self) -> dict[str, int]:
        rows = self.conn().execute(
            "SELECT status, COUNT(*) AS c FROM mesas GROUP BY status"
        ).fetchall()
        counts = {row[0]: row[1] for row in rows}
        counts["ANOMALIES"] = self.conn().execute(
            "SELECT COUNT(*) FROM anomalies"
        ).fetchone()[0]
        return counts

    def iter_anomalies(self) -> Iterable[sqlite3.Row]:
        yield from self.conn().execute(
            "SELECT codigo_mesa, id_interno, tipo_anomalia, detalle, severity, created_at FROM anomalies ORDER BY codigo_mesa, id"
        )


class OnpeClient:
    def __init__(self, config: Config, limiter: RateLimiter) -> None:
        self.config = config
        self.limiter = limiter
        self._local = threading.local()

    def client(self) -> Any:
        if httpx is None:
            return None
        client = getattr(self._local, "client", None)
        if client is None:
            timeout = httpx.Timeout(
                timeout=self.config.timeout,
                connect=self.config.connect_timeout,
                read=self.config.read_timeout,
            )
            headers = self._build_headers()
            client = httpx.Client(timeout=timeout, headers=headers, follow_redirects=True)
            self._local.client = client
        return client

    def close_thread_client(self) -> None:
        client = getattr(self._local, "client", None)
        if client is not None and httpx is not None:
            client.close()
            self._local.client = None

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "*/*",
            "Accept-Language": self.config.accept_language,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Content-Type": "application/json",
            "Referer": self.config.referer,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "priority": "u=1, i",
        }
        if self.config.cookie:
            headers["Cookie"] = self.config.cookie
        return headers

    def _request_json_stdlib(self, method: str, url: str, **kwargs: Any) -> tuple[Optional[dict[str, Any] | list[Any] | str], Optional[int], Optional[str]]:
        if method.upper() != "GET":
            return None, None, f"Método no soportado sin httpx: {method}"
        headers = self._build_headers()
        req = urllib.request.Request(url, headers=headers, method="GET")
        timeout = max(self.config.connect_timeout, self.config.read_timeout, self.config.timeout)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            raw = response.read()
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                return None, status, None
            return json.loads(text), status, None


    def _request_json_curl(self, method: str, url: str, **kwargs: Any) -> tuple[Optional[dict[str, Any] | list[Any] | str], Optional[int], Optional[str]]:
        if method.upper() != "GET":
            return None, None, f"Método no soportado con curl: {method}"
        curl_bin = shutil.which("curl")
        if not curl_bin:
            return None, None, "curl no disponible"
        headers = self._build_headers()
        cmd = [curl_bin, "-sS", "-D", "-", url]
        for k, v in headers.items():
            if k.lower() == "cookie":
                cmd.extend(["-b", v])
            else:
                cmd.extend(["-H", f"{k}: {v}"])
        if self.config.timeout:
            cmd.extend(["--max-time", str(int(self.config.timeout))])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return None, None, f"curl exit={proc.returncode}: {proc.stderr.strip()[:300]}"
        raw = proc.stdout
        sep = "\r\n\r\n" if "\r\n\r\n" in raw else "\n\n"
        if sep in raw:
            head, body = raw.split(sep, 1)
        else:
            head, body = raw, ""
        status = None
        content_type = ""
        for line in head.splitlines():
            if line.startswith("HTTP/"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    status = int(parts[1])
            elif line.lower().startswith("content-type:"):
                content_type = line.split(":",1)[1].strip().lower()
        text = body.strip()
        if status == 404:
            return None, 404, None
        if not text:
            return None, status, None
        if "json" not in content_type and text[:1] not in "[{":
            return None, status, f"non-json response content-type={content_type or 'unknown'}"
        try:
            return json.loads(text), status, None
        except json.JSONDecodeError as exc:
            return None, status, f"json decode error: {exc}"

    def request_json(self, method: str, url: str, **kwargs: Any) -> tuple[Optional[dict[str, Any] | list[Any] | str], Optional[int], Optional[str]]:
        last_error = None
        last_status = None
        for attempt in range(1, self.config.max_retries + 1):
            self.limiter.wait()
            try:
                payload, status, err = self._request_json_curl(method, url, **kwargs)
                last_status = status
                if err is None or status == 404:
                    return payload, status, err
                last_error = err
                if attempt >= self.config.max_retries:
                    break
            except Exception as exc:
                last_error = str(exc)
                if attempt >= self.config.max_retries:
                    break
            delay = self.config.base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            time.sleep(delay)
        return None, last_status, last_error


class Exporter:
    def __init__(self, state: SQLiteState, out_dir: Path, logger: logging.Logger) -> None:
        self.state = state
        self.out_dir = out_dir
        self.logger = logger
        self.output_dir = out_dir / "output"
        self.reports_dir = out_dir / "reports"
        self.manifest_path = out_dir / "manifests" / "download_manifest.csv"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def rebuild_outputs(self) -> None:
        rows = list(self.state.iter_downloaded_rows())
        detalhe_positions: list[int] = []
        timeline_depth = 0
        ordered_payloads: list[tuple[sqlite3.Row, dict[str, Any]]] = []

        for row in rows:
            path = row["json_path"]
            if not path:
                continue
            file_path = Path(path)
            if not file_path.exists():
                self.logger.warning("No existe raw JSON para %s: %s", row["codigo_mesa"], path)
                continue
            envelope = json.loads(file_path.read_text(encoding="utf-8"))
            payloads = envelope.get("data", []) if isinstance(envelope, dict) else []
            if not isinstance(payloads, list):
                payloads = []
            for payload in payloads:
                if not isinstance(payload, dict):
                    continue
                ordered_payloads.append((row, payload))
                for item in payload.get("detalle", []) or []:
                    try:
                        pos = int(item.get("adPosicion"))
                        if pos not in detalhe_positions:
                            detalhe_positions.append(pos)
                    except (TypeError, ValueError):
                        continue
                timeline_depth = max(timeline_depth, len(payload.get("lineaTiempo", []) or []))

        detalhe_positions.sort()
        manifest_fields = [
            "codigoMesa",
            "idInterno",
            "search_url",
            "detail_url",
            "status",
            "downloaded_at",
            "timezone",
            "json_path",
            "sha256",
            "file_size_bytes",
            "attempts",
            "http_status_search",
            "http_status_detail",
            "error",
            "observaciones",
        ]
        with self.manifest_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=manifest_fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "codigoMesa": row["codigo_mesa"],
                        "idInterno": row["id_interno"] or "",
                        "search_url": row["search_url"] or "",
                        "detail_url": row["detail_url"] or "",
                        "status": row["status"] or "",
                        "downloaded_at": row["downloaded_at"] or "",
                        "timezone": row["timezone"] or "",
                        "json_path": row["json_path"] or "",
                        "sha256": row["sha256"] or "",
                        "file_size_bytes": row["file_size_bytes"] or "",
                        "attempts": row["intentos"] or 0,
                        "http_status_search": row["http_status_search"] or "",
                        "http_status_detail": row["http_status_detail"] or "",
                        "error": row["ultimo_error"] or "",
                        "observaciones": row["observaciones"] or "",
                    }
                )

        csv_fields = list(BASE_COLUMNS)
        for pos in detalhe_positions:
            csv_fields.extend(
                [
                    f"detalle_{pos}_descripcion",
                    f"detalle_{pos}_cdocumentoIdentidad",
                    f"detalle_{pos}_nposicion",
                    f"detalle_{pos}_nvotos",
                ]
            )
        for idx in range(1, timeline_depth + 1):
            csv_fields.extend(
                [
                    f"lineaTiempo_{idx}_codigoEstadoActa",
                    f"lineaTiempo_{idx}_descripcionEstadoActa",
                    f"lineaTiempo_{idx}_descripcionEstadoActaResolucion",
                    f"lineaTiempo_{idx}_fechaRegistro",
                ]
            )

        csv_path = self.output_dir / "mesas_consolidado.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields)
            writer.writeheader()
            for row, payload in ordered_payloads:
                writer.writerow(flatten_payload(payload, detalhe_positions, timeline_depth))

        anomalies_path = self.reports_dir / "anomalias.csv"
        with anomalies_path.open("w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "codigoMesa",
                "idInterno",
                "tipo_anomalia",
                "detalle",
                "severity",
                "created_at",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.state.iter_anomalies():
                writer.writerow(
                    {
                        "codigoMesa": row["codigo_mesa"],
                        "idInterno": row["id_interno"] or "",
                        "tipo_anomalia": row["tipo_anomalia"],
                        "detalle": row["detalle"] or "",
                        "severity": row["severity"],
                        "created_at": row["created_at"],
                    }
                )

        counts = self.state.summary_counts()
        report = {
            "generated_at": now_lima_iso(),
            "timezone": "America/Lima",
            "total_mesas_en_estado": sum(v for k, v in counts.items() if k != "ANOMALIES"),
            "total_json_descargados_correctamente": counts.get(STATUS_DETAIL_OK, 0),
            "total_mesas_inexistentes": counts.get(STATUS_NOT_FOUND, 0),
            "total_fallas_definitivas": counts.get(STATUS_FAILED_FINAL, 0),
            "total_pendientes_reintento": counts.get(STATUS_FAILED_TEMP, 0),
            "total_anomalias_detectadas": counts.get("ANOMALIES", 0),
            "counts_by_status": counts,
            "detalle_positions_detected": detalhe_positions,
            "max_lineaTiempo_events": timeline_depth,
            "csv_path": str(csv_path),
            "manifest_path": str(self.manifest_path),
            "anomalias_path": str(anomalies_path),
        }
        report_path = self.reports_dir / "reporte_calidad.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info("Outputs reconstruidos: %s", csv_path)


def format_codigo_mesa(value: int | str) -> str:
    return f"{int(value):06d}"


def now_lima_iso() -> str:
    return datetime.now(TZ_LIMA).isoformat()


def setup_logging(log_path: Path, level: str) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("onpe_scraper")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(threadName)s] %(message)s"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def extract_internal_id(search_payload: Any) -> Optional[str]:
    if search_payload is None:
        return None
    if isinstance(search_payload, dict):
        for key in ("id", "idActa", "idMesa", "codigoActa"):
            value = search_payload.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        # fallback: first digit-only value with decent length
        for value in search_payload.values():
            if isinstance(value, (str, int)):
                text = str(value).strip()
                if text.isdigit() and len(text) >= 6:
                    return text
    elif isinstance(search_payload, list):
        for item in search_payload:
            internal = extract_internal_id(item)
            if internal:
                return internal
    elif isinstance(search_payload, (str, int)):
        text = str(search_payload).strip()
        if text.isdigit() and len(text) >= 6:
            return text
    return None


def relative_json_path(codigo_mesa: str) -> Path:
    return Path("raw_json") / codigo_mesa[:3] / f"{codigo_mesa}.json"


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_ts_millis(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        millis = int(value)
        dt = datetime.fromtimestamp(millis / 1000, tz=timezone.utc).astimezone(TZ_LIMA)
        return dt.isoformat()
    except Exception:
        return str(value)


def flatten_payload(payload: dict[str, Any], detalhe_positions: list[int], timeline_depth: int) -> dict[str, Any]:
    row: dict[str, Any] = {col: payload.get(col, "") for col in BASE_COLUMNS}

    if not row.get("ubigeoNivel01") and payload.get("idUbigeo") is not None:
        ub = str(payload.get("idUbigeo")).zfill(6)
        row["ubigeoNivel01"] = ub[:2]
        row["ubigeoNivel02"] = ub[:4]
        row["ubigeoNivel03"] = ub
    row.setdefault("estadoActaResolucion", payload.get("estadoActaResolucion", ""))
    row.setdefault("estadoDescripcionActaResolucion", payload.get("estadoDescripcionActaResolucion", ""))
    row.setdefault("descripcionSubEstadoActa", payload.get("descripcionSubEstadoActa", ""))

    details_by_pos: dict[int, dict[str, Any]] = {}
    for item in sorted(
        payload.get("detalle", []) or [],
        key=lambda x: safe_int(x.get("adPosicion"), default=10**9),
    ):
        pos = safe_int(item.get("adPosicion"), default=None)
        if pos is None:
            continue
        details_by_pos[pos] = item

    for pos in detalhe_positions:
        item = details_by_pos.get(pos, {})
        row[f"detalle_{pos}_descripcion"] = item.get("adDescripcion", "")
        cand = item.get("candidato") or []
        first_cand = cand[0] if cand and isinstance(cand[0], dict) else {}
        row[f"detalle_{pos}_cdocumentoIdentidad"] = first_cand.get("id", "") or ""
        row[f"detalle_{pos}_nposicion"] = item.get("adPosicion", "")
        row[f"detalle_{pos}_nvotos"] = item.get("adVotos", "")

    timeline = sorted(
        payload.get("lineaTiempo", []) or [],
        key=lambda x: safe_int(x.get("fechaRegistro"), default=10**18),
    )
    for idx in range(1, timeline_depth + 1):
        item = timeline[idx - 1] if idx - 1 < len(timeline) else {}
        row[f"lineaTiempo_{idx}_codigoEstadoActa"] = item.get("codigoEstadoActa", "")
        row[f"lineaTiempo_{idx}_descripcionEstadoActa"] = item.get("descripcionEstadoActa", "")
        row[f"lineaTiempo_{idx}_descripcionEstadoActaResolucion"] = item.get(
            "descripcionEstadoActaResolucion", ""
        )
        row[f"lineaTiempo_{idx}_fechaRegistro"] = parse_ts_millis(item.get("fechaRegistro"))

    return row


def safe_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_payload(
    codigo_mesa: str,
    internal_id: str,
    payload: dict[str, Any],
    state: SQLiteState,
) -> list[str]:
    observations: list[str] = []

    payload_codigo = str(payload.get("codigoMesa", "")).zfill(6) if payload.get("codigoMesa") is not None else ""
    if payload_codigo and payload_codigo != codigo_mesa:
        msg = f"codigoMesa inconsistente: solicitado={codigo_mesa}, json={payload_codigo}"
        state.add_anomaly(codigo_mesa, internal_id, "codigoMesa_inconsistente", msg, "high")
        observations.append(msg)

    total_validos = safe_int(payload.get("totalVotosValidos"), default=None)
    total_emitidos = safe_int(payload.get("totalVotosEmitidos"), default=None)
    total_habiles = safe_int(payload.get("totalElectoresHabiles"), default=None)

    if total_validos is not None and total_emitidos is not None and total_validos > total_emitidos:
        msg = f"totalVotosValidos ({total_validos}) > totalVotosEmitidos ({total_emitidos})"
        state.add_anomaly(codigo_mesa, internal_id, "validos_mayor_emitidos", msg, "high")
        observations.append(msg)

    if total_emitidos is not None and total_habiles is not None and total_emitidos > total_habiles:
        msg = f"totalVotosEmitidos ({total_emitidos}) > totalElectoresHabiles ({total_habiles})"
        state.add_anomaly(codigo_mesa, internal_id, "emitidos_mayor_habiles", msg, "high")
        observations.append(msg)

    detail_votes = 0
    has_any_detail_vote = False
    for item in payload.get("detalle", []) or []:
        nvotos = safe_int(item.get("adVotos"), default=None)
        if nvotos is not None:
            detail_votes += nvotos
            has_any_detail_vote = True
    if has_any_detail_vote and total_emitidos is not None and detail_votes != total_emitidos:
        msg = f"suma detalle.nvotos ({detail_votes}) != totalVotosEmitidos ({total_emitidos})"
        state.add_anomaly(codigo_mesa, internal_id, "detalle_vs_total_emitidos", msg, "medium")
        observations.append(msg)

    required = [
        "codigoMesa",
        "idUbigeo",
        "nombreLocalVotacion",
    ]
    missing = [field for field in required if field not in payload]
    if missing:
        msg = f"faltan campos clave: {', '.join(missing)}"
        state.add_anomaly(codigo_mesa, internal_id, "campos_clave_faltantes", msg, "medium")
        observations.append(msg)

    timeline = payload.get("lineaTiempo", []) or []
    last_ts = None
    for idx, item in enumerate(timeline, start=1):
        ts = safe_int(item.get("fechaRegistro"), default=None)
        if ts is None:
            msg = f"lineaTiempo[{idx}] sin fechaRegistro válida"
            state.add_anomaly(codigo_mesa, internal_id, "lineaTiempo_fecha_invalida", msg, "low")
            observations.append(msg)
            continue
        if last_ts is not None and ts < last_ts:
            msg = f"lineaTiempo no monotónica en evento {idx}"
            state.add_anomaly(codigo_mesa, internal_id, "lineaTiempo_no_monotona", msg, "medium")
            observations.append(msg)
        last_ts = ts

    return observations


def process_one(codigo_mesa: str, config: Config, state: SQLiteState, client: OnpeClient, logger: logging.Logger) -> None:
    existing = state.get_row(codigo_mesa)
    if config.resume and existing and existing["status"] == STATUS_DETAIL_OK and existing["json_path"]:
        state.update_result(codigo_mesa, status=STATUS_SKIPPED_ALREADY_DONE, skipped=1)
        logger.info("Saltando ya procesada: %s", codigo_mesa)
        return

    state.mark_in_progress(codigo_mesa)
    search_url = f"{SEARCH_URL}?codigoMesa={codigo_mesa}"

    if config.dry_run:
        state.update_result(codigo_mesa, status=STATUS_PENDING, search_url=search_url, observaciones="dry-run")
        logger.info("Dry run %s", codigo_mesa)
        return

    search_payload, http_status_search, search_error = client.request_json("GET", search_url)
    if search_error and http_status_search in (None, *ALLOWED_RETRY_STATUS):
        state.update_result(codigo_mesa, status=STATUS_FAILED_TEMP, ultimo_error=search_error, search_url=search_url, http_status_search=http_status_search, ts_fin=now_lima_iso())
        logger.warning("Falla temporal búsqueda %s: %s", codigo_mesa, search_error)
        return

    if not isinstance(search_payload, dict):
        state.update_result(codigo_mesa, status=STATUS_INVALID_RESPONSE, ultimo_error=search_error or "JSON búsqueda no es objeto", search_url=search_url, http_status_search=http_status_search, ts_fin=now_lima_iso())
        return

    data = search_payload.get("data")
    if not isinstance(data, list) or len(data) == 0:
        status = STATUS_NOT_FOUND if search_payload.get("success") is not True or not data else STATUS_INVALID_RESPONSE
        state.update_result(codigo_mesa, status=status, ultimo_error=search_error, search_url=search_url, http_status_search=http_status_search, ts_fin=now_lima_iso())
        logger.info("Mesa sin resultados %s (status=%s)", codigo_mesa, status)
        return

    raw_bytes = json.dumps(search_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha256 = compute_sha256_bytes(raw_bytes)
    rel_path = relative_json_path(codigo_mesa)
    abs_path = config.out_dir / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(raw_bytes)

    observations: list[str] = []
    for item in data:
        internal_id = str(item.get("id", ""))
        observations.extend(validate_payload(codigo_mesa, internal_id, item, state))

    ids = ",".join(str(item.get("id", "")) for item in data if item.get("id") is not None)
    state.update_result(codigo_mesa, id_interno=ids, status=STATUS_DETAIL_OK, ultimo_error=None, ts_fin=now_lima_iso(), json_path=str(abs_path), sha256=sha256, file_size_bytes=len(raw_bytes), downloaded_at=now_lima_iso(), timezone="America/Lima", search_url=search_url, http_status_search=http_status_search, observaciones=(" | ".join(observations) if observations else None))
    logger.info("OK %s -> %s registros", codigo_mesa, len(data))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Descarga y consolida actas ONPE por código de mesa",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=999999)
    parser.add_argument("--out", type=Path, default=Path("./data"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--read-timeout", type=float, default=20.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--base-delay", type=float, default=1.0)
    parser.add_argument("--rps", type=float, default=1.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--cookie", default="", help="Cookie completo para acceder al endpoint protegido")
    parser.add_argument("--cookie-file", type=Path, default=None, help="Archivo de texto con el header Cookie completo o parcial")
    parser.add_argument("--referer", default=DEFAULT_REFERER)
    parser.add_argument("--accept-language", default=DEFAULT_ACCEPT_LANGUAGE)
    parser.add_argument("--only-failed", action="store_true")
    parser.add_argument("--rebuild-csv", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser


def parse_config(args: argparse.Namespace) -> Config:
    if args.start < 1 or args.end > 999999 or args.start > args.end:
        raise SystemExit("Rango inválido: use --start >= 1, --end <= 999999 y start <= end")
    if args.workers < 1:
        raise SystemExit("--workers debe ser >= 1")
    cookie_value = ""
    if getattr(args, "cookie_file", None):
        cookie_value = args.cookie_file.read_text(encoding="utf-8").strip()
    elif getattr(args, "cookie", None):
        cookie_value = args.cookie.strip()
    if cookie_value.lower().startswith("cookie:"):
        cookie_value = cookie_value.split(":", 1)[1].strip()
    return Config(
        start=args.start,
        end=args.end,
        out_dir=args.out,
        workers=args.workers,
        timeout=args.timeout,
        connect_timeout=args.connect_timeout,
        read_timeout=args.read_timeout,
        max_retries=max(1, args.max_retries),
        base_delay=max(0.1, args.base_delay),
        rps=max(0.1, args.rps),
        resume=args.resume,
        dry_run=args.dry_run,
        user_agent=args.user_agent,
        cookie=cookie_value,
        referer=args.referer,
        accept_language=args.accept_language,
        only_failed=args.only_failed,
        rebuild_csv=args.rebuild_csv,
        log_level=args.log_level,
    )


def main() -> int:
    args = build_arg_parser().parse_args()
    config = parse_config(args)

    logger = setup_logging(config.out_dir / "logs" / "onpe_scraper.log", config.log_level)
    logger.info(
        "Inicio: rango=%s-%s out=%s workers=%s timeout=%s retries=%s rps=%s resume=%s dry_run=%s",
        format_codigo_mesa(config.start),
        format_codigo_mesa(config.end),
        config.out_dir,
        config.workers,
        config.timeout,
        config.max_retries,
        config.rps,
        config.resume,
        config.dry_run,
    )

    state = SQLiteState(config.out_dir / "state" / "onpe_scraper.sqlite")
    state.seed_range(config.start, config.end)
    exporter = Exporter(state, config.out_dir, logger)

    if config.rebuild_csv:
        exporter.rebuild_outputs()
        logger.info("Fin rebuild CSV/reportes")
        return 0

    codes = state.fetch_codes(config.start, config.end, config.resume, config.only_failed)
    logger.info("Mesas a procesar: %s", len(codes))
    limiter = RateLimiter(config.rps)
    client = OnpeClient(config, limiter)

    try:
        with ThreadPoolExecutor(max_workers=config.workers, thread_name_prefix="mesa") as executor:
            futures = [executor.submit(process_one, code, config, state, client, logger) for code in codes]
            for future in as_completed(futures):
                exc = future.exception()
                if exc:
                    logger.exception("Error no controlado en worker: %s", exc)
    finally:
        client.close_thread_client()

    exporter.rebuild_outputs()
    counts = state.summary_counts()
    logger.info("Resumen final: %s", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
