#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from build_ausentismo_presidencial import DEFAULT_CATALOG, DEFAULT_OUTPUT
from project_metadata import build_argument_parser

DEFAULT_2026_CSV = Path("data/output/por_votacion/mesas_presidencial.csv")
EXPECTED_UBIGEO = "140130"
EXPECTED_DEPARTAMENTO = "LIMA"
EXPECTED_PROVINCIA = "LIMA"
EXPECTED_DISTRITO = "SANTIAGO DE SURCO"
EXPECTED_MESA = "050915"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_catalog(catalog_path: Path) -> list[str]:
    errors: list[str] = []
    rows = read_csv(catalog_path)
    by_ubigeo = {row.get("ubigeo", ""): row for row in rows}
    row = by_ubigeo.get(EXPECTED_UBIGEO)
    if row is None:
        return [f"No existe {EXPECTED_UBIGEO} en {catalog_path}"]

    expected = {
        "departamento": EXPECTED_DEPARTAMENTO,
        "provincia": EXPECTED_PROVINCIA,
        "distrito": EXPECTED_DISTRITO,
    }
    for field, value in expected.items():
        if row.get(field) != value:
            errors.append(f"{catalog_path}: {EXPECTED_UBIGEO}.{field}={row.get(field)!r}, esperado {value!r}")
    return errors


def validate_2026_source(presidencial_2026: Path) -> list[str]:
    errors: list[str] = []
    rows = read_csv(presidencial_2026)
    matches = [row for row in rows if row.get("codigoMesa") == EXPECTED_MESA]
    if not matches:
        return [f"No existe mesa {EXPECTED_MESA} en {presidencial_2026}"]
    row = matches[0]
    if row.get("ubigeoNivel03") != EXPECTED_UBIGEO:
        errors.append(
            f"{presidencial_2026}: mesa {EXPECTED_MESA} ubigeoNivel03="
            f"{row.get('ubigeoNivel03')!r}, esperado {EXPECTED_UBIGEO!r}"
        )
    return errors


def validate_ausentismo(output_path: Path) -> list[str]:
    errors: list[str] = []
    rows = read_csv(output_path)
    matches = [
        row
        for row in rows
        if row.get("anio") == "2026" and row.get("codigo_mesa") == EXPECTED_MESA
    ]
    if not matches:
        errors.append(f"No existe mesa {EXPECTED_MESA} de 2026 en {output_path}")
    else:
        row = matches[0]
        expected = {
            "ubigeo": EXPECTED_UBIGEO,
            "departamento": EXPECTED_DEPARTAMENTO,
            "provincia": EXPECTED_PROVINCIA,
            "distrito": EXPECTED_DISTRITO,
        }
        for field, value in expected.items():
            if row.get(field) != value:
                errors.append(
                    f"{output_path}: mesa {EXPECTED_MESA} {field}={row.get(field)!r}, "
                    f"esperado {value!r}"
                )

    bad_lambayeque = [
        row
        for row in rows
        if row.get("ubigeo", "").startswith("14") and row.get("departamento") == "LAMBAYEQUE"
    ]
    if bad_lambayeque:
        sample = bad_lambayeque[0]
        errors.append(
            "Hay registros ONPE con ubigeo prefijo 14 rotulados como LAMBAYEQUE; "
            f"ejemplo anio={sample.get('anio')} mesa={sample.get('codigo_mesa')}"
        )
    return errors


def main() -> int:
    parser = build_argument_parser(
        description="Valida el mapeo territorial UBIGEO ONPE usado por outputs derivados.",
        assisted_coauthors=("GPT-5.5",),
    )
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Catálogo UBIGEO ONPE")
    parser.add_argument(
        "--presidencial-2026",
        default=str(DEFAULT_2026_CSV),
        help="CSV presidencial 2026 generado desde JSON ONPE",
    )
    parser.add_argument("--ausentismo", default=str(DEFAULT_OUTPUT), help="CSV consolidado de ausentismo")
    args = parser.parse_args()

    errors: list[str] = []
    errors.extend(validate_catalog(Path(args.catalog)))
    errors.extend(validate_2026_source(Path(args.presidencial_2026)))
    errors.extend(validate_ausentismo(Path(args.ausentismo)))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Validación UBIGEO ONPE OK")
    print(
        f"Mesa {EXPECTED_MESA}: ubigeo={EXPECTED_UBIGEO}, "
        f"{EXPECTED_DEPARTAMENTO}/{EXPECTED_PROVINCIA}/{EXPECTED_DISTRITO}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
