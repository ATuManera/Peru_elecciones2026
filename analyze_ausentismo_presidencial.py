#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from project_metadata import build_argument_parser


DISCLAIMER = (
    "Estos resultados son estimaciones contrafactuales bajo supuestos explícitos. "
    "No constituyen evidencia de manipulación electoral, fraude ni causalidad. "
    "Su propósito es analítico y exploratorio."
)

DEFAULT_ABSENTEEISM_CSV = Path(
    "data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv"
)
DEFAULT_PRESIDENTIAL_2026_CSV = Path("data/output/por_votacion/mesas_presidencial.csv")
DEFAULT_OUTPUT_DIR = Path("data/output/analisis_ausentismo")
DEFAULT_REPORT = Path("FINAL_REPORT.md")

BASELINES = {
    "baseline_short_2011_2016": (2011, 2016),
    "baseline_long_2006_2011_2016": (2006, 2011, 2016),
    "baseline_recent_2016_2021": (2016, 2021),
    "baseline_robust_median_mad": (2011, 2016, 2021),
}

ABSENTEEISM_FIELDS = [
    "anio",
    "fuente",
    "codigo_mesa",
    "ubigeo",
    "ubigeo_original",
    "ubigeo_normalizado",
    "departamento",
    "provincia",
    "distrito",
    "estado_acta",
    "estado_operacional",
    "electores_habiles",
    "votos_emitidos",
    "votos_validos",
    "votos_blancos",
    "votos_nulos",
    "votos_impugnados",
    "votos_no_validos",
    "ausentes",
    "tasa_ausentismo",
    "nucleo_completo",
]


@dataclass
class UbigeoYear:
    anio: int
    ubigeo: str
    departamento: str
    provincia: str
    distrito: str
    mesas: int = 0
    electores_habiles: int = 0
    votos_emitidos: int = 0
    votos_validos: int = 0
    votos_blancos: int = 0
    votos_nulos: int = 0
    votos_impugnados: int = 0
    votos_no_validos: int = 0
    ausentes: int = 0
    filas_nucleo_incompleto: int = 0

    @property
    def tasa_ausentismo(self) -> float | None:
        if self.electores_habiles <= 0:
            return None
        return self.ausentes / self.electores_habiles


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


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


def text(value: object) -> str:
    if value is None:
        return ""
    value_text = str(value).strip()
    if value_text.lower() in {"nan", "none", "null"}:
        return ""
    return value_text


def normalize_ubigeo(value: object) -> tuple[str, str]:
    original = text(value)
    digits = "".join(ch for ch in original if ch.isdigit())
    if digits and len(digits) <= 6:
        return digits.zfill(6), original
    return original, original


def classify_state(value: str) -> str:
    state = value.upper()
    if "SIN INSTALAR" in state or "MESA NO INSTALADA" in state:
        return "sin_instalar"
    if "ANULAD" in state:
        return "anulada"
    if "RESUELT" in state:
        return "resuelta"
    if "CONTABILIZ" in state or "COMPUTAD" in state or "NORMAL" in state:
        return "contabilizada_normal"
    if "PENDIENTE" in state or "PROCESO" in state or "ENVIO" in state or "ENVÍO" in state:
        return "en_proceso"
    return "otro"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "no_disponible"


