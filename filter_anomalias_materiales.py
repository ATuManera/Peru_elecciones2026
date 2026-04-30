#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from project_metadata import build_argument_parser


def pick_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lower_map = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def normalize(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def main() -> int:
    parser = build_argument_parser(
        description="Genera anomalias_materiales.csv excluyendo tipos no materiales"
    )
    parser.add_argument(
        "--input",
        default="./data/reports/anomalias.csv",
        help="Ruta al anomalias.csv original",
    )
    parser.add_argument(
        "--output",
        default="./data/reports/anomalias_materiales.csv",
        help="Ruta del CSV filtrado",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["lineaTiempo_no_monotona"],
        help="Tipos de anomalía a excluir",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"No existe el archivo de entrada: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if not fieldnames:
        raise SystemExit("El CSV de entrada no tiene cabecera o está vacío.")

    tipo_col = pick_column(
        fieldnames,
        ["tipo_anomalia", "tipo", "anomalia", "anomaly_type"],
    )
    sev_col = pick_column(
        fieldnames,
        ["severity", "severidad", "nivel", "criticidad"],
    )
    mesa_col = pick_column(
        fieldnames,
        ["codigoMesa", "codigo_mesa", "mesa"],
    )

    if not tipo_col:
        raise SystemExit(
            f"No encontré columna de tipo. Columnas detectadas: {fieldnames}"
        )

    excluded = {x.strip() for x in args.exclude if x and x.strip()}

    filtered_rows = []
    excluded_count = 0

    for row in rows:
        tipo = normalize(row.get(tipo_col), "DESCONOCIDO")
        if tipo in excluded:
            excluded_count += 1
            continue
        filtered_rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

    total_original = len(rows)
    total_material = len(filtered_rows)

    tipo_counter: Counter[str] = Counter()
    sev_counter: Counter[str] = Counter()
    mesas = set()

    for row in filtered_rows:
        tipo = normalize(row.get(tipo_col), "DESCONOCIDO")
        tipo_counter[tipo] += 1
        if sev_col:
            sev = normalize(row.get(sev_col), "SIN_SEVERIDAD")
            sev_counter[sev] += 1
        if mesa_col:
            mesa = normalize(row.get(mesa_col))
            if mesa:
                mesas.add(mesa)

    print("=" * 72)
    print("RESUMEN FILTRADO")
    print("=" * 72)
    print(f"Archivo original        : {input_path}")
    print(f"Archivo material        : {output_path}")
    print(f"Total anomalías original: {total_original}")
    print(f"Excluidas               : {excluded_count}")
    print(f"Materiales restantes    : {total_material}")
    if mesa_col:
        print(f"Mesas únicas restantes  : {len(mesas)}")
    print()

    print("Tipos excluidos:")
    for x in sorted(excluded):
        print(f"- {x}")
    print()

    if total_material:
        print("=" * 72)
        print("TOP TIPOS MATERIALES")
        print("=" * 72)
        for tipo, count in tipo_counter.most_common(20):
            print(f"{tipo:35s} {count:10d}")
        print()

        if sev_col:
            print("=" * 72)
            print("SEVERIDAD DE MATERIALES")
            print("=" * 72)
            for sev, count in sev_counter.most_common():
                print(f"{sev:20s} {count:10d}")
    else:
        print("No quedaron anomalías materiales luego del filtrado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
