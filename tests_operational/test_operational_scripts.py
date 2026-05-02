import csv
import subprocess
import sys
from pathlib import Path

from build_ausentismo_presidencial import (
    UNRESOLVED_TERRITORY,
    build_ubigeo_catalog,
    normalize_2026_row,
)


ROOT = Path(__file__).resolve().parents[1]


def test_main_scripts_show_help():
    for script in (
        "onpe_scraper.py",
        "refresh_presidencial_only_v2.py",
        "split_mesas_por_votacion.py",
        "build_ausentismo_presidencial.py",
        "validate_ubigeo_onpe_mapping.py",
        "consultar_padron_mesas.py",
        "update_readme_status.py",
    ):
        result = subprocess.run(
            [sys.executable, str(ROOT / script), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout


def test_split_mesas_por_votacion_creates_expected_files(tmp_path):
    input_path = tmp_path / "mesas_consolidado.csv"
    outdir = tmp_path / "por_votacion"

    with input_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["codigoMesa", "idEleccion", "valor"])
        writer.writeheader()
        writer.writerows(
            [
                {"codigoMesa": "000001", "idEleccion": "10", "valor": "a"},
                {"codigoMesa": "000001", "idEleccion": "12", "valor": "b"},
                {"codigoMesa": "000002", "idEleccion": "10", "valor": "c"},
            ]
        )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "split_mesas_por_votacion.py"),
            "--input",
            str(input_path),
            "--outdir",
            str(outdir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (outdir / "mesas_presidencial.csv").exists()
    assert (outdir / "mesas_parlamento_andino.csv").exists()
    assert "Filas totales      : 3" in result.stdout


def test_catalogo_ubigeo_onpe_resuelve_140130_para_2026():
    catalog, _ = build_ubigeo_catalog(
        [
            {
                "anio": 2016,
                "ubigeo": "140130",
                "departamento": "LIMA",
                "provincia": "LIMA",
                "distrito": "SANTIAGO DE SURCO",
            }
        ]
    )

    row = normalize_2026_row(
        {
            "codigoMesa": "050915",
            "ubigeoNivel03": "140130",
            "totalElectoresHabiles": "300",
            "totalVotosEmitidos": "175",
        },
        catalog,
    )

    assert row["codigo_mesa"] == "050915"
    assert row["ubigeo"] == "140130"
    assert row["departamento"] == "LIMA"
    assert row["provincia"] == "LIMA"
    assert row["distrito"] == "SANTIAGO DE SURCO"


def test_ubigeo_2026_sin_catalogo_no_usa_fallback_externo():
    unresolved: set[str] = set()
    row = normalize_2026_row({"codigoMesa": "1", "ubigeoNivel03": "999999"}, {}, unresolved)

    assert unresolved == {"999999"}
    assert row["departamento"] == UNRESOLVED_TERRITORY
    assert row["provincia"] == UNRESOLVED_TERRITORY
    assert row["distrito"] == UNRESOLVED_TERRITORY


def test_outputs_versionados_validan_ubigeo_onpe():
    result = subprocess.run(
        [sys.executable, str(ROOT / "validate_ubigeo_onpe_mapping.py")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Validación UBIGEO ONPE OK" in result.stdout


def test_consultar_padron_mesas_loads_unique_valid_dnis(tmp_path):
    from consultar_padron_mesas import extract_mesa, load_dnis, mask_dni

    input_path = tmp_path / "dnis.txt"
    input_path.write_text(
        "\n".join(
            [
                "12345678",
                "12-345-678 # comentario",
                "",
                "87654321",
            ]
        ),
        encoding="utf-8",
    )

    dnis, invalid = load_dnis(input_path)

    assert dnis == ["12345678", "87654321"]
    assert invalid == []
    assert mask_dni("12345678") == "12****78"
    assert extract_mesa({"data": {"codigoMesa": "050915"}}) == "050915"


def test_update_readme_status_replaces_section_from_presidential_csv(tmp_path):
    from update_readme_status import (
        build_section,
        load_ubigeo_catalog,
        read_presidential_status,
        replace_readme_section,
        write_pending_territorial_csv,
        write_pending_territorial_markdown,
    )

    csv_path = tmp_path / "mesas_presidencial.csv"
    catalog_path = tmp_path / "ubigeo_onpe_catalog.csv"
    pending_output = tmp_path / "desagregado_pendientes.csv"
    pending_markdown = tmp_path / "desagregado_pendientes.md"
    readme = "\n".join(
        [
            "# Proyecto",
            "",
            "## Estado de Actualización de Datos",
            "",
            "Texto viejo.",
            "",
            "## Alcance Actual",
            "",
            "Contenido siguiente.",
            "",
        ]
    )
    fieldnames = [
        "codigoMesa",
        "descripcionEstadoActa",
        "ubigeoNivel01",
        "ubigeoNivel02",
        "ubigeoNivel03",
        "detalle_1_descripcion",
        "detalle_1_nvotos",
        "detalle_2_descripcion",
        "detalle_2_nvotos",
        "detalle_3_descripcion",
        "detalle_3_nvotos",
    ]
    rows = [
        {
            "codigoMesa": "000001",
            "descripcionEstadoActa": "Contabilizada",
            "ubigeoNivel01": "14",
            "ubigeoNivel02": "1401",
            "ubigeoNivel03": "140130",
            "detalle_1_descripcion": "FUERZA POPULAR",
            "detalle_1_nvotos": "17",
            "detalle_2_descripcion": "JUNTOS POR EL PERÚ",
            "detalle_2_nvotos": "12",
            "detalle_3_descripcion": "VOTOS NULOS",
            "detalle_3_nvotos": "3",
        },
        {
            "codigoMesa": "000002",
            "descripcionEstadoActa": "Contabilizada",
            "ubigeoNivel01": "14",
            "ubigeoNivel02": "1401",
            "ubigeoNivel03": "140130",
            "detalle_1_descripcion": "FUERZA POPULAR",
            "detalle_1_nvotos": "1",
            "detalle_2_descripcion": "RENOVACIÓN POPULAR",
            "detalle_2_nvotos": "10",
            "detalle_3_descripcion": "VOTOS EN BLANCO",
            "detalle_3_nvotos": "2",
        },
        {
            "codigoMesa": "000003",
            "descripcionEstadoActa": "Para envío al JEE",
            "ubigeoNivel01": "92",
            "ubigeoNivel02": "9202",
            "ubigeoNivel03": "920202",
            "detalle_1_descripcion": "FUERZA POPULAR",
            "detalle_1_nvotos": "999",
            "detalle_2_descripcion": "RENOVACIÓN POPULAR",
            "detalle_2_nvotos": "999",
            "detalle_3_descripcion": "VOTOS NULOS",
            "detalle_3_nvotos": "999",
        },
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with catalog_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ubigeo",
                "departamento",
                "provincia",
                "distrito",
                "fuente_anios",
                "n_observaciones",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "ubigeo": "920202",
                "departamento": "AMERICA",
                "provincia": "ARGENTINA",
                "distrito": "BUENOS AIRES",
                "fuente_anios": "2021",
                "n_observaciones": "1",
            }
        )

    status = read_presidential_status(csv_path, load_ubigeo_catalog(catalog_path))
    section = build_section(
        status,
        sqlite_counts=None,
        top_n=2,
        csv_path=csv_path,
        pending_territorial_output=pending_output,
        pending_territorial_markdown_output=pending_markdown,
    )
    updated = replace_readme_section(readme, section)
    write_pending_territorial_csv(status, pending_output)
    write_pending_territorial_markdown(status, pending_markdown, pending_output)
    pending_rows = list(csv.DictReader(pending_output.open(encoding="utf-8-sig", newline="")))
    pending_markdown_text = pending_markdown.read_text(encoding="utf-8")

    assert "| Contabilizadas | 2 | 66.67% |" in updated
    assert "| Para envío al JEE | 1 | 33.33% |" in updated
    assert pending_output.read_bytes().startswith(b"\xef\xbb\xbf")
    assert f"[{pending_output.as_posix()}]({pending_output.as_posix()})" in updated
    assert f"[{pending_markdown.as_posix()}]({pending_markdown.as_posix()})" in updated
    assert "| Para envío al JEE | EXTRANJERO | AMERICA | ARGENTINA | BUENOS AIRES |" not in updated
    assert (
        "| Para envío al JEE | EXTRANJERO | AMERICA | ARGENTINA | BUENOS AIRES | "
        "1 | 33.33% |"
    ) in pending_markdown_text
    assert {
        "estado": "Para envío al JEE",
        "ambito": "EXTRANJERO",
        "region": "AMERICA",
        "provincia": "ARGENTINA",
        "distrito": "BUENOS AIRES",
        "mesas": "1",
        "pct_universo": "33.33%",
    } in pending_rows
    assert {
        "estado": "Pendientes",
        "ambito": "PERU",
        "region": "-",
        "provincia": "-",
        "distrito": "-",
        "mesas": "0",
        "pct_universo": "0.00%",
    } in pending_rows
    assert "| FUERZA POPULAR | 18 | 45.00% |" in updated
    assert "| JUNTOS POR EL PERÚ | 12 | 30.00% |" in updated
    assert "| Otros candidatos | 10 | 25.00% |" in updated
    assert "Snapshot de datos: generado automáticamente por `update_readme_status.py`" in updated
    assert f"desde `{csv_path.as_posix()}`" in updated
    assert "Blancos, nulos e impugnados suman **5** votos" in updated
    assert "## Alcance Actual" in updated