def median_absolute_deviation(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    return median, mad


def sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    std = statistics.stdev(values)
    return std if std > 0 else None


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[int(index)]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def read_absenteeism_rows(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    audit: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    duplicate_count = 0
    malformed_mesa = 0
    malformed_ubigeo = 0
    negative_absent = 0
    emitidos_gt_electores = 0
    formula_mismatch = 0
    incomplete_core = 0

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            anio = text(raw.get("anio"))
            codigo_mesa = text(raw.get("codigo_mesa"))
            key = (anio, codigo_mesa)
            if key in seen:
                duplicate_count += 1
            seen.add(key)

            if len(codigo_mesa) != 6 or not codigo_mesa.isdigit():
                malformed_mesa += 1

            ubigeo, ubigeo_original = normalize_ubigeo(raw.get("ubigeo"))
            ubigeo_normalizado = "1" if ubigeo != ubigeo_original else "0"
            if len(ubigeo) != 6 or not ubigeo.isdigit():
                malformed_ubigeo += 1

            electores = parse_int(raw.get("electores_habiles"))
            emitidos = parse_int(raw.get("votos_emitidos"))
            ausentes = parse_int(raw.get("ausentes"))
            nucleo_completo = electores is not None and emitidos is not None and ausentes is not None
            if not nucleo_completo:
                incomplete_core += 1
            else:
                if ausentes < 0:
                    negative_absent += 1
                if emitidos > electores:
                    emitidos_gt_electores += 1
                if ausentes != electores - emitidos:
                    formula_mismatch += 1

            row = {
                "anio": anio,
                "fuente": text(raw.get("fuente")),
                "codigo_mesa": codigo_mesa,
                "ubigeo": ubigeo,
                "ubigeo_original": ubigeo_original,
                "ubigeo_normalizado": ubigeo_normalizado,
                "departamento": text(raw.get("departamento")),
                "provincia": text(raw.get("provincia")),
                "distrito": text(raw.get("distrito")),
                "estado_acta": text(raw.get("estado_acta")),
                "estado_operacional": classify_state(text(raw.get("estado_acta"))),
                "electores_habiles": fmt(electores, 0),
                "votos_emitidos": fmt(emitidos, 0),
                "votos_validos": text(raw.get("votos_validos")),
                "votos_blancos": text(raw.get("votos_blancos")),
                "votos_nulos": text(raw.get("votos_nulos")),
                "votos_impugnados": text(raw.get("votos_impugnados")),
                "votos_no_validos": text(raw.get("votos_no_validos")),
                "ausentes": fmt(ausentes, 0),
                "tasa_ausentismo": text(raw.get("tasa_ausentismo")),
                "nucleo_completo": "1" if nucleo_completo else "0",
            }
            rows.append(row)

    checks = {
        "filas": len(rows),
        "duplicados_anio_mesa": duplicate_count,
        "codigo_mesa_malformado": malformed_mesa,
        "ubigeo_malformado": malformed_ubigeo,
        "filas_ubigeo_normalizado": sum(1 for row in rows if row["ubigeo_normalizado"] == "1"),
        "ausentismo_negativo": negative_absent,
        "votos_emitidos_mayor_electores": emitidos_gt_electores,
        "formula_ausentes_inconsistente": formula_mismatch,
        "nucleo_incompleto": incomplete_core,
    }
    for name, value in checks.items():
        audit.append(
            {
                "categoria": "validacion_ausentismo",
                "check": name,
                "estado": "ok" if value == 0 or name in {"filas", "filas_ubigeo_normalizado", "nucleo_incompleto"} else "revisar",
                "valor": str(value),
                "detalle": "Chequeo operativo reproducible sobre el consolidado de ausentismo.",
            }
        )
    return rows, audit


TERMINAL_STATES = {"contabilizada_normal", "resuelta"}


def aggregate_by_ubigeo(
    rows: list[dict[str, str]], terminal_only: bool = True
) -> dict[tuple[int, str], UbigeoYear]:
    grouped: dict[tuple[int, str], UbigeoYear] = {}
    for row in rows:
        anio = parse_int(row["anio"])
        if anio is None:
            continue
        if terminal_only and row.get("estado_operacional") not in TERMINAL_STATES:
            continue
        key = (anio, row["ubigeo"])
        if key not in grouped:
            grouped[key] = UbigeoYear(
                anio=anio,
                ubigeo=row["ubigeo"],
                departamento=row["departamento"],
                provincia=row["provincia"],
                distrito=row["distrito"],
            )
        item = grouped[key]
        item.mesas += 1
        if not item.departamento and row["departamento"]:
            item.departamento = row["departamento"]
        if not item.provincia and row["provincia"]:
            item.provincia = row["provincia"]
        if not item.distrito and row["distrito"]:
            item.distrito = row["distrito"]

        electores = parse_int(row["electores_habiles"])
        emitidos = parse_int(row["votos_emitidos"])
        ausentes = parse_int(row["ausentes"])
        if electores is None or emitidos is None or ausentes is None:
            item.filas_nucleo_incompleto += 1
            continue
        item.electores_habiles += electores
        item.votos_emitidos += emitidos
        item.ausentes += ausentes
        for attr, field in (
            ("votos_validos", "votos_validos"),
            ("votos_blancos", "votos_blancos"),
            ("votos_nulos", "votos_nulos"),
            ("votos_impugnados", "votos_impugnados"),
            ("votos_no_validos", "votos_no_validos"),
        ):
            value = parse_int(row[field])
            if value is not None:
                setattr(item, attr, getattr(item, attr) + value)
    return grouped


def enrich_geography(grouped: dict[tuple[int, str], UbigeoYear]) -> None:
    descriptors: dict[str, tuple[str, str, str]] = {}
    for (year, ubigeo), item in sorted(grouped.items()):
        if year == 2026:
            continue
        if item.departamento or item.provincia or item.distrito:
            descriptors.setdefault(ubigeo, (item.departamento, item.provincia, item.distrito))

    for (_, ubigeo), item in grouped.items():
        departamento, provincia, distrito = descriptors.get(ubigeo, ("", "", ""))
        if not item.departamento:
            item.departamento = departamento
        if not item.provincia:
            item.provincia = provincia
        if not item.distrito:
            item.distrito = distrito


def ubigeo_to_row(item: UbigeoYear) -> dict[str, str]:
    return {
        "anio": str(item.anio),
        "ubigeo": item.ubigeo,
        "departamento": item.departamento,
        "provincia": item.provincia,
        "distrito": item.distrito,
        "mesas": str(item.mesas),
        "electores_habiles": str(item.electores_habiles),
        "votos_emitidos": str(item.votos_emitidos),
        "votos_validos": str(item.votos_validos),
        "votos_blancos": str(item.votos_blancos),
        "votos_nulos": str(item.votos_nulos),
        "votos_impugnados": str(item.votos_impugnados),
        "votos_no_validos": str(item.votos_no_validos),
        "ausentes": str(item.ausentes),
        "tasa_ausentismo": fmt(item.tasa_ausentismo),
        "filas_nucleo_incompleto": str(item.filas_nucleo_incompleto),
    }


def build_baselines(grouped: dict[tuple[int, str], UbigeoYear]) -> list[dict[str, str]]:
    ubigeos = sorted({ubigeo for _, ubigeo in grouped})
    rows: list[dict[str, str]] = []
    for ubigeo in ubigeos:
        descriptor = next((grouped[key] for key in sorted(grouped) if key[1] == ubigeo), None)
        for baseline_name, years in BASELINES.items():
            rates = []
            electores_hist = 0
            for year in years:
                item = grouped.get((year, ubigeo))
                if item and item.tasa_ausentismo is not None:
                    rates.append(item.tasa_ausentismo)
                    electores_hist += item.electores_habiles
            if not rates:
                continue
            mean = sum(rates) / len(rates)
            median, mad = median_absolute_deviation(rates)
            std = sample_std(rates)
            tasa_esperada = median if baseline_name == "baseline_robust_median_mad" else mean
            rows.append(
                {
                    "ubigeo": ubigeo,
                    "departamento": descriptor.departamento if descriptor else "",
                    "provincia": descriptor.provincia if descriptor else "",
                    "distrito": descriptor.distrito if descriptor else "",
                    "baseline": baseline_name,
                    "anios_baseline": "|".join(str(year) for year in years),
                    "n_anios_disponibles": str(len(rates)),
                    "electores_historicos": str(electores_hist),
                    "tasa_media": fmt(mean),
                    "tasa_mediana": fmt(median),
                    "tasa_mad": fmt(mad),
                    "tasa_std": fmt(std),
                    "tasa_esperada": fmt(tasa_esperada),
                    "baseline_evaluable": "1" if len(rates) == len(years) else "0",
                }
            )
    return rows


def build_excess_flags(
    grouped: dict[tuple[int, str], UbigeoYear], baselines: list[dict[str, str]]
) -> list[dict[str, str]]:
    baseline_by_key = {(row["ubigeo"], row["baseline"]): row for row in baselines}
    rows: list[dict[str, str]] = []
    by_baseline: dict[str, list[float]] = defaultdict(list)

    for (ubigeo, baseline_name), baseline in baseline_by_key.items():
        observed = grouped.get((2026, ubigeo))
        if not observed or observed.tasa_ausentismo is None:
            continue
        tasa_esperada = parse_float(baseline["tasa_esperada"])
        if tasa_esperada is None:
            continue
        ausentes_esperados = observed.electores_habiles * tasa_esperada
        exceso_ausentes = observed.ausentes - ausentes_esperados
        exceso_relativo = observed.tasa_ausentismo - tasa_esperada
        std = parse_float(baseline["tasa_std"])
        mad = parse_float(baseline["tasa_mad"])
        robust_scale = 1.4826 * mad if mad is not None else None
        z_score = exceso_relativo / std if std and std > 0 else None
        robust_z = exceso_relativo / robust_scale if robust_scale and robust_scale > 0 else None
        row = {
            "ubigeo": ubigeo,
            "departamento": observed.departamento or baseline["departamento"],
            "provincia": observed.provincia or baseline["provincia"],
            "distrito": observed.distrito or baseline["distrito"],
            "baseline": baseline_name,
            "anios_baseline": baseline["anios_baseline"],
            "n_anios_disponibles": baseline["n_anios_disponibles"],
            "electores_habiles_2026": str(observed.electores_habiles),
            "votos_emitidos_2026": str(observed.votos_emitidos),
            "ausentes_2026": str(observed.ausentes),
            "tasa_ausentismo_2026": fmt(observed.tasa_ausentismo),
            "tasa_esperada": fmt(tasa_esperada),
            "ausentes_esperados": fmt(ausentes_esperados),
            "exceso_ausentes": fmt(exceso_ausentes),
            "exceso_ausentes_positivo": fmt(max(0.0, exceso_ausentes)),
            "exceso_relativo": fmt(exceso_relativo),
            "z_score": fmt(z_score),
            "robust_z": fmt(robust_z),
            "mad_scale": fmt(robust_scale),
            "flag_mad_2_5": "1" if robust_z is not None and robust_z >= 2.5 else "0",
            "flag_mad_3_0": "1" if robust_z is not None and robust_z >= 3.0 else "0",
            "flag_mad_3_5": "1" if robust_z is not None and robust_z >= 3.5 else "0",
            "flag_percentil_90": "0",
            "flag_percentil_95": "0",
            "flag_percentil_99": "0",
            "interpretacion_flag": "sin_flag",
        }
        rows.append(row)
        by_baseline[baseline_name].append(exceso_relativo)

    thresholds: dict[str, dict[str, float | None]] = {}
    for baseline_name, values in by_baseline.items():
        thresholds[baseline_name] = {
            "90": percentile(values, 0.90),
            "95": percentile(values, 0.95),
            "99": percentile(values, 0.99),
        }

    for row in rows:
        exceso_relativo = parse_float(row["exceso_relativo"])
        baseline_thresholds = thresholds[row["baseline"]]
        for label, value in baseline_thresholds.items():
            if exceso_relativo is not None and value is not None and exceso_relativo >= value:
                row[f"flag_percentil_{label}"] = "1"
        if row["flag_mad_3_5"] == "1":
            row["interpretacion_flag"] = "senal_estadistica_fuerte_para_revision"
        elif row["flag_mad_3_0"] == "1" or row["flag_percentil_99"] == "1":
            row["interpretacion_flag"] = "senal_estadistica_para_revision"
        elif row["flag_percentil_95"] == "1" or row["flag_mad_2_5"] == "1":
            row["interpretacion_flag"] = "senal_exploratoria_para_revision"
    return rows


def candidate_detail_ids(fieldnames: list[str]) -> list[int]:
    ids = []
    for name in fieldnames:
        if not name.startswith("detalle_") or not name.endswith("_descripcion"):
            continue
        middle = name.removeprefix("detalle_").removesuffix("_descripcion")
        if middle.isdigit():
            number = int(middle)
            if 1 <= number <= 79:
                ids.append(number)
    return sorted(ids)


def load_candidate_votes(path: Path) -> tuple[dict[str, dict[str, int]], dict[str, int], dict[str, str]]:
    by_ubigeo: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    national: dict[str, int] = defaultdict(int)
    labels: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        ids = candidate_detail_ids(reader.fieldnames or [])
        for raw in reader:
            ubigeo, _ = normalize_ubigeo(raw.get("ubigeoNivel03"))
            for detail_id in ids:
                desc = text(raw.get(f"detalle_{detail_id}_descripcion"))
                votes = parse_int(raw.get(f"detalle_{detail_id}_nvotos")) or 0
                if not desc:
                    continue
                candidate_id = str(detail_id)
                labels[candidate_id] = desc
                by_ubigeo[ubigeo][candidate_id] += votes
                national[candidate_id] += votes
    return by_ubigeo, dict(national), labels


def shares(votes: dict[str, int]) -> dict[str, float]:
    total = sum(votes.values())
    if total <= 0:
        return {}
    return {candidate: value / total for candidate, value in votes.items()}


def matched_shares_for_ubigeo(
    ubigeo: str,
    baseline_name: str,
    excess_by_ubigeo: dict[str, float],
    grouped: dict[tuple[int, str], UbigeoYear],
    baselines_by_key: dict[tuple[str, str], dict[str, str]],
    candidate_votes_by_ubigeo: dict[str, dict[str, int]],
    k: int,
) -> tuple[dict[str, float], str, float | None]:
    observed = grouped.get((2026, ubigeo))
    baseline = baselines_by_key.get((ubigeo, baseline_name))
    if not observed or not baseline:
        return {}, "", None
    expected = parse_float(baseline["tasa_esperada"]) or 0.0
    log_electors = math.log1p(observed.electores_habiles)
    candidates: list[tuple[float, str]] = []
    for other_key, other in grouped.items():
        other_year, other_ubigeo = other_key
        if other_year != 2026 or other_ubigeo == ubigeo:
            continue
        if sum(candidate_votes_by_ubigeo.get(other_ubigeo, {}).values()) <= 0:
            continue
        other_baseline = baselines_by_key.get((other_ubigeo, baseline_name))
        if not other_baseline:
            continue
        other_expected = parse_float(other_baseline["tasa_esperada"]) or 0.0
        dept_penalty = 0.0 if other.departamento == observed.departamento else 0.25
        province_penalty = 0.0 if other.provincia == observed.provincia else 0.10
        excess_penalty = 0.05 if excess_by_ubigeo.get(other_ubigeo, 0.0) > 0 else 0.0
        distance = (
            abs(expected - other_expected) * 10
            + abs(log_electors - math.log1p(other.electores_habiles))
            + dept_penalty
            + province_penalty
            + excess_penalty
        )
        candidates.append((distance, other_ubigeo))
    nearest = sorted(candidates)[:k]
    if not nearest:
        return {}, "", None
    weighted_votes: dict[str, float] = defaultdict(float)
    total_weight = 0.0
    distances = []
    for distance, matched_ubigeo in nearest:
        weight = 1.0 / max(distance, 0.001)
        distances.append(distance)
        for candidate, share in shares(candidate_votes_by_ubigeo.get(matched_ubigeo, {})).items():
            weighted_votes[candidate] += share * weight
        total_weight += weight
    if total_weight <= 0:
        return {}, "|".join(match for _, match in nearest), None
    return (
        {candidate: value / total_weight for candidate, value in weighted_votes.items()},
        "|".join(match for _, match in nearest),
        sum(distances) / len(distances),
    )


def build_candidate_scenarios(
    flags: list[dict[str, str]],
    grouped: dict[tuple[int, str], UbigeoYear],
    baselines: list[dict[str, str]],
    candidate_votes_by_ubigeo: dict[str, dict[str, int]],
    national_votes: dict[str, int],
    candidate_labels: dict[str, str],
    k_neighbors: int,
) -> list[dict[str, str]]:
    national_shares = shares(national_votes)
    baselines_by_key = {(row["ubigeo"], row["baseline"]): row for row in baselines}
    flags_by_baseline: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in flags:
        flags_by_baseline[row["baseline"]].append(row)

    output: list[dict[str, str]] = []
    for baseline_name, rows in flags_by_baseline.items():
        excess_by_ubigeo = {
            row["ubigeo"]: parse_float(row["exceso_ausentes_positivo"]) or 0.0 for row in rows
        }
        scenario_totals: dict[str, dict[str, float]] = {
            "distribucion_nacional": defaultdict(float),
            "distribucion_ubigeo": defaultdict(float),
            "matching_ubigeos_aproximado": defaultdict(float),
        }
        match_quality: list[float] = []
        excess_total = sum(excess_by_ubigeo.values())
        for candidate, share in national_shares.items():
            scenario_totals["distribucion_nacional"][candidate] = excess_total * share

        for row in rows:
            ubigeo = row["ubigeo"]
            excess = excess_by_ubigeo.get(ubigeo, 0.0)
            if excess <= 0:
                continue
            local_shares = shares(candidate_votes_by_ubigeo.get(ubigeo, {})) or national_shares
            for candidate, share in local_shares.items():
                scenario_totals["distribucion_ubigeo"][candidate] += excess * share

            matched_shares, _, avg_distance = matched_shares_for_ubigeo(
                ubigeo,
                baseline_name,
                excess_by_ubigeo,
                grouped,
                baselines_by_key,
                candidate_votes_by_ubigeo,
                k_neighbors,
            )
            if avg_distance is not None:
                match_quality.append(avg_distance)
            for candidate, share in (matched_shares or national_shares).items():
                scenario_totals["matching_ubigeos_aproximado"][candidate] += excess * share

        for model_name, totals in scenario_totals.items():
            for candidate, imputed in sorted(totals.items(), key=lambda item: int(item[0])):
                observed = national_votes.get(candidate, 0)
                output.append(
                    {
                        "baseline": baseline_name,
                        "modelo_imputacion": model_name,
                        "candidate_id": candidate,
                        "candidato": candidate_labels.get(candidate, ""),
                        "votos_observados_2026": str(observed),
                        "votos_imputados_contrafactuales": fmt(imputed),
                        "votos_ajustados_contrafactuales": fmt(observed + imputed),
                        "exceso_ausentes_total_modelado": fmt(excess_total),
                        "supuesto": scenario_assumption(model_name),
                        "calidad_matching_distancia_media": (
                            fmt(sum(match_quality) / len(match_quality))
                            if model_name == "matching_ubigeos_aproximado" and match_quality
                            else ""
                        ),
                        "disclaimer": DISCLAIMER,
                    }
                )
    return output


def scenario_assumption(model_name: str) -> str:
    if model_name == "distribucion_nacional":
        return "Los ausentes excedentes se distribuyen como el voto nacional observado en 2026."
    if model_name == "distribucion_ubigeo":
        return "Los ausentes excedentes se distribuyen como el voto observado en su mismo UBIGEO."
    return (
        "Los ausentes excedentes se distribuyen como UBIGEOs cercanos por tasa esperada, "
        "tamaño electoral y proximidad territorial aproximada."
    )


def build_geographic_concentration(flags: list[dict[str, str]]) -> list[dict[str, str]]:
    by_ubigeo: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"exceso": 0.0, "electores": 0.0, "flagged_z35": 0.0, "n_ubigeos": 0.0}
    )
    by_provincia: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: {"exceso": 0.0, "electores": 0.0, "n_flagged_z35": 0.0, "n_ubigeos": 0.0}
    )
    by_departamento: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"exceso": 0.0, "electores": 0.0, "n_flagged_z35": 0.0, "n_ubigeos": 0.0}
    )
    z_by_provincia: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    z_by_departamento: dict[tuple[str, str], list[float]] = defaultdict(list)

    for row in flags:
        excess = parse_float(row["exceso_ausentes_positivo"]) or 0.0
        electores = parse_float(row["electores_habiles_2026"]) or 0.0
        z = parse_float(row["robust_z"])
        flagged_z35 = 1.0 if row["flag_mad_3_5"] == "1" else 0.0
        baseline = row["baseline"]
        dept = row["departamento"]
        prov = row["provincia"]
        ubigeo = row["ubigeo"]

        k_ubigeo = (baseline, dept, prov, ubigeo)
        by_ubigeo[k_ubigeo]["exceso"] += excess
        by_ubigeo[k_ubigeo]["electores"] += electores
        by_ubigeo[k_ubigeo]["flagged_z35"] = flagged_z35
        by_ubigeo[k_ubigeo]["n_ubigeos"] = 1.0

        k_prov = (baseline, dept, prov)
        by_provincia[k_prov]["exceso"] += excess
        by_provincia[k_prov]["electores"] += electores
        by_provincia[k_prov]["n_flagged_z35"] += flagged_z35
        by_provincia[k_prov]["n_ubigeos"] += 1.0
        if z is not None:
            z_by_provincia[k_prov].append(z)

        k_dept = (baseline, dept)
        by_departamento[k_dept]["exceso"] += excess
        by_departamento[k_dept]["electores"] += electores
        by_departamento[k_dept]["n_flagged_z35"] += flagged_z35
        by_departamento[k_dept]["n_ubigeos"] += 1.0
        if z is not None:
            z_by_departamento[k_dept].append(z)

    totals: dict[str, float] = defaultdict(float)
    for (baseline, _, _, _), vals in by_ubigeo.items():
        totals[baseline] += vals["exceso"]

    rows: list[dict[str, str]] = []

    by_baseline_ubigeo: dict[str, list] = defaultdict(list)
    for key, vals in by_ubigeo.items():
        by_baseline_ubigeo[key[0]].append((key, vals))
    for baseline, items in by_baseline_ubigeo.items():
        cumulative = 0.0
        total = totals[baseline]
        for rank, (key, vals) in enumerate(
            sorted(items, key=lambda x: x[1]["exceso"], reverse=True), 1
        ):
            _, dept, prov, ubigeo = key
            cumulative += vals["exceso"]
            rows.append(
                {
                    "nivel": "ubigeo",
                    "baseline": baseline,
                    "rank": str(rank),
                    "departamento": dept,
                    "provincia": prov,
                    "ubigeo": ubigeo,
                    "electores_habiles_2026": fmt(vals["electores"], 0),
                    "exceso_ausentes_positivo": fmt(vals["exceso"]),
                    "n_ubigeos": "1",
                    "n_ubigeos_flagged_z35": fmt(vals["flagged_z35"], 0),
                    "pct_ubigeos_flagged_z35": fmt(vals["flagged_z35"]),
                    "mediana_z_robusto": "",
                    "participacion_exceso_total": fmt(vals["exceso"] / total if total else None),
                    "participacion_acumulada": fmt(cumulative / total if total else None),
                }
            )

    by_baseline_prov: dict[str, list] = defaultdict(list)
    for key, vals in by_provincia.items():
        by_baseline_prov[key[0]].append((key, vals))
    for baseline, items in by_baseline_prov.items():
        total = totals[baseline]
        for rank, (key, vals) in enumerate(
            sorted(items, key=lambda x: x[1]["exceso"], reverse=True), 1
        ):
            _, dept, prov = key
            n = vals["n_ubigeos"]
            n_flag = vals["n_flagged_z35"]
            z_values = z_by_provincia.get(key, [])
            median_z = statistics.median(z_values) if z_values else None
            rows.append(
                {
                    "nivel": "provincia",
                    "baseline": baseline,
                    "rank": str(rank),
                    "departamento": dept,
                    "provincia": prov,
                    "ubigeo": "",
                    "electores_habiles_2026": fmt(vals["electores"], 0),
                    "exceso_ausentes_positivo": fmt(vals["exceso"]),
                    "n_ubigeos": fmt(n, 0),
                    "n_ubigeos_flagged_z35": fmt(n_flag, 0),
                    "pct_ubigeos_flagged_z35": fmt(n_flag / n if n else None),
                    "mediana_z_robusto": fmt(median_z),
                    "participacion_exceso_total": fmt(vals["exceso"] / total if total else None),
                    "participacion_acumulada": "",
                }
            )

    by_baseline_dept: dict[str, list] = defaultdict(list)
    for key, vals in by_departamento.items():
        by_baseline_dept[key[0]].append((key, vals))
    for baseline, items in by_baseline_dept.items():
        total = totals[baseline]
        for rank, (key, vals) in enumerate(
            sorted(items, key=lambda x: x[1]["exceso"], reverse=True), 1
        ):
            _, dept = key
            n = vals["n_ubigeos"]
            n_flag = vals["n_flagged_z35"]
            z_values = z_by_departamento.get(key, [])
            median_z = statistics.median(z_values) if z_values else None
            rows.append(
                {
                    "nivel": "departamento",
                    "baseline": baseline,
                    "rank": str(rank),
                    "departamento": dept,
                    "provincia": "",
                    "ubigeo": "",
                    "electores_habiles_2026": fmt(vals["electores"], 0),
                    "exceso_ausentes_positivo": fmt(vals["exceso"]),
                    "n_ubigeos": fmt(n, 0),
                    "n_ubigeos_flagged_z35": fmt(n_flag, 0),
                    "pct_ubigeos_flagged_z35": fmt(n_flag / n if n else None),
                    "mediana_z_robusto": fmt(median_z),
                    "participacion_exceso_total": fmt(vals["exceso"] / total if total else None),
                    "participacion_acumulada": "",
                }
            )

    return rows


