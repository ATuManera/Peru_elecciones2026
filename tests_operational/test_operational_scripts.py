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
