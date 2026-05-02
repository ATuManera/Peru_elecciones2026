#!/usr/bin/env python3
"""Actualiza la sección de estado de datos en README.md desde el CSV presidencial."""

from __future__ import annotations

import csv
import sqlite3
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_metadata import build_argument_parser


DEFAULT_README = Path("README.md")
DEFAULT_PRESIDENCIAL_CSV = Path("data/output/por_votacion/mesas_presidencial.csv")
DEFAULT_UBIGEO_CATALOG = Path("data/output/catalogos/ubigeo_onpe_catalog.csv")
DEFAULT_PENDING_TERRITORIAL_OUTPUT = Path(
    "data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv"
)
DEFAULT_SQLITE = Path("data/state/onpe_scraper.sqlite")
README_HEADING = "## Estado de Actualización de Datos"
PENDING_STATE_ORDER = ("Para envío al JEE", "Pendiente")
FOREIGN_REGIONS = {"AFRICA", "AMERICA", "ASIA", "EUROPA", "OCEANIA"}
NON_VALID_VOTE_LABELS = {
    "VOTOS EN BLANCO",
    "VOTOS NULOS",
    "VOTOS IMPUGNADOS",
}
STATE_LABELS = {
    "Contabilizada": "Contabilizadas",
    "Para envío al JEE": "Para envío al JEE",
    "Pendiente": "Pendientes",
}
STATE_ORDER = ("Contabilizada", "Para envío al JEE", "Pendiente")
MONTHS_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


@dataclass(frozen=True)
class ReadmeStatus:
    total_mesas: int
    unique_mesas: int
    state_counts: Counter[str]
    pending_locations: Counter[tuple[str, str, str, str, str]]
    valid_votes_by_group: dict[str, int]
    non_valid_votes: int
    contabilizadas: int

    @property
    def valid_total(self) -> int:
        return sum(self.valid_votes_by_group.values())


def parse_args():
    parser = build_argument_parser(
        description=(
            "Actualiza README.md con avance presidencial, estados de mesa y votos válidos "
            "calculados desde mesas_presidencial.csv."
        ),
        assisted_coauthors=("GPT-5.5",),
    )
    parser.add_argument("--readme", type=Path, default=DEFAULT_README, help="Ruta a README.md")
    parser.add_argument(
        "--presidencial-csv",
        type=Path,
        default=DEFAULT_PRESIDENCIAL_CSV,
        help="CSV presidencial generado por split_mesas_por_votacion.py",
    )
    parser.add_argument(
        "--ubigeo-catalog",
        type=Path,
        default=DEFAULT_UBIGEO_CATALOG,
        help="Catálogo UBIGEO ONPE con nombres de región, provincia y distrito",
    )
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=DEFAULT_SQLITE,
        help="SQLite operativo usado solo como referencia si existe",
    )
    parser.add_argument(
        "--pending-territorial-output",
        type=Path,
        default=DEFAULT_PENDING_TERRITORIAL_OUTPUT,
        help="CSV de detalle territorial para mesas en JEE o pendientes",
    )
    parser.add_argument("--top", type=int, default=5, help="Cantidad de grupos a mostrar antes de Otros")
    parser.add_argument("--dry-run", action="store_true", help="Imprime la sección sin escribir README.md")
    return parser.parse_args()


def fmt_int(value: int) -> str:
    return f"{value:,}"


def fmt_pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00%"
    return f"{(numerator / denominator) * 100:.2f}%"


def today_lima() -> str:
    now = datetime.now(ZoneInfo("America/Lima"))
    return f"{now.day} de {MONTHS_ES[now.month]} de {now.year}"


def format_datetime_lima(timestamp: float) -> str:
    moment = datetime.fromtimestamp(timestamp, ZoneInfo("America/Lima"))
    return (
        f"{moment.day} de {MONTHS_ES[moment.month]} de {moment.year} "
        f"{moment:%H:%M:%S} PET"
    )