def build_sensitivity_summary(flags: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    by_baseline: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in flags:
        by_baseline[row["baseline"]].append(row)
    for baseline, baseline_rows in sorted(by_baseline.items()):
        positive_total = sum(parse_float(row["exceso_ausentes_positivo"]) or 0.0 for row in baseline_rows)
        evaluable = len(baseline_rows)
        for threshold in ("2_5", "3_0", "3_5"):
            flagged = [row for row in baseline_rows if row[f"flag_mad_{threshold}"] == "1"]
            rows.append(
                {
                    "baseline": baseline,
                    "dimension": "umbral_mad",
                    "parametro": threshold.replace("_", "."),
                    "unidades_evaluadas": str(evaluable),
                    "unidades_flag": str(len(flagged)),
                    "exceso_ausentes_positivo_total": fmt(positive_total),
                    "exceso_ausentes_positivo_flag": fmt(
                        sum(parse_float(row["exceso_ausentes_positivo"]) or 0.0 for row in flagged)
                    ),
                    "nota": "Flags interpretados como senales estadisticas para revision.",
                }
            )
        for percentile_label in ("90", "95", "99"):
            flagged = [row for row in baseline_rows if row[f"flag_percentil_{percentile_label}"] == "1"]
            rows.append(
                {
                    "baseline": baseline,
                    "dimension": "umbral_percentil",
                    "parametro": percentile_label,
                    "unidades_evaluadas": str(evaluable),
                    "unidades_flag": str(len(flagged)),
                    "exceso_ausentes_positivo_total": fmt(positive_total),
                    "exceso_ausentes_positivo_flag": fmt(
                        sum(parse_float(row["exceso_ausentes_positivo"]) or 0.0 for row in flagged)
                    ),
                    "nota": "Percentiles calculados dentro de cada baseline.",
                }
            )
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, str]], fieldnames: list[str] | None = None) -> int:
    materialized = list(rows)
    if fieldnames is None:
        fieldnames = list(materialized[0].keys()) if materialized else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def build_audit_checks(
    input_paths: list[Path],
    absenteeism_audit: list[dict[str, str]],
    grouped: dict[tuple[int, str], UbigeoYear],
    output_dir: Path,
) -> list[dict[str, str]]:
    rows = []
    for path in input_paths:
        rows.append(
            {
                "categoria": "input",
                "check": "archivo_existe",
                "estado": "ok" if path.exists() else "error",
                "valor": str(path),
                "detalle": "Existencia de archivo de entrada versionado.",
            }
        )
        if path.exists():
            rows.append(
                {
                    "categoria": "input",
                    "check": "sha256",
                    "estado": "ok",
                    "valor": sha256_file(path),
                    "detalle": str(path),
                }
            )
    rows.extend(absenteeism_audit)
    totals_by_year: dict[int, UbigeoYear] = {}
    for item in grouped.values():
        totals_by_year.setdefault(
            item.anio, UbigeoYear(item.anio, "NACIONAL", "", "", "")
        )
        total = totals_by_year[item.anio]
        total.mesas += item.mesas
        total.electores_habiles += item.electores_habiles
        total.votos_emitidos += item.votos_emitidos
        total.ausentes += item.ausentes
        total.filas_nucleo_incompleto += item.filas_nucleo_incompleto
    for year, total in sorted(totals_by_year.items()):
        rows.append(
            {
                "categoria": "resumen_anual",
                "check": f"tasa_ausentismo_{year}",
                "estado": "ok",
                "valor": fmt(total.tasa_ausentismo),
                "detalle": (
                    f"electores={total.electores_habiles}; emitidos={total.votos_emitidos}; "
                    f"ausentes={total.ausentes}; mesas={total.mesas}"
                ),
            }
        )
    rows.append(
        {
            "categoria": "ejecucion",
            "check": "commit_git",
            "estado": "ok",
            "valor": current_commit(),
            "detalle": "Commit registrado para reproducibilidad.",
        }
    )
    rows.append(
        {
            "categoria": "ejecucion",
            "check": "output_dir",
            "estado": "ok",
            "valor": str(output_dir),
            "detalle": DISCLAIMER,
        }
    )
    return rows


