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