def current_git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def load_ubigeo_catalog(catalog_path: Path) -> dict[str, tuple[str, str, str]]:
    if not catalog_path.exists():
        return {}

    catalog = {}
    with catalog_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ubigeo = (row.get("ubigeo") or "").strip()
            if not ubigeo:
                continue
            catalog[ubigeo] = (
                (row.get("departamento") or "").strip() or "SIN REGIÓN",
                (row.get("provincia") or "").strip() or "SIN PROVINCIA",
                (row.get("distrito") or "").strip() or "SIN DISTRITO",
            )
            catalog.setdefault(f"D:{ubigeo[:2]}", (catalog[ubigeo][0], "", ""))
            catalog.setdefault(f"P:{ubigeo[:4]}", ("", catalog[ubigeo][1], ""))
    return catalog


def scope_from_ubigeo(ubigeo: str) -> str:
    return "EXTRANJERO" if ubigeo.startswith("92") else "PERU"


def scope_from_territory(ubigeo: str, region: str) -> str:
    return "EXTRANJERO" if region in FOREIGN_REGIONS else scope_from_ubigeo(ubigeo)


def territory_from_row(
    row: dict[str, str], ubigeo_catalog: dict[str, tuple[str, str, str]]
) -> tuple[str, str, str, str]:
    ubigeo = (row.get("ubigeoNivel03") or "").strip()
    exact = ubigeo_catalog.get(ubigeo)
    if exact:
        region, province, district = exact
    else:
        region = ubigeo_catalog.get(f"D:{ubigeo[:2]}", ("", "", ""))[0]
        province = ubigeo_catalog.get(f"P:{ubigeo[:4]}", ("", "", ""))[1]
        region = region or (row.get("ubigeoNivel01") or "").strip() or "SIN REGIÓN"
        province = province or (row.get("ubigeoNivel02") or "").strip() or "SIN PROVINCIA"
        district = f"SIN NOMBRE ({ubigeo})" if ubigeo else "SIN DISTRITO"
    scope = scope_from_territory(ubigeo, region)
    return scope, region, province, district


def vote_detail_indices(fieldnames: list[str]) -> list[str]:
    indices = []
    for field in fieldnames:
        if field.startswith("detalle_") and field.endswith("_descripcion"):
            idx = field.removeprefix("detalle_").removesuffix("_descripcion")
            if f"detalle_{idx}_nvotos" in fieldnames:
                indices.append(idx)
    return sorted(indices, key=lambda item: int(item) if item.isdigit() else item)


def read_presidential_status(
    csv_path: Path, ubigeo_catalog: dict[str, tuple[str, str, str]] | None = None
) -> ReadmeStatus:
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el CSV presidencial: {csv_path}")

    ubigeo_catalog = ubigeo_catalog or {}
    rows = 0
    mesas: set[str] = set()
    state_counts: Counter[str] = Counter()
    pending_locations: Counter[tuple[str, str, str, str, str]] = Counter()
    valid_votes_by_group: dict[str, int] = defaultdict(int)
    non_valid_votes = 0
    contabilizadas = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV sin cabecera: {csv_path}")
        detail_indices = vote_detail_indices(reader.fieldnames)

        for row in reader:
            rows += 1
            mesa = (row.get("codigoMesa") or "").strip()
            if mesa:
                mesas.add(mesa)

            state = (row.get("descripcionEstadoActa") or row.get("estado_control") or "").strip()
            state_counts[state or "Sin estado"] += 1

            if state in PENDING_STATE_ORDER:
                scope, region, province, district = territory_from_row(row, ubigeo_catalog)
                pending_locations[(state, scope, region, province, district)] += 1

            if state != "Contabilizada":
                continue

            contabilizadas += 1
            for idx in detail_indices:
                label = (row.get(f"detalle_{idx}_descripcion") or "").strip()
                raw_votes = (row.get(f"detalle_{idx}_nvotos") or "0").strip()
                if not label:
                    continue
                try:
                    votes = int(raw_votes)
                except ValueError:
                    votes = 0

                if label in NON_VALID_VOTE_LABELS:
                    non_valid_votes += votes
                else:
                    valid_votes_by_group[label] += votes

    return ReadmeStatus(
        total_mesas=rows,
        unique_mesas=len(mesas),
        state_counts=state_counts,
        pending_locations=pending_locations,
        valid_votes_by_group=dict(valid_votes_by_group),
        non_valid_votes=non_valid_votes,
        contabilizadas=contabilizadas,
    )