def get_package_version(name: str) -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version(name)
    except Exception:
        return "desconocida"


def write_config_yaml(path: Path, baselines: dict[str, tuple[int, ...]], args: object) -> None:
    baseline_primario = list(BASELINES["baseline_robust_median_mad"])
    matching_k = getattr(args, "matching_k", 5)
    lines = [
        "baseline:",
        f"  primario: {json.dumps(baseline_primario)}",
        "  cobertura_minima: 0.5",
        "  metodo: mediana_mad",
        "deteccion:",
        "  z_robusto_alerta: 3.5",
        "  exceso_absoluto_alerta_pp: 5",
        "  exceso_relativo_alerta: 0.25",
        "filtros:",
        "  estado_acta_terminal_only: true",
        "  excluir_voto_extranjero: false",
        "modelos:",
        '  imputacion: ["A", "B", "C"]',
        "  D_activado: false",
        "matching:",
        f"  k: {matching_k}",
        "  k_min: 5",
        '  features: ["electores_habiles", "tasa_baseline", "region_geo"]',
        "monte_carlo:",
        "  ejecutar: false",
        "  n_iter: 1000",
        "  seed: 20260501",
        f"salidas:",
        f"  directorio: {getattr(args, 'outdir', str(DEFAULT_OUTPUT_DIR))}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest_json(
    path: Path,
    run_id: str,
    start_utc: datetime,
    end_utc: datetime,
    input_paths: list[Path],
    output_paths: list[Path],
    counts: dict[str, int],
    args: object,
) -> None:
    manifest = {
        "run_id": run_id,
        "commit_hash": current_commit(),
        "branch": subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=False,
        ).stdout.strip(),
        "fecha_inicio_utc": start_utc.isoformat(),
        "fecha_fin_utc": end_utc.isoformat(),
        "duracion_segundos": round((end_utc - start_utc).total_seconds(), 2),
        "python_version": sys.version,
        "plataforma": platform.platform(),
        "pandas_version": get_package_version("pandas"),
        "numpy_version": get_package_version("numpy"),
        "parametros": {
            "ausentismo_csv": getattr(args, "ausentismo_csv", ""),
            "presidencial_2026": getattr(args, "presidencial_2026", ""),
            "outdir": getattr(args, "outdir", ""),
            "matching_k": getattr(args, "matching_k", 5),
            "baselines": {name: list(years) for name, years in BASELINES.items()},
            "terminal_only": True,
        },
        "seed": 20260501,
        "inputs": {
            str(p): sha256_file(p) if p.exists() else "no_existe"
            for p in input_paths
        },
        "outputs": {
            str(p): sha256_file(p) if p.exists() else "no_existe"
            for p in output_paths
        },
        "n_filas_por_archivo": counts,
        "disclaimer": DISCLAIMER,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_assumptions_md(path: Path, run_id: str) -> None:
    content = f"""# Supuestos y decisiones metodológicas

Run ID: `{run_id}`
Commit: `{current_commit()}`
Fecha: `{datetime.now(timezone.utc).isoformat()}`

## Baseline elegido

Baseline principal: **mediana/MAD sobre 2011, 2016 y 2021** (`baseline_robust_median_mad`).

**Por qué:** Combina los tres ciclos electorales históricos más recientes. La mediana es robusta
ante el dato atípico de 2021 (pandemia). El MAD mide dispersión sin asumir normalidad.
2006 se excluye del baseline principal por diferencias estructurales (tasa 11.3 %, padrón distinto).

Baselines de robustez calculados en paralelo: corto (2011/16), largo (2006/11/16), reciente (2016/21).

## Filtros aplicados

- **Estado del acta**: solo mesas con estado terminal (`contabilizada_normal`, `resuelta`).
  Se excluyen `sin_instalar`, `anulada`, `en_proceso`, `otro`.
- **Electores hábiles**: se excluyen mesas con `electores_habiles = 0` o vacío.
- **Votos emitidos**: se excluyen mesas con `votos_emitidos > electores_habiles`.
- **Núcleo incompleto**: filas sin `electores_habiles`, `votos_emitidos` o `ausentes` no
  entran a la inferencia de ubigeo.

## Modelos activados

- **Modelo A** (distribución nacional 2026): `distribucion_nacional`
- **Modelo B** (distribución local por ubigeo 2026): `distribucion_ubigeo`
- **Modelo C** (matching territorial aproximado): `matching_ubigeos_aproximado`
- **Modelo D** (bloque partidario): **no activado** — requiere archivo `bloques_partidarios.yaml`
  pre-registrado.

## Decisiones no automatizables

- Los años de baseline fueron elegidos por el diseño metodológico en `METHODOLOGY.md`;
  no se optimizaron para producir ningún resultado específico.
- El umbral de flag principal es z-robusto ≥ 3.5, conservador por diseño.

## Limitaciones reconocidas

- El matching territorial usa distancia euclidiana sobre variables disponibles; no es causal.
- 2021 incluye efectos pandemia; elevar el baseline esperado puede subestimar el exceso.
- Los ubigeos sin dato en al menos un año de baseline quedan marcados `baseline_insuficiente`.
- Las preferencias no observadas de electores ausentes **no** pueden conocerse; los modelos
  A, B y C son supuestos, no observaciones.

## {DISCLAIMER}
"""
    path.write_text(content, encoding="utf-8")


