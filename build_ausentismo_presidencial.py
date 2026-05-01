#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import chain
from io import BytesIO, StringIO
from pathlib import Path
from typing import Iterable, Mapping
from xml.etree import ElementTree as ET

from project_metadata import build_argument_parser


DEFAULT_INPUT_DIR = Path("data/input/onpe_historico/presidencial_primera_vuelta")
DEFAULT_2026_CSV = Path("data/output/por_votacion/mesas_presidencial.csv")
DEFAULT_OUTPUT = Path("data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv")
DEFAULT_CATALOG = Path("data/output/catalogos/ubigeo_onpe_catalog.csv")
ONPE_HISTORICAL_URL = "https://www.onpe.gob.pe/elecciones/historico-elecciones/"
UNRESOLVED_TERRITORY = "NO_RESUELTO_ONPE"

OUTPUT_FIELDS = [
    "anio",
    "fuente",
    "fuente_url",
    "codigo_mesa",
    "ubigeo",
    "departamento",
    "provincia",
    "distrito",
    "centro_poblado",
    "local_votacion",
    "tipo_eleccion",
    "estado_acta",
    "tipo_observacion",
    "electores_habiles",
    "votos_emitidos",
    "votos_validos",
    "votos_blancos",
    "votos_nulos",
    "votos_impugnados",
    "votos_no_validos",
    "ausentes",
    "tasa_ausentismo",
]
CATALOG_FIELDS = [
    "ubigeo",
    "departamento",
    "provincia",
    "distrito",
    "fuente_anios",
    "n_observaciones",
]


@dataclass(frozen=True)
class HistoricalSource:
    year: int
    filename: str
    kind: str


@dataclass(frozen=True)
class UbigeoTerritory:
    departamento: str
    provincia: str
    distrito: str
    fuente_anios: str
    n_observaciones: int


HISTORICAL_SOURCES = [
    HistoricalSource(2006, "2006_EG2006_Presidencial.csv", "csv"),
    HistoricalSource(2011, "2011_EG2011_Presidencial_0.zip", "zip_xlsx"),
    HistoricalSource(2016, "2016_EG2016_Presidencial.csv", "csv"),
    HistoricalSource(2021, "2021_Resultados_1ra_vuelta_Version_PCM.csv", "csv"),
]


def parse_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    text = text.replace(",", "")
    try:
        return int(float(text))
    except ValueError:
        return None


def format_ratio(numerator: int | None, denominator: int | None) -> str:
    if numerator is None or denominator in (None, 0):
        return ""
    return f"{numerator / denominator:.6f}"


def text(value: object) -> str:
    if value is None:
        return ""
    value_text = str(value).strip()
    if value_text.lower() in {"nan", "none", "null"}:
        return ""
    return value_text


def normalize_ubigeo(value: object) -> str:
    value_text = text(value).strip('"')
    if not value_text:
        return ""
    if value_text.isdigit():
        return value_text.zfill(6)
    return value_text


def normalized_mesa(value: object) -> str:
    value_text = text(value)
    if not value_text:
        return ""
    parsed = parse_int(value_text)
    if parsed is None:
        return value_text
    return f"{parsed:06d}"


def sum_columns(row: dict[str, object], pattern: str) -> int | None:
    total = 0
    found = False
    compiled = re.compile(pattern)
    for key, value in row.items():
        if not isinstance(key, str):
            continue
        if compiled.fullmatch(key):
            parsed = parse_int(value)
            if parsed is not None:
                total += parsed
                found = True
    return total if found else None


def read_csv_rows(path: Path) -> Iterable[dict[str, str]]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            content = path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        yield from csv.DictReader(StringIO(content), delimiter=";")
        return
    raise UnicodeDecodeError(
        "csv",
        b"",
        0,
        1,
        f"No se pudo leer {path} con utf-8-sig, cp1252 ni latin-1",
    )