def sqlite_state_counts(sqlite_path: Path) -> Counter[str] | None:
    if not sqlite_path.exists():
        return None

    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT estado_control, COUNT(*)
            FROM mesa_presidencial_control
            GROUP BY estado_control
            """
        ).fetchall()

    return Counter({state or "Sin estado": count for state, count in rows})


def ordered_state_items(state_counts: Counter[str]) -> list[tuple[str, int]]:
    seen = set()
    items: list[tuple[str, int]] = []
    for state in STATE_ORDER:
        items.append((state, state_counts.get(state, 0)))
        seen.add(state)
    for state, count in state_counts.most_common():
        if state not in seen:
            items.append((state, count))
    return items


def ordered_pending_locations(
    pending_locations: Counter[tuple[str, str, str, str, str]]
) -> list[tuple[tuple[str, str, str, str, str], int]]:
    state_rank = {state: index for index, state in enumerate(PENDING_STATE_ORDER)}
    scope_rank = {"PERU": 0, "EXTRANJERO": 1}
    return sorted(
        pending_locations.items(),
        key=lambda item: (
            state_rank.get(item[0][0], 99),
            scope_rank.get(item[0][1], 99),
            item[0][2],
            item[0][3],
            item[0][4],
        ),
    )


def missing_pending_scope_rows(
    pending_locations: Counter[tuple[str, str, str, str, str]]
) -> list[tuple[tuple[str, str, str, str, str], int]]:
    present = {(state, scope) for state, scope, _, _, _ in pending_locations}
    rows = []
    for state in PENDING_STATE_ORDER:
        for scope in ("PERU", "EXTRANJERO"):
            if (state, scope) not in present:
                rows.append(((state, scope, "-", "-", "-"), 0))
    return rows


def pending_territorial_rows(
    pending_locations: Counter[tuple[str, str, str, str, str]]
) -> list[tuple[str, str, str, str, str, int]]:
    rows = [
        (state, scope, region, province, district, count)
        for (state, scope, region, province, district), count in ordered_pending_locations(
            pending_locations
        )
    ]
    rows.extend(
        (state, scope, region, province, district, count)
        for (state, scope, region, province, district), count in missing_pending_scope_rows(
            pending_locations
        )
    )
    if not rows:
        return [("Sin mesas", "-", "-", "-", "-", 0)]
    return rows


def write_pending_territorial_csv(status: ReadmeStatus, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "estado",
                "ambito",
                "region",
                "provincia",
                "distrito",
                "mesas",
                "pct_universo",
            ],
        )
        writer.writeheader()
        for state, scope, region, province, district, count in pending_territorial_rows(
            status.pending_locations
        ):
            writer.writerow(
                {
                    "estado": STATE_LABELS.get(state, state),
                    "ambito": scope,
                    "region": region,
                    "provincia": province,
                    "distrito": district,
                    "mesas": count,
                    "pct_universo": fmt_pct(count, status.total_mesas),
                }
            )


def build_section(
    status: ReadmeStatus,
    sqlite_counts: Counter[str] | None,
    top_n: int,
    csv_path: Path = DEFAULT_PRESIDENCIAL_CSV,
    pending_territorial_output: Path = DEFAULT_PENDING_TERRITORIAL_OUTPUT,
) -> str:
    csv_label = csv_path.as_posix()
    source = f"`{csv_label}`"
    if sqlite_counts and sum(sqlite_counts.values()) == status.total_mesas:
        source += " y el control SQLite local"

    snapshot = (
        "Snapshot de datos: generado automáticamente por `update_readme_status.py` "
        f"desde `{csv_label}`; CSV modificado el "
        f"**{format_datetime_lima(csv_path.stat().st_mtime)}**."
    )
    git_commit = current_git_commit()
    if git_commit:
        snapshot += f" Commit local de base: `{git_commit}`."

    top_groups = sorted(status.valid_votes_by_group.items(), key=lambda item: item[1], reverse=True)[:top_n]
    top_votes = sum(votes for _, votes in top_groups)
    other_votes = status.valid_total - top_votes

    lines = [
        README_HEADING,
        "",
        (
            f"Según {source}, las mesas presidenciales consolidadas cubren un universo de "
            f"**{fmt_int(status.total_mesas)}** mesas. Con corte de refresh al "
            f"**{today_lima()}**, el avance de mesas contabilizadas es "
            f"**{fmt_pct(status.contabilizadas, status.total_mesas)}**."
        ),
        "",
        snapshot,
        "",
        "Resumen de mesas presidenciales por estado:",
        "",
        "| Estado | Mesas | % del universo |",
        "|---|---:|---:|",
    ]

    for state, count in ordered_state_items(status.state_counts):
        label = STATE_LABELS.get(state, state)
        lines.append(f"| {label} | {fmt_int(count)} | {fmt_pct(count, status.total_mesas)} |")

    lines.extend(
        [
            "",
            "Desagregado territorial de mesas presidenciales para envío al JEE o pendientes:",
            "",
            (
                "Ver "
                f"[{pending_territorial_output.as_posix()}]"
                f"({pending_territorial_output.as_posix()})."
            ),
        ]
    )

    lines.extend(
        [
            "",
            "Votos válidos por organización política en mesas contabilizadas:",
            "",
            "| Grupo | Votos válidos | % votos válidos |",
            "|---|---:|---:|",
        ]
    )

    for group, votes in top_groups:
        lines.append(f"| {group} | {fmt_int(votes)} | {fmt_pct(votes, status.valid_total)} |")
    if other_votes:
        lines.append(
            f"| Otros candidatos | {fmt_int(other_votes)} | {fmt_pct(other_votes, status.valid_total)} |"
        )

    lines.extend(
        [
            "",
            (
                f"Blancos, nulos e impugnados suman **{fmt_int(status.non_valid_votes)}** votos "
                "y no forman parte del denominador de votos válidos ONPE."
            ),
        ]
    )
    return "\n".join(lines)


def replace_readme_section(readme_text: str, section: str) -> str:
    start = readme_text.find(README_HEADING)
    if start == -1:
        raise ValueError(f"No se encontró la sección {README_HEADING!r} en README.md")

    next_heading = readme_text.find("\n## ", start + len(README_HEADING))
    if next_heading == -1:
        return readme_text[:start] + section.rstrip() + "\n"

    return readme_text[:start] + section.rstrip() + "\n\n" + readme_text[next_heading + 1 :]


def main() -> None:
    args = parse_args()
    ubigeo_catalog = load_ubigeo_catalog(args.ubigeo_catalog)
    status = read_presidential_status(args.presidencial_csv, ubigeo_catalog)
    sqlite_counts = sqlite_state_counts(args.sqlite)
    section = build_section(
        status,
        sqlite_counts,
        args.top,
        args.presidencial_csv,
        args.pending_territorial_output,
    )

    if args.dry_run:
        print(section)
        return

    readme_text = args.readme.read_text(encoding="utf-8")
    args.readme.write_text(replace_readme_section(readme_text, section), encoding="utf-8")
    write_pending_territorial_csv(status, args.pending_territorial_output)
    print(
        "README actualizado: "
        f"{fmt_int(status.contabilizadas)}/{fmt_int(status.total_mesas)} mesas contabilizadas "
        f"({fmt_pct(status.contabilizadas, status.total_mesas)})"
    )


if __name__ == "__main__":
    main()