def top_rows(rows: list[dict[str, str]], baseline: str, metric: str, limit: int) -> list[dict[str, str]]:
    filtered = [row for row in rows if row.get("baseline") == baseline]
    return sorted(filtered, key=lambda row: parse_float(row.get(metric, "")) or 0.0, reverse=True)[:limit]


def build_final_report(
    report_path: Path,
    audit_rows: list[dict[str, str]],
    grouped: dict[tuple[int, str], UbigeoYear],
    flags: list[dict[str, str]],
    sensitivity: list[dict[str, str]],
    scenarios: list[dict[str, str]],
    output_dir: Path,
) -> None:
    national = []
    for (year, ubigeo), item in grouped.items():
        if ubigeo == "NACIONAL":
            continue
        if year not in {2006, 2011, 2016, 2021, 2026}:
            continue
    totals: dict[int, UbigeoYear] = {}
    for item in grouped.values():
        totals.setdefault(item.anio, UbigeoYear(item.anio, "NACIONAL", "", "", ""))
        total = totals[item.anio]
        total.mesas += item.mesas
        total.electores_habiles += item.electores_habiles
        total.votos_emitidos += item.votos_emitidos
        total.ausentes += item.ausentes
    for year, total in sorted(totals.items()):
        national.append(
            f"| {year} | {total.electores_habiles:,} | {total.votos_emitidos:,} | "
            f"{total.ausentes:,} | {fmt(total.tasa_ausentismo)} |"
        )

    baseline_summary = []
    for baseline in BASELINES:
        rows = [row for row in flags if row["baseline"] == baseline]
        positive = sum(parse_float(row["exceso_ausentes_positivo"]) or 0.0 for row in rows)
        flagged = sum(1 for row in rows if row["flag_mad_3_5"] == "1")
        baseline_summary.append(
            f"| {baseline} | {len(rows):,} | {fmt(positive)} | {flagged:,} |"
        )

    central = "baseline_short_2011_2016"
    top = top_rows(flags, central, "exceso_ausentes_positivo", 10)
    top_lines = [
        f"| {row['ubigeo']} | {row['departamento']} | {row['provincia']} | "
        f"{row['exceso_ausentes_positivo']} | {row['exceso_relativo']} | {row['interpretacion_flag']} |"
        for row in top
    ]

    scenario_summary: dict[tuple[str, str], float] = defaultdict(float)
    for row in scenarios:
        key = (row["baseline"], row["modelo_imputacion"])
        scenario_summary[key] += parse_float(row["votos_imputados_contrafactuales"]) or 0.0
    scenario_lines = [
        f"| {baseline} | {model} | {fmt(value)} |"
        for (baseline, model), value in sorted(scenario_summary.items())
    ]

    content = f"""# Reporte Final Preliminar - Analisis de Ausentismo Presidencial 2006-2026

## Alcance y disclaimer

{DISCLAIMER}

Este reporte preliminar resume un flujo reproducible construido desde archivos versionados del repositorio. Los flags se interpretan exclusivamente como senales estadisticas para revision, no como prueba de irregularidad ni de intencionalidad.

## Reproducibilidad

- Commit: `{current_commit()}`
- Fecha UTC de ejecucion: `{datetime.now(timezone.utc).isoformat()}`
- Directorio de outputs: `{output_dir}`
- Script: `analyze_ausentismo_presidencial.py`

## Tasa nacional de ausentismo

| Anio | Electores habiles | Votos emitidos | Ausentes | Tasa ausentismo |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(national)}

## Exceso estimado por baseline

| Baseline | UBIGEOs evaluados | Exceso positivo de ausentes | Flags MAD >= 3.5 |
| --- | ---: | ---: | ---: |
{chr(10).join(baseline_summary)}

## Principales contribuciones bajo baseline central

Baseline central: `baseline_short_2011_2016`.

| UBIGEO | Departamento | Provincia | Exceso positivo | Exceso relativo | Interpretacion |
| --- | --- | --- | ---: | ---: | --- |
{chr(10).join(top_lines)}

## Escenarios contrafactuales de votos

Los votos imputados no son votos observados. Cada fila depende del baseline y del modelo de imputacion.

| Baseline | Modelo | Votos imputados contrafactuales |
| --- | --- | ---: |
{chr(10).join(scenario_lines)}

## Sensibilidad

El archivo `sensitivity_summary.csv` resume sensibilidad por baseline, umbrales MAD y percentiles. Si los resultados cambian entre baselines, la lectura debe ser cautelosa y centrada en rangos.

## Calidad de datos

Los checks completos estan en `audit_checks.csv`. Puntos metodologicos relevantes:

- 2006 se usa en el baseline largo con normalizacion de UBIGEO; no es el baseline central.
- 2021 se usa como sensibilidad reciente por su contexto extraordinario.
- Las filas con nucleo incompleto no se imputan para inferencia primaria.
- La unidad primaria es UBIGEO; mesa se conserva como descomposicion secundaria.

## Outputs generados

- `audit_checks.csv`
- `absenteeism_by_mesa.csv`
- `absenteeism_by_ubigeo.csv`
- `baselines_by_ubigeo.csv`
- `excess_absenteeism_flags.csv`
- `geographic_concentration.csv`
- `candidate_impact_scenarios.csv`
- `sensitivity_summary.csv`

## Limitaciones pendientes

- El matching territorial es una aproximacion defensible con variables disponibles, no un diseno causal.
- No se modelan preferencias no observadas de personas ausentes.
- No se incorporan covariables socioeconomicas externas ni cartografia oficial para mapas.
- La comparabilidad mesa-a-mesa historica es limitada; por eso la inferencia primaria se mantiene en UBIGEO.
"""
    report_path.write_text(content, encoding="utf-8")