def col_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref)
    if not letters:
        return 0
    result = 0
    for char in letters.group(0):
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def read_shared_strings(xlsx_zip: zipfile.ZipFile) -> list[str]:
    try:
        xml_bytes = xlsx_zip.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(xml_bytes)
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values: list[str] = []
    for item in root.findall("a:si", namespace):
        parts = [node.text or "" for node in item.findall(".//a:t", namespace)]
        values.append("".join(parts))
    return values


def cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    cell_type = cell.attrib.get("t")
    value_node = cell.find("a:v", namespace)

    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//a:t", namespace))
    if value_node is None or value_node.text is None:
        return ""
    if cell_type == "s":
        index = parse_int(value_node.text)
        if index is not None and 0 <= index < len(shared_strings):
            return shared_strings[index]
    return value_node.text


def read_first_sheet_xlsx_bytes(content: bytes) -> Iterable[dict[str, str]]:
    with zipfile.ZipFile(BytesIO(content)) as xlsx_zip:
        shared_strings = read_shared_strings(xlsx_zip)
        sheet_xml = xlsx_zip.read("xl/worksheets/sheet1.xml")
        root = ET.fromstring(sheet_xml)

    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    headers: list[str] = []

    for row_node in root.findall(".//a:sheetData/a:row", namespace):
        values: list[str] = []
        for cell in row_node.findall("a:c", namespace):
            ref = cell.attrib.get("r", "")
            index = col_index(ref)
            while len(values) <= index:
                values.append("")
            values[index] = cell_text(cell, shared_strings)

        if not headers:
            headers = [value.strip() for value in values]
            continue

        if any(value.strip() for value in values):
            yield {
                header: values[index] if index < len(values) else ""
                for index, header in enumerate(headers)
                if header
            }


def read_zip_xlsx_rows(path: Path) -> Iterable[dict[str, str]]:
    with zipfile.ZipFile(path) as outer_zip:
        xlsx_names = [name for name in outer_zip.namelist() if name.lower().endswith(".xlsx")]
        if not xlsx_names:
            raise ValueError(f"No se encontró .xlsx dentro de {path}")
        content = outer_zip.read(xlsx_names[0])
    yield from read_first_sheet_xlsx_bytes(content)


def normalize_historical_row(year: int, source_file: str, row: dict[str, object]) -> dict[str, object]:
    electores = parse_int(row.get("N_ELEC_HABIL"))
    emitidos = parse_int(row.get("N_CVAS"))
    validos = sum_columns(row, r"VOTOS_P\d+")
    blancos = parse_int(row.get("VOTOS_VB"))
    nulos = parse_int(row.get("VOTOS_VN"))
    impugnados = parse_int(row.get("VOTOS_VI"))
    no_validos = sum(value for value in (blancos, nulos, impugnados) if value is not None)
    ausentes = electores - emitidos if electores is not None and emitidos is not None else None

    return {
        "anio": year,
        "fuente": source_file,
        "fuente_url": ONPE_HISTORICAL_URL,
        "codigo_mesa": normalized_mesa(row.get("MESA_DE_VOTACION")),
        "ubigeo": normalize_ubigeo(row.get("UBIGEO")),
        "departamento": text(row.get("DEPARTAMENTO")),
        "provincia": text(row.get("PROVINCIA")),
        "distrito": text(row.get("DISTRITO")),
        "centro_poblado": "",
        "local_votacion": "",
        "tipo_eleccion": text(row.get("TIPO_ELECCION")),
        "estado_acta": text(row.get("DESCRIP_ESTADO_ACTA")),
        "tipo_observacion": text(row.get("TIPO_OBSERVACION")),
        "electores_habiles": electores,
        "votos_emitidos": emitidos,
        "votos_validos": validos,
        "votos_blancos": blancos,
        "votos_nulos": nulos,
        "votos_impugnados": impugnados,
        "votos_no_validos": no_validos,
        "ausentes": ausentes,
        "tasa_ausentismo": format_ratio(ausentes, electores),
    }


