#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from project_metadata import build_argument_parser


DEFAULT_NAME_MAP = {
    "10": "presidencial",
    "12": "parlamento_andino",
    "13": "diputados",
    "14": "senadores_distrito_electoral_multiple",
    "15": "senadores_distrito_electoral_unico",
}


def pick_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lower_map = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def safe_name(value: str) -> str:
    value = value.strip().lower()
    cleaned = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_"):
            cleaned.append(ch)
        else:
            cleaned.append("_")
    while "__" in "".join(cleaned):
        cleaned = list("".join(cleaned).replace("__", "_"))
    return "".join(cleaned).strip("_") or "sin_nombre"


def main() -> int:
    parser = build_argument_parser(
        description="Separa mesas_consolidado.csv en 5 archivos, uno por votación"
    )
    parser.add_argument(
        "--input",
        default="./data/output/mesas_consolidado.csv",
        help="Ruta al CSV consolidado",
    )
    parser.add_argument(
        "--outdir",
        default="./data/output/por_votacion",
        help="Directorio de salida",
    )
    parser.add_argument(
        "--column",
        default=None,
        help="Nombre exacto de la columna de elección. Si no se pasa, se autodetecta.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)

    if not input_path.exists():
        raise SystemExit(f"No existe el archivo de entrada: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

    if not fieldnames:
        raise SystemExit("El CSV no tiene cabecera o está vacío.")

    election_col = args.column or pick_column(
        fieldnames,
        ["idEleccion", "id_eleccion", "eleccion", "votacion", "idVotacion"],
    )

    if not election_col:
        raise SystemExit(
            f"No encontré columna de elección. Columnas detectadas: {fieldnames}"
        )

    counts: Counter[str] = Counter()
    output_paths: dict[str, Path] = {}
    writers: dict[str, csv.DictWriter] = {}
    handles = []

    outdir.mkdir(parents=True, exist_ok=True)

    try:
        with input_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                election_value = str(row.get(election_col, "")).strip()
                if not election_value:
                    election_value = "SIN_ID_ELECCION"

                writer = writers.get(election_value)
                if writer is None:
                    file_label = DEFAULT_NAME_MAP.get(
                        election_value, f"idEleccion_{safe_name(election_value)}"
                    )
                    output_path = outdir / f"mesas_{file_label}.csv"
                    handle = output_path.open("w", encoding="utf-8", newline="")
                    handles.append(handle)
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writers[election_value] = writer
                    output_paths[election_value] = output_path

                writer.writerow(row)
                counts[election_value] += 1
    finally:
        for handle in handles:
            handle.close()

    print("=" * 72)
    print("RESUMEN DE SEPARACIÓN")
    print("=" * 72)
    print(f"Archivo de entrada : {input_path}")
    print(f"Columna detectada  : {election_col}")
    print(f"Filas totales      : {sum(counts.values())}")
    print(f"Grupos encontrados : {len(counts)}")
    print()

    for election_value in sorted(counts.keys(), key=lambda x: (x == "SIN_ID_ELECCION", x)):
        output_path = output_paths[election_value]
        count = counts[election_value]
        print(f"idEleccion={election_value:>12s}  filas={count:>8d}  archivo={output_path}")

    print()
    print("Proceso terminado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