def main() -> int:
    start_utc = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())

    parser = build_argument_parser(
        description=(
            "Ejecuta el analisis reproducible de ausentismo presidencial 2006-2026 "
            "con baselines historicos, flags estadisticos y escenarios contrafactuales."
        ),
    )
    parser.add_argument("--ausentismo-csv", default=str(DEFAULT_ABSENTEEISM_CSV))
    parser.add_argument("--presidencial-2026", default=str(DEFAULT_PRESIDENTIAL_2026_CSV))
    parser.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--matching-k", type=int, default=5)
    args = parser.parse_args()

    absenteeism_path = Path(args.ausentismo_csv)
    presidential_path = Path(args.presidencial_2026)
    output_dir = Path(args.outdir)
    report_path = Path(args.report)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not absenteeism_path.exists():
        raise SystemExit(f"No existe el consolidado de ausentismo: {absenteeism_path}")
    if not presidential_path.exists():
        raise SystemExit(f"No existe el CSV presidencial 2026: {presidential_path}")

    mesa_rows, absenteeism_audit = read_absenteeism_rows(absenteeism_path)
    grouped = aggregate_by_ubigeo(mesa_rows, terminal_only=True)
    enrich_geography(grouped)
    ubigeo_rows = [ubigeo_to_row(item) for item in sorted(grouped.values(), key=lambda x: (x.anio, x.ubigeo))]
    baselines = build_baselines(grouped)
    flags = build_excess_flags(grouped, baselines)
    geographic = build_geographic_concentration(flags)
    sensitivity = build_sensitivity_summary(flags)
    candidate_votes_by_ubigeo, national_votes, candidate_labels = load_candidate_votes(presidential_path)
    scenarios = build_candidate_scenarios(
        flags,
        grouped,
        baselines,
        candidate_votes_by_ubigeo,
        national_votes,
        candidate_labels,
        max(1, args.matching_k),
    )
    audit_rows = build_audit_checks(
        [absenteeism_path, presidential_path], absenteeism_audit, grouped, output_dir
    )

    counts = {
        "audit_checks.csv": write_csv(output_dir / "audit_checks.csv", audit_rows),
        "absenteeism_by_mesa.csv": write_csv(
            output_dir / "absenteeism_by_mesa.csv", mesa_rows, ABSENTEEISM_FIELDS
        ),
        "absenteeism_by_ubigeo.csv": write_csv(output_dir / "absenteeism_by_ubigeo.csv", ubigeo_rows),
        "baselines_by_ubigeo.csv": write_csv(output_dir / "baselines_by_ubigeo.csv", baselines),
        "excess_absenteeism_flags.csv": write_csv(
            output_dir / "excess_absenteeism_flags.csv", flags
        ),
        "geographic_concentration.csv": write_csv(
            output_dir / "geographic_concentration.csv", geographic
        ),
        "candidate_impact_scenarios.csv": write_csv(
            output_dir / "candidate_impact_scenarios.csv", scenarios
        ),
        "sensitivity_summary.csv": write_csv(output_dir / "sensitivity_summary.csv", sensitivity),
    }
    build_final_report(report_path, audit_rows, grouped, flags, sensitivity, scenarios, output_dir)

    config_path = output_dir / "config_run.yaml"
    write_config_yaml(config_path, BASELINES, args)

    assumptions_path = output_dir / "assumptions.md"
    write_assumptions_md(assumptions_path, run_id)

    end_utc = datetime.now(timezone.utc)
    output_paths = [output_dir / name for name in counts] + [report_path, config_path, assumptions_path]
    manifest_path = output_dir / "manifest_run.json"
    write_manifest_json(
        manifest_path,
        run_id,
        start_utc,
        end_utc,
        [absenteeism_path, presidential_path],
        output_paths,
        counts,
        args,
    )

    print("Analisis de ausentismo presidencial completado.")
    print(f"Run ID: {run_id}")
    print(f"Disclaimer: {DISCLAIMER}")
    for filename, count in counts.items():
        print(f"{filename}: {count} filas")
    print(f"Reporte final preliminar: {report_path}")
    print(f"Manifiesto: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