def resolve_territory(
    ubigeo: str,
    catalog: Mapping[str, UbigeoTerritory] | None,
    unresolved_ubigeos: set[str] | None = None,
) -> tuple[str, str, str]:
    if not ubigeo or catalog is None:
        return "", "", ""
    territory = catalog.get(ubigeo)
    if territory is None:
        if unresolved_ubigeos is not None:
            unresolved_ubigeos.add(ubigeo)
        return UNRESOLVED_TERRITORY, UNRESOLVED_TERRITORY, UNRESOLVED_TERRITORY
    return territory.departamento, territory.provincia, territory.distrito


def normalize_2026_row(
    row: dict[str, object],
    catalog: Mapping[str, UbigeoTerritory] | None = None,
    unresolved_ubigeos: set[str] | None = None,
) -> dict[str, object]:
    electores = parse_int(row.get("totalElectoresHabiles"))
    emitidos = parse_int(row.get("totalVotosEmitidos"))
    validos = parse_int(row.get("totalVotosValidos"))
    blancos = parse_int(row.get("detalle_80_nvotos"))
    nulos = parse_int(row.get("detalle_81_nvotos"))
    impugnados = parse_int(row.get("detalle_82_nvotos"))
    no_validos = sum(value for value in (blancos, nulos, impugnados) if value is not None)
    ausentes = electores - emitidos if electores is not None and emitidos is not None else None
    ubigeo = normalize_ubigeo(row.get("ubigeoNivel03"))
    departamento, provincia, distrito = resolve_territory(ubigeo, catalog, unresolved_ubigeos)

    return {
        "anio": 2026,
        "fuente": str(DEFAULT_2026_CSV),
        "fuente_url": "",
        "codigo_mesa": normalized_mesa(row.get("codigoMesa")),
        "ubigeo": ubigeo,
        "departamento": departamento,
        "provincia": provincia,
        "distrito": distrito,
        "centro_poblado": text(row.get("centroPoblado")),
        "local_votacion": text(row.get("nombreLocalVotacion")),
        "tipo_eleccion": "PRESIDENCIAL",
        "estado_acta": text(row.get("descripcionEstadoActa")),
        "tipo_observacion": text(row.get("descripcionSubEstadoActa")),
        "electores_habiles": electores,
        "votos_emitidos": emitidos,
        "votos_validos": validos,
        "votos_blancos": blancos,
        "votos_nulos": nulos,
        "votos_impugnados": impugnados,
        "votos_no_validos": no_validos,
        "ausentes": ausentes,
        "tasa_ausentismo": format_ratio(ausentes, electores),
    }


def iter_historical_rows(input_dir: Path) -> Iterable[dict[str, object]]:
    for source in HISTORICAL_SOURCES:
        path = input_dir / source.filename
        if not path.exists():
            raise FileNotFoundError(f"No existe el archivo histórico esperado: {path}")

        if source.kind == "csv":
            rows = read_csv_rows(path)
        elif source.kind == "zip_xlsx":
            rows = read_zip_xlsx_rows(path)
        else:
            raise ValueError(f"Tipo de fuente no soportado: {source.kind}")

        for row in rows:
            yield normalize_historical_row(source.year, source.filename, row)


