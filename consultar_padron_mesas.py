#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 A Tu Manera Digital - Fernando Gallarday
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from project_metadata import build_help_epilog

TZ_LIMA = ZoneInfo("America/Lima")
PADRON_URL = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/padron/mesa/{dni}"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)
DEFAULT_REFERER = "https://resultadoelectoral.onpe.gob.pe/main"
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


@dataclass(slots=True)
class ConsultaResult:
    dni: str
    status: str
    mesa: str
    http_status: int | None
    error: str
    consulted_at: str


class RateLimiter:
    def __init__(self, rps: float) -> None:
        self.interval = 1.0 / max(rps, 0.01)
        self.next_allowed = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        if now < self.next_allowed:
            time.sleep(self.next_allowed - now)
            now = time.monotonic()
        self.next_allowed = max(self.next_allowed + self.interval, now + self.interval)


def now_lima_iso() -> str:
    return datetime.now(TZ_LIMA).isoformat(timespec="seconds")


def normalize_dni(value: str) -> str | None:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 8:
        return None
    return digits


def mask_dni(dni: str) -> str:
    return f"{dni[:2]}****{dni[-2:]}"


def hash_dni(dni: str) -> str:
    return hashlib.sha256(dni.encode("utf-8")).hexdigest()


def load_dnis(path: Path) -> tuple[list[str], list[str]]:
    seen: set[str] = set()
    dnis: list[str] = []
    invalid_lines: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, raw in enumerate(f, start=1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            dni = normalize_dni(line)
            if not dni:
                invalid_lines.append(f"linea {line_number}: {raw.strip()}")
                continue
            if dni not in seen:
                seen.add(dni)
                dnis.append(dni)

    return dnis, invalid_lines


def extract_mesa(payload: Any) -> str:
    candidates = {"mesa", "nromesa", "nro_mesa", "numero_mesa", "numeromesa", "codigomesa", "codigo_mesa"}

    def walk(value: Any) -> str:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized_key = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if normalized_key in candidates and item not in (None, ""):
                    return str(item).strip()
            for item in value.values():
                found = walk(item)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = walk(item)
                if found:
                    return found
        return ""

    return walk(payload)


def fetch_padron_mesa(
    dni: str,
    *,
    timeout: float,
    user_agent: str,
    referer: str,
) -> tuple[int, Any]:
    url = PADRON_URL.format(dni=dni)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-419,es;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": referer,
            "User-Agent": user_agent,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="replace")
        try:
            return int(response.status), json.loads(text)
        except json.JSONDecodeError:
            return int(response.status), {"raw": text}


def query_dni(
    dni: str,
    *,
    timeout: float,
    max_retries: int,
    base_delay: float,
    user_agent: str,
    referer: str,
) -> ConsultaResult:
    last_error = ""
    last_status: int | None = None

    for attempt in range(max_retries + 1):
        try:
            http_status, payload = fetch_padron_mesa(
                dni,
                timeout=timeout,
                user_agent=user_agent,
                referer=referer,
            )
            mesa = extract_mesa(payload)
            if mesa:
                return ConsultaResult(dni, "HABILITADO", mesa, http_status, "", now_lima_iso())
            return ConsultaResult(dni, "NO_ENCONTRADO", "", http_status, "", now_lima_iso())
        except urllib.error.HTTPError as exc:
            last_status = int(exc.code)
            if exc.code == 404:
                return ConsultaResult(dni, "NO_ENCONTRADO", "", last_status, "", now_lima_iso())
            last_error = f"HTTP {exc.code}"
            retryable = exc.code in RETRY_STATUS
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            retryable = True
            last_error = str(exc)

        if not retryable or attempt >= max_retries:
            break
        sleep_for = base_delay * (2**attempt) + random.uniform(0, base_delay)
        time.sleep(sleep_for)

    return ConsultaResult(dni, "ERROR_FINAL", "", last_status, last_error, now_lima_iso())


def write_results(path: Path, results: list[ConsultaResult], include_dni: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["dni_mask", "dni_sha256", "status", "mesa", "http_status", "error", "consulted_at"]
    if include_dni:
        fieldnames.insert(0, "dni")

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = {
                "dni_mask": mask_dni(result.dni),
                "dni_sha256": hash_dni(result.dni),
                "status": result.status,
                "mesa": result.mesa,
                "http_status": "" if result.http_status is None else result.http_status,
                "error": result.error,
                "consulted_at": result.consulted_at,
            }
            if include_dni:
                row["dni"] = result.dni
            writer.writerow(row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Consulta el numero de mesa para una lista cerrada de DNIs provistos en TXT, "
            "sin generar ni barrer rangos."
        ),
        epilog=build_help_epilog(("GPT-5.5",)),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True, type=Path, help="TXT con un DNI de 8 digitos por linea")
    parser.add_argument("--output", required=True, type=Path, help="CSV de resultados")
    parser.add_argument("--rps", type=float, default=0.5, help="Consultas por segundo. Default: 0.5")
    parser.add_argument("--timeout", type=float, default=20.0, help="Timeout HTTP por consulta")
    parser.add_argument("--max-retries", type=int, default=2, help="Reintentos para errores temporales")
    parser.add_argument("--base-delay", type=float, default=1.0, help="Espera base para backoff exponencial")
    parser.add_argument("--max-dnis", type=int, default=1000, help="Maximo de DNIs por corrida")
    parser.add_argument(
        "--allow-large-batch",
        action="store_true",
        help="Permite procesar mas de --max-dnis DNIs en una sola corrida",
    )
    parser.add_argument(
        "--include-dni",
        action="store_true",
        help="Incluye el DNI completo en el CSV. Por defecto se guarda mascara y hash.",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--referer", default=DEFAULT_REFERER)
    parser.add_argument("--dry-run", action="store_true", help="Valida el TXT sin consultar ONPE")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dnis, invalid_lines = load_dnis(args.input)

    if invalid_lines:
        preview = "\n".join(invalid_lines[:10])
        raise SystemExit(f"Se encontraron lineas invalidas en {args.input}:\n{preview}")
    if not dnis:
        raise SystemExit(f"No se encontraron DNIs validos en {args.input}")
    if len(dnis) > args.max_dnis and not args.allow_large_batch:
        raise SystemExit(
            f"El archivo contiene {len(dnis)} DNIs. Ajusta --max-dnis o usa --allow-large-batch "
            "para confirmar una corrida grande sobre una lista cerrada."
        )

    if args.dry_run:
        print(f"DNIs validos unicos: {len(dnis)}")
        print("Dry run: no se consulto el endpoint de ONPE.")
        return 0

    limiter = RateLimiter(args.rps)
    results: list[ConsultaResult] = []
    for index, dni in enumerate(dnis, start=1):
        limiter.wait()
        result = query_dni(
            dni,
            timeout=args.timeout,
            max_retries=args.max_retries,
            base_delay=args.base_delay,
            user_agent=args.user_agent,
            referer=args.referer,
        )
        results.append(result)
        print(f"[{index}/{len(dnis)}] {mask_dni(dni)} -> {result.status} {result.mesa}".rstrip())

    write_results(args.output, results, args.include_dni)
    print(f"Resultados escritos en: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
