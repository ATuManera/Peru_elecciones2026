import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_scripts_show_help():
    for script in (
        "onpe_scraper.py",
        "refresh_presidencial_only_v2.py",
        "split_mesas_por_votacion.py",
        "analyze_ausentismo_presidencial.py",
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


def test_analyze_ausentismo_helpers_normalize_and_classify():
    from analyze_ausentismo_presidencial import classify_state, normalize_ubigeo

    assert normalize_ubigeo("10101") == ("010101", "10101")
    assert normalize_ubigeo("010101") == ("010101", "010101")
    assert classify_state("Acta electoral resuelta") == "resuelta"
    assert classify_state("Mesa no instalada") == "sin_instalar"
    assert classify_state("Contabilizada") == "contabilizada_normal"


def test_analyze_ausentismo_builds_baseline_and_flags():
    from analyze_ausentismo_presidencial import (
        UbigeoYear,
        build_baselines,
        build_excess_flags,
        enrich_geography,
    )

    grouped = {
        (2011, "010101"): UbigeoYear(
            2011, "010101", "AMAZONAS", "CHACHAPOYAS", "CHACHAPOYAS",
            electores_habiles=1000, votos_emitidos=850, ausentes=150
        ),
        (2016, "010101"): UbigeoYear(
            2016, "010101", "AMAZONAS", "CHACHAPOYAS", "CHACHAPOYAS",
            electores_habiles=1000, votos_emitidos=810, ausentes=190
        ),
        (2026, "010101"): UbigeoYear(
            2026, "010101", "", "", "",
            electores_habiles=1000, votos_emitidos=700, ausentes=300
        ),
    }
    enrich_geography(grouped)

    baselines = build_baselines(grouped)
    flags = build_excess_flags(grouped, baselines)
    short = next(row for row in flags if row["baseline"] == "baseline_short_2011_2016")

    assert grouped[(2026, "010101")].departamento == "AMAZONAS"
    assert short["tasa_esperada"] == "0.170000"
    assert short["exceso_ausentes_positivo"] == "130.000000"
    assert short["interpretacion_flag"] in {
        "senal_estadistica_fuerte_para_revision",
        "senal_estadistica_para_revision",
        "senal_exploratoria_para_revision",
        "sin_flag",
    }