def build_ubigeo_catalog(
    rows: Iterable[dict[str, object]],
) -> tuple[dict[str, UbigeoTerritory], dict[str, Counter[tuple[str, str, str]]]]:
    counts: dict[str, Counter[tuple[str, str, str]]] = defaultdict(Counter)
    years: dict[str, dict[tuple[str, str, str], set[int]]] = defaultdict(lambda: defaultdict(set))

    for row in rows:
        ubigeo = normalize_ubigeo(row.get("ubigeo"))
        departamento = text(row.get("departamento"))
        provincia = text(row.get("provincia"))
        distrito = text(row.get("distrito"))
        if not ubigeo or not departamento or not provincia or not distrito:
            continue
        key = (departamento, provincia, distrito)
        counts[ubigeo][key] += 1
        year = parse_int(row.get("anio"))
        if year is not None:
            years[ubigeo][key].add(year)

    catalog: dict[str, UbigeoTerritory] = {}
    conflicts: dict[str, Counter[tuple[str, str, str]]] = {}
    for ubigeo, options in counts.items():
        ranked = sorted(
            options,
            key=lambda key: (
                len(years[ubigeo][key]),
                options[key],
                max(years[ubigeo][key]) if years[ubigeo][key] else 0,
                key,
            ),
            reverse=True,
        )
        selected = ranked[0]
        if len(ranked) > 1:
            conflicts[ubigeo] = options
            second = ranked[1]
            selected_score = (
                len(years[ubigeo][selected]),
                options[selected],
                max(years[ubigeo][selected]) if years[ubigeo][selected] else 0,
            )
            second_score = (
                len(years[ubigeo][second]),
                options[second],
                max(years[ubigeo][second]) if years[ubigeo][second] else 0,
            )
            if selected_score == second_score:
                raise ValueError(
                    "Conflicto territorial ONPE sin resolución determinística "
                    f"para ubigeo={ubigeo}: {options}"
                )

        source_years = "|".join(str(year) for year in sorted(years[ubigeo][selected]))
        catalog[ubigeo] = UbigeoTerritory(
            departamento=selected[0],
            provincia=selected[1],
            distrito=selected[2],
            fuente_anios=source_years,
            n_observaciones=options[selected],
        )
    return catalog, conflicts


def write_ubigeo_catalog(catalog: Mapping[str, UbigeoTerritory], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        for ubigeo in sorted(catalog):
            territory = catalog[ubigeo]
            writer.writerow(
                {
                    "ubigeo": ubigeo,
                    "departamento": territory.departamento,
                    "provincia": territory.provincia,
                    "distrito": territory.distrito,
                    "fuente_anios": territory.fuente_anios,
                    "n_observaciones": territory.n_observaciones,
                }
            )
    return len(catalog)


def iter_2026_rows(
    path: Path,
    catalog: Mapping[str, UbigeoTerritory] | None = None,
    unresolved_ubigeos: set[str] | None = None,
) -> Iterable[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV presidencial 2026: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield normalize_2026_row(row, catalog, unresolved_ubigeos)


def write_rows(rows: Iterable[dict[str, object]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def main() -> int:
    parser = build_argument_parser(
        description=(
            "Construye una tabla consolidada de ausentismo presidencial por mesa "
            "para 2006, 2011, 2016, 2021 y 2026."
        ),
        assisted_coauthors=("GPT-5.5",),
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directorio con archivos históricos oficiales de ONPE",
    )
    parser.add_argument(
        "--presidencial-2026",
        default=str(DEFAULT_2026_CSV),
        help="CSV presidencial 2026 generado por split_mesas_por_votacion.py",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT),
        help="Ruta del CSV consolidado de salida",
    )
    parser.add_argument(
        "--catalog-out",
        default=str(DEFAULT_CATALOG),
        help="Ruta del catálogo territorial UBIGEO ONPE derivado de históricos",
    )
    parser.add_argument(
        "--skip-2026",
        action="store_true",
        help="No incluir el CSV presidencial 2026",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.out)
    catalog_path = Path(args.catalog_out)

    catalog, conflicts = build_ubigeo_catalog(iter_historical_rows(input_dir))
    catalog_count = write_ubigeo_catalog(catalog, catalog_path)
    rows: Iterable[dict[str, object]] = iter_historical_rows(input_dir)
    unresolved_ubigeos: set[str] = set()
    if not args.skip_2026:
        rows = chain(rows, iter_2026_rows(Path(args.presidencial_2026), catalog, unresolved_ubigeos))

    count = write_rows(rows, output_path)
    print(f"Catálogo UBIGEO ONPE generado: {catalog_path} ({catalog_count} ubigeos)")
    if conflicts:
        print(f"Conflictos territoriales resueltos por regla ONPE documentada: {len(conflicts)}")
    if unresolved_ubigeos:
        unresolved_preview = ", ".join(sorted(unresolved_ubigeos)[:20])
        print(
            "UBIGEO 2026 sin correspondencia histórica ONPE: "
            f"{len(unresolved_ubigeos)} ({unresolved_preview})"
        )
    print(f"Filas consolidadas: {count}")
    print(f"Archivo generado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
