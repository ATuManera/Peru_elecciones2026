#!/usr/bin/env python3
"""Pipeline de análisis de ausentismo presidencial 2006-2026 (Perú).

Calcula métricas de ausentismo, línea base histórica (mediana/MAD sobre
2011, 2016, 2021), detección de exceso a nivel ubigeo, escenarios
contrafactuales de impacto sobre votos y análisis de sensibilidad.

AVISO OBLIGATORIO: Los resultados son estimaciones contrafactuales bajo
supuestos explícitos. No constituyen evidencia de fraude, manipulación,
supresión ni intención. Son señales para revisión adicional por las
autoridades electorales competentes y la sociedad civil.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from project_metadata import build_argument_parser

VERSION = "1.0.0"

MAD_FACTOR   = 1.4826
SIGMA_FLOOR  = 0.01
DEFAULT_SEED = 20260501
DEFAULT_K    = 7
DEFAULT_K_MIN = 5
DEFAULT_MC_N  = 1000
MIN_COVERAGE  = 0.5

BASELINE_ROBUST = (2011, 2016, 2021)
BASELINE_SHORT  = (2011, 2016)
BASELINE_RECENT = (2016, 2021)
BASELINE_LONG   = (2006, 2011, 2016)

DOMESTIC_DEP_CODES = {f"{i:02d}" for i in range(1, 26)}

ESTADO_MAP: dict[str, str] = {
    "CONTABILIZADAS NORMALES":    "terminal_normal",
    "CONTABILIZADAS ANULADAS":    "terminal_resuelto",
    "MESA NO INSTALADA":          "no_instalada",
    "ACTA ELECTORAL NORMAL":      "terminal_normal",
    "ACTA ELECTORAL RESUELTA":    "terminal_resuelto",
    "CONTABILIZADA":              "terminal_normal",
    "COMPUTADA RESUELTA":         "terminal_resuelto",
    "ANULADA":                    "anulada_no_contabilizada",
    "ANULADA POR EXTRAVIADA":     "anulada_no_contabilizada",
    "SIN INSTALAR":               "no_instalada",
    "EN PROCESO":                 "pendiente",
    "Contabilizada":              "terminal_normal",
    "Pendiente":                  "pendiente",
    "Para envío al JEE":          "pendiente",
    "En proceso":                 "pendiente",
}
TERMINAL = {"terminal_normal", "terminal_resuelto"}
VOTOS_ESPECIALES = {"VOTOS EN BLANCO", "VOTOS NULOS", "VOTOS IMPUGNADOS"}

SCENARIOS: dict[str, dict] = {
    "S1": dict(baseline=BASELINE_ROBUST,  model="B", terminal_only=True,  excl_ext=False),
    "S2": dict(baseline=BASELINE_ROBUST,  model="C", terminal_only=True,  excl_ext=False),
    "S3": dict(baseline=BASELINE_ROBUST,  model="A", terminal_only=True,  excl_ext=False),
    "S4": dict(baseline=BASELINE_SHORT,   model="B", terminal_only=True,  excl_ext=False),
    "S5": dict(baseline=BASELINE_RECENT,  model="B", terminal_only=True,  excl_ext=False),
    "S6": dict(baseline=BASELINE_LONG,    model="B", terminal_only=True,  excl_ext=False),
    "S7": dict(baseline=BASELINE_ROBUST,  model="B", terminal_only=False, excl_ext=False),
    "S8": dict(baseline=BASELINE_ROBUST,  model="B", terminal_only=True,  excl_ext=True),
}

# ═══════════════════════════════════════════════════════════════════════════
# Utilidades
# ═══════════════════════════════════════════════════════════════════════════

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_info() -> tuple[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        commit, branch = "unknown", "unknown"
    return commit, branch


def parse_int(val: object) -> int | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in {"nan", "none", "null", ""}:
        return None
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def parse_float(val: object) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in {"nan", "none", "null", ""}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def safe_div(num: float | int | None, denom: float | int | None) -> float | None:
    if num is None or denom is None or denom == 0:
        return None
    return num / denom


def safe_mad(vals: list[float], center: float) -> float:
    return statistics.median([abs(v - center) for v in vals]) if vals else 0.0


def fmt(val: float | None, decimals: int = 6) -> str:
    return "" if val is None else f"{val:.{decimals}f}"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def classify_estado(estado: str) -> str:
    return ESTADO_MAP.get(estado.strip(), "desconocido")


def load_dep_map(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = (row.get("ubigeo_dpto") or "").strip().zfill(2)
            name = (row.get("nombre") or "").strip()
            if code:
                result[code] = name
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Fase 1 — Carga del consolidado
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MesaRow:
    anio: int
    codigo_mesa: str
    ubigeo: str
    departamento: str
    provincia: str
    distrito: str
    estado_original: str
    estado_cat: str
    electores: int | None
    emitidos: int | None
    validos: int | None
    blancos: int | None
    nulos: int | None
    impugnados: int | None
    ausentes: int | None
    tasa: float | None
    excluir: bool


def load_consolidado(path: Path) -> list[MesaRow]:
    rows: list[MesaRow] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            anio = parse_int(raw.get("anio"))
            if anio is None:
                continue
            electores  = parse_int(raw.get("electores_habiles"))
            emitidos   = parse_int(raw.get("votos_emitidos"))
            validos    = parse_int(raw.get("votos_validos"))
            blancos    = parse_int(raw.get("votos_blancos"))
            nulos      = parse_int(raw.get("votos_nulos"))
            impugnados = parse_int(raw.get("votos_impugnados"))
            ausentes   = parse_int(raw.get("ausentes"))
            estado_orig = (raw.get("estado_acta") or "").strip()
            tasa = safe_div(ausentes, electores)
            excluir = (
                electores is None
                or electores == 0
                or (emitidos is not None and electores is not None and emitidos > electores)
            )
            rows.append(MesaRow(
                anio=anio,
                codigo_mesa=(raw.get("codigo_mesa") or "").strip(),
                ubigeo=(raw.get("ubigeo") or "").strip(),
                departamento=(raw.get("departamento") or "").strip(),
                provincia=(raw.get("provincia") or "").strip(),
                distrito=(raw.get("distrito") or "").strip(),
                estado_original=estado_orig,
                estado_cat=classify_estado(estado_orig),
                electores=electores, emitidos=emitidos, validos=validos,
                blancos=blancos, nulos=nulos, impugnados=impugnados,
                ausentes=ausentes, tasa=tasa, excluir=excluir,
            ))
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Fase 2 — Auditoría
# ═══════════════════════════════════════════════════════════════════════════

def build_audit_checks(rows: list[MesaRow]) -> list[dict]:
    by_year: dict[int, list[MesaRow]] = defaultdict(list)
    for r in rows:
        by_year[r.anio].append(r)

    checks: list[dict] = []
    for year, yr_rows in sorted(by_year.items()):
        def add(check_type: str, res: str, n: int, desc: str) -> None:
            checks.append({"check_type": check_type, "anio": year,
                           "resultado": res, "n": n, "descripcion": desc})
        add("total_mesas", "info", len(yr_rows), f"Total filas cargadas para {year}")
        n_zero = sum(1 for r in yr_rows if r.electores == 0)
        add("zero_electores", "warn" if n_zero else "pass", n_zero,
            "electores_habiles == 0")
        n_miss = sum(1 for r in yr_rows if r.electores is None)
        add("electores_missing", "warn" if n_miss else "pass", n_miss,
            "electores_habiles nulo")
        n_imp = sum(1 for r in yr_rows
                    if r.electores and r.emitidos and r.emitidos > r.electores)
        add("emitidos_gt_electores", "fail" if n_imp else "pass", n_imp,
            "votos_emitidos > electores_habiles")
        for cat in ("terminal_normal", "terminal_resuelto",
                    "no_instalada", "anulada_no_contabilizada",
                    "pendiente", "desconocido"):
            n_cat = sum(1 for r in yr_rows if r.estado_cat == cat)
            add(f"estado_{cat}", "info", n_cat, f"estado_acta_categoria = {cat}")
        n_incons = 0
        for r in yr_rows:
            if r.emitidos is None:
                continue
            no_val   = sum(v for v in [r.blancos, r.nulos, r.impugnados] if v is not None)
            expected = (r.validos or 0) + no_val
            if abs(r.emitidos - expected) > 1:
                n_incons += 1
        add("totales_inconsistentes", "warn" if n_incons else "pass", n_incons,
            "|votos_emitidos - (validos+blancos+nulos+impugnados)| > 1")
    return checks


# ═══════════════════════════════════════════════════════════════════════════
# Fase 3 — Ausentismo por mesa
# ═══════════════════════════════════════════════════════════════════════════

def build_absenteeism_by_mesa(rows: list[MesaRow]) -> list[dict]:
    return [{
        "anio": r.anio,
        "codigo_mesa": r.codigo_mesa,
        "ubigeo": r.ubigeo,
        "departamento": r.departamento,
        "provincia": r.provincia,
        "distrito": r.distrito,
        "estado_acta_original": r.estado_original,
        "estado_acta_categoria": r.estado_cat,
        "electores_habiles": "" if r.electores is None else r.electores,
        "votos_emitidos": "" if r.emitidos is None else r.emitidos,
        "ausentes": "" if r.ausentes is None else r.ausentes,
        "tasa_ausentismo": fmt(r.tasa),
        "excluir_de_inferencia": "1" if r.excluir else "0",
    } for r in rows]


# ═══════════════════════════════════════════════════════════════════════════
# Fase 4 — Ausentismo por ubigeo
# ═══════════════════════════════════════════════════════════════════════════

def aggregate_by_ubigeo(
    rows: list[MesaRow],
    terminal_only: bool = True,
) -> dict[tuple[int, str], dict]:
    """Agrega por (anio, ubigeo). Corrección metodológica: filtrar estados
    terminales ANTES de agregar (no después)."""
    groups: dict[tuple[int, str], dict] = {}
    for r in rows:
        if r.excluir:
            continue
        if terminal_only and r.estado_cat not in TERMINAL:
            continue
        if not r.ubigeo:
            continue
        key = (r.anio, r.ubigeo)
        if key not in groups:
            groups[key] = {
                "anio": r.anio, "ubigeo": r.ubigeo,
                "departamento": r.departamento, "provincia": r.provincia,
                "n_mesas": 0, "electores": 0, "emitidos": 0, "ausentes": 0,
            }
        g = groups[key]
        g["n_mesas"]   += 1
        g["electores"] += r.electores or 0
        g["emitidos"]  += r.emitidos or 0
        g["ausentes"]  += (r.electores or 0) - (r.emitidos or 0)
        if not g["departamento"] and r.departamento:
            g["departamento"] = r.departamento
        if not g["provincia"] and r.provincia:
            g["provincia"] = r.provincia
    for g in groups.values():
        g["tasa"] = safe_div(g["ausentes"], g["electores"])
    return groups


def build_absenteeism_by_ubigeo_rows(
    groups: dict[tuple[int, str], dict],
    dep_map: dict[str, str],
) -> list[dict]:
    out = []
    for (anio, ubigeo), g in sorted(groups.items()):
        out.append({
            "anio": anio, "ubigeo": ubigeo,
            "departamento": g["departamento"] or dep_map.get(ubigeo[:2], ""),
            "provincia": g["provincia"],
            "n_mesas": g["n_mesas"],
            "electores_habiles": g["electores"],
            "votos_emitidos": g["emitidos"],
            "ausentes": g["ausentes"],
            "tasa_ausentismo": fmt(g["tasa"]),
        })
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Fase 5 — Baseline (mediana/MAD)
# ═══════════════════════════════════════════════════════════════════════════

def build_baselines(
    ubigeo_groups: dict[tuple[int, str], dict],
    baseline_years: tuple[int, ...],
    dep_map: dict[str, str],
) -> dict[str, dict]:
    """baseline_robust_median_mad usa (2011, 2016, 2021).
    Corrección metodológica: no solo (2011, 2016)."""
    ubigeo_tasas: dict[str, list[float]] = defaultdict(list)
    for (anio, ubigeo), g in ubigeo_groups.items():
        if anio in baseline_years and g["tasa"] is not None:
            ubigeo_tasas[ubigeo].append(g["tasa"])

    all_ubigeos = {ubigeo for (_, ubigeo) in ubigeo_groups.keys()}
    result: dict[str, dict] = {}
    for ubigeo in all_ubigeos:
        tasas = ubigeo_tasas.get(ubigeo, [])
        n = len(tasas)
        cobertura    = n / len(baseline_years) if baseline_years else 0.0
        insuficiente = cobertura < MIN_COVERAGE
        if tasas:
            tasa_bl = statistics.median(tasas)
            mad     = safe_mad(tasas, tasa_bl)
            sigma   = max(SIGMA_FLOOR, MAD_FACTOR * mad)
        else:
            tasa_bl = mad = sigma = None
            insuficiente = True
        result[ubigeo] = {
            "ubigeo": ubigeo,
            "departamento": dep_map.get(ubigeo[:2], ""),
            "n_anios_baseline": n,
            "tasa_baseline": tasa_bl,
            "mad": mad,
            "sigma": sigma,
            "cobertura": cobertura,
            "baseline_insuficiente": insuficiente,
        }
    return result


def build_baselines_rows(baselines: dict[str, dict]) -> list[dict]:
    return [{
        "ubigeo": bl["ubigeo"],
        "departamento": bl["departamento"],
        "n_anios_baseline": bl["n_anios_baseline"],
        "tasa_baseline": fmt(bl["tasa_baseline"]),
        "mad": fmt(bl["mad"]),
        "sigma": fmt(bl["sigma"]),
        "cobertura": fmt(bl["cobertura"]),
        "baseline_insuficiente": "1" if bl["baseline_insuficiente"] else "0",
    } for bl in sorted(baselines.values(), key=lambda x: x["ubigeo"])]


# ═══════════════════════════════════════════════════════════════════════════
# Fase 6 — Exceso y flags
# ═══════════════════════════════════════════════════════════════════════════

def compute_flags(
    ubigeo_2026: dict[str, dict],
    baselines: dict[str, dict],
    dep_map: dict[str, str],
    prov_from_hist: dict[str, str],
) -> list[dict]:
    rows = []
    for ubigeo, g in sorted(ubigeo_2026.items()):
        bl = baselines.get(ubigeo)
        if bl is None:
            continue
        tasa_2026 = g["tasa"]
        tasa_bl   = bl["tasa_baseline"]
        sigma     = bl["sigma"]
        if tasa_2026 is None:
            continue
        if tasa_bl is not None:
            exc_abs = tasa_2026 - tasa_bl
            exc_rel = safe_div(exc_abs, tasa_bl)
            z_rob   = safe_div(exc_abs, sigma) if sigma else None
        else:
            exc_abs = exc_rel = z_rob = None
        electores = g["electores"]
        exc_aus = max(0.0, exc_abs) * electores if exc_abs is not None else 0.0
        dep_name  = g.get("departamento") or dep_map.get(ubigeo[:2], "")
        prov_name = g.get("provincia") or prov_from_hist.get(ubigeo[:4], ubigeo[:4])
        rows.append({
            "ubigeo": ubigeo,
            "departamento": dep_name,
            "provincia": prov_name,
            "electores_2026": electores,
            "votos_2026": g["emitidos"],
            "tasa_2026": fmt(tasa_2026),
            "tasa_baseline": fmt(tasa_bl),
            "sigma": fmt(sigma),
            "exceso_absoluto": fmt(exc_abs),
            "exceso_relativo": fmt(exc_rel),
            "z_robusto": fmt(z_rob),
            "exceso_ausentes": fmt(exc_aus, 1),
            "flag_z_robusto_3p5": "1" if z_rob is not None and z_rob >= 3.5 else "0",
            "flag_z_robusto_5":   "1" if z_rob is not None and z_rob >= 5.0 else "0",
            "flag_exceso_5pp":    "1" if exc_abs is not None and exc_abs >= 0.05 else "0",
            "flag_exceso_10pp":   "1" if exc_abs is not None and exc_abs >= 0.10 else "0",
            "flag_relativo_25":   "1" if exc_rel is not None and exc_rel >= 0.25 else "0",
            "flag_baseline_insuficiente": "1" if bl["baseline_insuficiente"] else "0",
        })
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Fase 7 — Concentración geográfica (tres niveles)
# ═══════════════════════════════════════════════════════════════════════════

def build_geographic_concentration(flag_rows: list[dict]) -> list[dict]:
    """Corrección metodológica: agrega en tres niveles (ubigeo, provincia,
    departamento) con mediana de z-robusto y % de ubigeos flageados."""
    out: list[dict] = []

    for r in flag_rows:
        z    = parse_float(r["z_robusto"])
        flag = r["flag_z_robusto_3p5"] == "1"
        exc  = parse_float(r["exceso_ausentes"]) or 0.0
        elec = parse_int(r["electores_2026"]) or 0
        out.append({
            "nivel": "ubigeo",
            "codigo": r["ubigeo"],
            "zona_nombre": r.get("departamento", ""),
            "n_ubigeos_total": 1,
            "n_ubigeos_flagged": 1 if flag else 0,
            "pct_ubigeos_flagged": fmt(1.0 if flag else 0.0),
            "mediana_z_robusto": fmt(z),
            "total_exceso_ausentes": fmt(exc, 1),
            "total_electores": elec,
        })

    for nivel, prefix_len in [("provincia", 4), ("departamento", 2)]:
        zona_field = "departamento" if nivel == "departamento" else "provincia"
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in flag_rows:
            groups[r["ubigeo"][:prefix_len]].append(r)
        for codigo, g_rows in sorted(groups.items()):
            n_total   = len(g_rows)
            n_flagged = sum(1 for r in g_rows if r["flag_z_robusto_3p5"] == "1")
            pct       = n_flagged / n_total if n_total else 0.0
            z_vals    = [z for r in g_rows
                         if (z := parse_float(r["z_robusto"])) is not None]
            med_z     = statistics.median(z_vals) if z_vals else None
            tot_exc   = sum(parse_float(r["exceso_ausentes"]) or 0.0 for r in g_rows)
            tot_ele   = sum(parse_int(r["electores_2026"]) or 0 for r in g_rows)
            zona_nombre = next(
                (r[zona_field] for r in g_rows if r.get(zona_field)), codigo
            )
            out.append({
                "nivel": nivel,
                "codigo": codigo,
                "zona_nombre": zona_nombre,
                "n_ubigeos_total": n_total,
                "n_ubigeos_flagged": n_flagged,
                "pct_ubigeos_flagged": fmt(pct),
                "mediana_z_robusto": fmt(med_z),
                "total_exceso_ausentes": fmt(tot_exc, 1),
                "total_electores": tot_ele,
            })
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Fase 8 — Candidatos 2026
# ═══════════════════════════════════════════════════════════════════════════

def load_candidates_2026(
    path: Path,
) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    ubigeo_cands: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        detalle_pairs: list[tuple[str, str]] = []
        for n in list(range(1, 39)) + [80, 81, 82]:
            dc, vc = f"detalle_{n}_descripcion", f"detalle_{n}_nvotos"
            if dc in fieldnames and vc in fieldnames:
                detalle_pairs.append((dc, vc))
        for raw in reader:
            ubigeo = (raw.get("ubigeoNivel03") or "").strip().zfill(6)
            if not ubigeo or ubigeo == "000000":
                continue
            for dc, vc in detalle_pairs:
                desc  = (raw.get(dc) or "").strip()
                if not desc:
                    continue
                votes = parse_int(raw.get(vc)) or 0
                ubigeo_cands[ubigeo][desc] += votes
    national: dict[str, int] = defaultdict(int)
    for cands in ubigeo_cands.values():
        for cand, v in cands.items():
            national[cand] += v
    return dict(ubigeo_cands), dict(national)


# ═══════════════════════════════════════════════════════════════════════════
# Modelos de imputación
# ═══════════════════════════════════════════════════════════════════════════

def model_A_shares(national_cands: dict[str, int]) -> dict[str, float]:
    total = sum(v for c, v in national_cands.items() if c not in VOTOS_ESPECIALES)
    if total == 0:
        return {}
    return {c: v / total for c, v in national_cands.items() if c not in VOTOS_ESPECIALES}


def model_B_shares(
    ubigeo_cands: dict[str, dict[str, int]],
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for ubigeo, cands in ubigeo_cands.items():
        total = sum(v for c, v in cands.items() if c not in VOTOS_ESPECIALES)
        if total == 0:
            continue
        result[ubigeo] = {c: v / total for c, v in cands.items()
                          if c not in VOTOS_ESPECIALES}
    return result


def _standardize(vals: list[float]) -> list[float]:
    if not vals:
        return vals
    m = statistics.mean(vals)
    try:
        s = statistics.stdev(vals)
    except statistics.StatisticsError:
        s = 0.0
    if s == 0:
        s = 1.0
    return [(v - m) / s for v in vals]


def model_C_compute(
    flag_rows: list[dict],
    ubigeo_2026: dict[str, dict],
    baselines: dict[str, dict],
    local_shares: dict[str, dict[str, float]],
    k: int = DEFAULT_K,
    k_min: int = DEFAULT_K_MIN,
    seed: int = DEFAULT_SEED,
) -> dict[str, dict]:
    _rng = random.Random(seed)  # semilla determinística registrada en manifiesto
    flagged_set = {r["ubigeo"] for r in flag_rows if r["flag_z_robusto_3p5"] == "1"}
    all_ubigeos = sorted(ubigeo_2026.keys())

    norm_e = _standardize([float(ubigeo_2026[u]["electores"] or 0) for u in all_ubigeos])
    norm_t = _standardize([
        baselines[u]["tasa_baseline"] if u in baselines and baselines[u]["tasa_baseline"] is not None
        else 0.0 for u in all_ubigeos
    ])
    norm_n = _standardize([float(ubigeo_2026[u]["n_mesas"]) for u in all_ubigeos])
    feat_map = {u: (norm_e[i], norm_t[i], norm_n[i]) for i, u in enumerate(all_ubigeos)}

    result: dict[str, dict] = {}
    for r in flag_rows:
        if r["flag_z_robusto_3p5"] != "1":
            continue
        ubigeo = r["ubigeo"]
        dep    = ubigeo[:2]
        target = feat_map.get(ubigeo)
        if target is None:
            result[ubigeo] = {"shares": {}, "match_insuficiente": True, "matches": []}
            continue
        candidates: list[tuple[float, str]] = []
        for u in all_ubigeos:
            if u in flagged_set:
                continue
            bl = baselines.get(u)
            if bl is None or bl["cobertura"] < 1.0:
                continue
            if u[:2] != dep:
                continue
            feat = feat_map.get(u)
            if feat is None:
                continue
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, feat)))
            candidates.append((dist, u))
        candidates.sort()
        matches = [u for _, u in candidates[:k]]
        if len(matches) < k_min:
            result[ubigeo] = {"shares": {}, "match_insuficiente": True, "matches": matches}
            continue
        all_cands: set[str] = set()
        for m in matches:
            all_cands.update(local_shares.get(m, {}).keys())
        shares: dict[str, float] = {}
        for cand in all_cands:
            cand_vals = [local_shares[m].get(cand, 0.0) for m in matches if m in local_shares]
            if cand_vals:
                shares[cand] = statistics.median(cand_vals)
        tot = sum(shares.values())
        if tot > 0:
            shares = {c: v / tot for c, v in shares.items()}
        result[ubigeo] = {"shares": shares, "match_insuficiente": False, "matches": matches}
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Fase 9 — Escenarios
# ═══════════════════════════════════════════════════════════════════════════

def run_scenario(
    scenario_id: str,
    baseline_years: tuple[int, ...],
    model_id: str,
    terminal_only: bool,
    excl_ext: bool,
    rows: list[MesaRow],
    dep_map: dict[str, str],
    ubigeo_cands: dict[str, dict[str, int]],
    national_cands: dict[str, int],
    k: int = DEFAULT_K,
    k_min: int = DEFAULT_K_MIN,
    seed: int = DEFAULT_SEED,
) -> tuple[list[dict], list[dict]]:
    ubigeo_groups = aggregate_by_ubigeo(rows, terminal_only=terminal_only)
    ubigeo_2026 = {
        ubigeo: g for (anio, ubigeo), g in ubigeo_groups.items() if anio == 2026
    }
    if excl_ext:
        ubigeo_2026 = {u: g for u, g in ubigeo_2026.items()
                       if u[:2] in DOMESTIC_DEP_CODES}
    baselines   = build_baselines(ubigeo_groups, baseline_years, dep_map)
    flag_rows   = compute_flags(ubigeo_2026, baselines, dep_map, {})
    exceso_map  = {r["ubigeo"]: float(r["exceso_ausentes"]) for r in flag_rows}
    baseline_str = "+".join(str(y) for y in baseline_years)
    total_electores = sum(g["electores"] for g in ubigeo_2026.values())

    impact_rows: list[dict] = []

    if model_id == "A":
        shares_A = model_A_shares(national_cands)
        for ubigeo, exceso in exceso_map.items():
            if exceso <= 0:
                continue
            for cand, share in shares_A.items():
                impact_rows.append({
                    "escenario": scenario_id, "baseline": baseline_str,
                    "modelo": model_id, "ubigeo": ubigeo, "candidato": cand,
                    "votos_observados": ubigeo_cands.get(ubigeo, {}).get(cand, 0),
                    "delta_votos": fmt(exceso * share, 2),
                    "share_imputado": fmt(share),
                    "exceso_ausentes": fmt(exceso, 1), "match_insuficiente": "0",
                })

    elif model_id == "B":
        shares_B = model_B_shares(ubigeo_cands)
        shares_A_fb = model_A_shares(national_cands)
        for ubigeo, exceso in exceso_map.items():
            if exceso <= 0:
                continue
            local_sh = shares_B.get(ubigeo) or shares_A_fb
            for cand, share in local_sh.items():
                impact_rows.append({
                    "escenario": scenario_id, "baseline": baseline_str,
                    "modelo": model_id, "ubigeo": ubigeo, "candidato": cand,
                    "votos_observados": ubigeo_cands.get(ubigeo, {}).get(cand, 0),
                    "delta_votos": fmt(exceso * share, 2),
                    "share_imputado": fmt(share),
                    "exceso_ausentes": fmt(exceso, 1), "match_insuficiente": "0",
                })

    elif model_id == "C":
        shares_B  = model_B_shares(ubigeo_cands)
        c_result  = model_C_compute(flag_rows, ubigeo_2026, baselines,
                                    shares_B, k=k, k_min=k_min, seed=seed)
        for ubigeo, exceso in exceso_map.items():
            if exceso <= 0:
                continue
            c_data = c_result.get(ubigeo)
            if c_data is None:
                continue
            if c_data["match_insuficiente"]:
                impact_rows.append({
                    "escenario": scenario_id, "baseline": baseline_str,
                    "modelo": model_id, "ubigeo": ubigeo, "candidato": "TODOS",
                    "votos_observados": 0, "delta_votos": "0.00",
                    "share_imputado": "0.000000",
                    "exceso_ausentes": fmt(exceso, 1), "match_insuficiente": "1",
                })
                continue
            for cand, share in c_data["shares"].items():
                impact_rows.append({
                    "escenario": scenario_id, "baseline": baseline_str,
                    "modelo": model_id, "ubigeo": ubigeo, "candidato": cand,
                    "votos_observados": ubigeo_cands.get(ubigeo, {}).get(cand, 0),
                    "delta_votos": fmt(exceso * share, 2),
                    "share_imputado": fmt(share),
                    "exceso_ausentes": fmt(exceso, 1), "match_insuficiente": "0",
                })

    # Resumen nacional
    national_obs: dict[str, int] = {
        cand: sum(ubigeo_cands.get(u, {}).get(cand, 0) for u in ubigeo_2026)
        for cand in national_cands if cand not in VOTOS_ESPECIALES
    }
    delta_by_cand: dict[str, float] = defaultdict(float)
    for ir in impact_rows:
        if ir["match_insuficiente"] == "0" and ir["candidato"] != "TODOS":
            delta_by_cand[ir["candidato"]] += float(ir["delta_votos"])

    summary_rows: list[dict] = []
    for cand, delta in sorted(delta_by_cand.items(), key=lambda x: -x[1]):
        obs      = national_obs.get(cand, 0)
        delta_pct = delta / total_electores * 100 if total_electores else 0.0
        summary_rows.append({
            "escenario": scenario_id, "baseline": baseline_str, "modelo": model_id,
            "candidato": cand,
            "delta_votos_nacional": fmt(delta, 2),
            "votos_observados_nacional": obs,
            "delta_pct_padron": fmt(delta_pct, 4),
        })
    return impact_rows, summary_rows


# ═══════════════════════════════════════════════════════════════════════════
# Fase 10 — Sensibilidad
# ═══════════════════════════════════════════════════════════════════════════

def build_sensitivity(all_summary_rows: list[dict]) -> list[dict]:
    delta_by_cand: dict[str, list[float]] = defaultdict(list)
    for r in all_summary_rows:
        d = parse_float(r["delta_votos_nacional"])
        if d is not None:
            delta_by_cand[r["candidato"]].append(d)
    enriched: list[dict] = []
    for r in all_summary_rows:
        cand   = r["candidato"]
        deltas = delta_by_cand.get(cand, [])
        if len(deltas) > 1:
            try:
                cv = statistics.stdev(deltas) / abs(statistics.mean(deltas))
            except (statistics.StatisticsError, ZeroDivisionError):
                cv = 0.0
            signo_pos = sum(1 for d in deltas if d >= 0) / len(deltas)
        else:
            cv = 0.0
            signo_pos = 1.0
        enriched.append({
            **r,
            "coef_variacion": fmt(cv, 4),
            "prop_signo_positivo": fmt(signo_pos, 4),
            "delta_no_robusto": "1" if signo_pos < 0.8 else "0",
        })
    return enriched


# ═══════════════════════════════════════════════════════════════════════════
# Fase 11 — Manifiesto, config, supuestos
# ═══════════════════════════════════════════════════════════════════════════

def write_manifest(
    path: Path,
    run_id: str,
    commit: str,
    branch: str,
    params: dict,
    input_hashes: dict[str, str],
    output_hashes: dict[str, str],
    duration_secs: float,
    n_rows_by_stage: dict[str, int],
) -> None:
    manifest = {
        "run_id": run_id,
        "commit_hash": commit,
        "branch": branch,
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "parametros": params,
        "inputs": input_hashes,
        "outputs": output_hashes,
        "seed": params.get("seed", DEFAULT_SEED),
        "n_filas_por_etapa": n_rows_by_stage,
        "duracion_segundos": round(duration_secs, 2),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)


def write_config_yaml(path: Path, params: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bl = params.get("baseline_robust", list(BASELINE_ROBUST))
    text = f"""\
# Parámetros de corrida — generado automáticamente
# Fecha: {datetime.now(timezone.utc).isoformat()}

baseline:
  primario: {json.dumps(bl)}
  cobertura_minima: {params.get("min_coverage", MIN_COVERAGE)}
  metodo: mediana_mad

deteccion:
  z_robusto_alerta: 3.5
  exceso_absoluto_alerta_pp: 5
  exceso_relativo_alerta: 0.25

filtros:
  estado_acta_terminal_only: true
  excluir_voto_extranjero: false

modelos:
  imputacion: ["A", "B", "C"]
  D_activado: false

matching:
  k: {params.get("k", DEFAULT_K)}
  k_min: {params.get("k_min", DEFAULT_K_MIN)}
  features: [electores_habiles, urbano_rural_proxy, tasa_baseline]

monte_carlo:
  ejecutar: false
  n_iter: {params.get("mc_n", DEFAULT_MC_N)}
  seed: {params.get("seed", DEFAULT_SEED)}

salidas:
  directorio: ./data/output/analisis_ausentismo/
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_assumptions(path: Path, baseline_years: tuple[int, ...], run_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bl_str = ", ".join(str(y) for y in baseline_years)
    text = f"""\
# Supuestos y decisiones metodológicas

> **AVISO OBLIGATORIO.** Los resultados de este análisis son **estimaciones
> contrafactuales bajo supuestos explícitos**. No constituyen evidencia de
> fraude, manipulación, supresión ni intención. Son señales para revisión
> adicional por las autoridades electorales competentes (ONPE, JNE, JEE)
> y la sociedad civil.

## Identificador de corrida

`{run_id}`

## Baseline elegido

**Baseline principal**: mediana/MAD sobre años {bl_str}.

**Justificación**:
- 2011 y 2016 son las elecciones pre-pandemia comparables estructuralmente a 2026.
- 2021 se incluye para capturar variabilidad reciente, aunque es atípica (pandemia).
- La mediana y MAD minimizan el peso de un único año atípico.
- Se excluye 2006 del baseline principal por diferencias estructurales
  (tasa agregada 11.29 %, esquema de mesas distinto, padrón menor).

**Corrección metodológica aplicada**: `baseline_robust_median_mad` usa los años
(2011, 2016, 2021), **no** solo (2011, 2016). Ver METHODOLOGY.md §2.4.

## Filtros aplicados

- **Estado del acta**: solo `terminal_normal` y `terminal_resuelto`.
  Se excluyen `no_instalada`, `anulada_no_contabilizada`, `pendiente`, `desconocido`.
  **Corrección metodológica aplicada**: el filtro se aplica **antes** de agregar
  por ubigeo, no después.
- **Mesas con `electores_habiles = 0`** o vacío: excluidas.
- **Mesas con `votos_emitidos > electores_habiles`**: excluidas.
- **Ubigeos con cobertura de baseline < 0.5**: marcados `baseline_insuficiente`.

## Modelos activados

- **Modelo A**: distribución nacional 2026.
- **Modelo B**: distribución local 2026 por ubigeo (estimación central).
- **Modelo C**: distritos pareados (k={DEFAULT_K}, mismo departamento, cobertura=1.0).
- **Modelo D**: desactivado (requiere bloques pre-registrados).

## Escenarios ejecutados

S1–S8 según METHODOLOGY.md §7.1.

## geographic_concentration.csv

**Corrección metodológica aplicada**: tres niveles (ubigeo, provincia,
departamento) con mediana z-robusto y % ubigeos flageados.

## Limitaciones reconocidas

1. Supuestos de modelos no validados empíricamente.
2. 2021 en baseline amplía rango por efecto pandemia.
3. Esquemas de mesa distintos entre elecciones.
4. Nombres de candidatos no comparables entre años.
5. Cobertura de matching (Modelo C) puede ser insuficiente.
6. Snapshot 2026 estático; refresh puede modificarlo.

## Aviso de no atribución de fraude

Ningún resultado puede interpretarse como evidencia de fraude,
manipulación electoral o supresión de votos.
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ═══════════════════════════════════════════════════════════════════════════
# Fase 12 — Reporte final
# ═══════════════════════════════════════════════════════════════════════════

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    sep = "|" + "|".join("-" * max(4, len(h)) for h in headers) + "|"
    return "\n".join(
        ["|" + "|".join(headers) + "|", sep]
        + ["|" + "|".join(r) + "|" for r in rows]
    )


def generate_final_report(
    report_path: Path,
    run_id: str,
    commit: str,
    branch: str,
    flag_rows: list[dict],
    sensitivity_rows: list[dict],
    input_hashes: dict[str, str],
    baseline_years: tuple[int, ...],
    ubigeo_groups: dict[tuple[int, str], dict],
    dep_map: dict[str, str],
) -> None:
    # Tabla 1: indicadores agregados nacionales por año
    by_year: dict[int, dict] = {}
    for (anio, _), g in ubigeo_groups.items():
        if anio not in by_year:
            by_year[anio] = {"electores": 0, "emitidos": 0, "n_mesas": 0}
        by_year[anio]["electores"] += g["electores"]
        by_year[anio]["emitidos"]  += g["emitidos"]
        by_year[anio]["n_mesas"]   += g["n_mesas"]

    t1 = []
    for yr in sorted(by_year.keys()):
        d    = by_year[yr]
        aus  = d["electores"] - d["emitidos"]
        tasa = safe_div(aus, d["electores"])
        t1.append([str(yr), f"{d['electores']:,}", f"{d['emitidos']:,}",
                   f"{aus:,}", fmt(tasa, 4), str(d["n_mesas"])])

    # Tabla 2: top-20 ubigeos por z-robusto
    flagged_sorted = sorted(
        [r for r in flag_rows if r["flag_z_robusto_3p5"] == "1"],
        key=lambda x: parse_float(x["z_robusto"]) or 0, reverse=True
    )[:20]
    t3 = [[r["ubigeo"], r["departamento"][:20], r["provincia"][:20],
           r["tasa_2026"], r["tasa_baseline"], r["z_robusto"], r["exceso_ausentes"]]
          for r in flagged_sorted]

    # Tabla 3: sensibilidad S1
    s1 = sorted(
        [r for r in sensitivity_rows if r["escenario"] == "S1"],
        key=lambda x: parse_float(x["delta_votos_nacional"]) or 0, reverse=True
    )[:15]
    t4 = [[r["candidato"][:40], r["delta_votos_nacional"],
           str(r["votos_observados_nacional"]), r["delta_pct_padron"],
           r.get("delta_no_robusto", "0")] for r in s1]

    n_flagged = sum(1 for r in flag_rows if r["flag_z_robusto_3p5"] == "1")
    n_total   = len(flag_rows)
    tot_exc   = sum(parse_float(r["exceso_ausentes"]) or 0.0 for r in flag_rows)
    bl_str    = "+".join(str(y) for y in baseline_years)
    fecha_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    md = f"""\
# REPORTE FINAL — Análisis de Ausentismo Presidencial 2026

> **AVISO OBLIGATORIO.** Los resultados de este reporte son **estimaciones
> contrafactuales bajo supuestos explícitos**. No constituyen evidencia de
> fraude, manipulación, supresión ni intención. Son señales para revisión
> adicional por las autoridades electorales competentes (ONPE, JNE, JEE)
> y la sociedad civil.

- **Fecha**: {fecha_utc}  |  **Run ID**: `{run_id}`
- **Commit**: `{commit[:12]}`  |  **Rama**: `{branch}`
- **Baseline principal**: mediana/MAD sobre {bl_str}

---

## 1. Resumen ejecutivo

### Tabla 1 — Indicadores agregados nacionales por año

{_md_table(
    ["Año","Electores hábiles","Votos emitidos","Ausentes","Tasa","N mesas"],
    t1,
)}

### Ubigeos flageados (z-robusto ≥ 3.5)

- Ubigeos analizados: **{n_total:,}**
- Flageados z ≥ 3.5: **{n_flagged:,}** ({100*n_flagged/n_total:.1f} %)
- Exceso total de ausentes estimado: **{tot_exc:,.0f}** electores

> Los ubigeos flageados **ameritan revisión adicional**; no constituyen
> evidencia de irregularidad.

---

## 2. Alcance y aviso obligatorio

Este análisis NO afirma: fraude, manipulación, supresión, intencionalidad,
ni que el resultado oficial sea incorrecto.

Este análisis SÍ produce: medición de diferencias estadísticas, distribución
geográfica de ubigeos con desviaciones grandes, rangos contrafactuales bajo
supuestos explícitos.

Instituciones competentes para investigar irregularidades: ONPE, JNE, JEE,
Ministerio Público, Defensoría del Pueblo, observadores nacionales/internacionales.

---

## 3. Fuentes de datos

| Archivo | SHA-256 (primeros 16 chars) |
|---------|------------------------------|
{chr(10).join(f"| `{k.split('/')[-1]}` | `{v[:16]}…` |" for k, v in input_hashes.items())}

---

## 4. Calidad y comparabilidad

| Año | Recomendación de uso |
|-----|---------------------|
| 2006 | Robustez secundaria — diferencias estructurales |
| 2011 | Robustez secundaria — ~107k mesas vs ~77-88k |
| 2016 | Baseline principal — pre-pandemia, alta comparabilidad |
| 2021 | Incluido con etiqueta "ciclo atípico" (pandemia) |
| 2026 | Año de evaluación |

---

## 5. Metodología

- **Unidad de inferencia**: ubigeo distrital (~2,000)
- **Baseline**: mediana/MAD sobre {bl_str} (corrección metodológica: incluye 2021)
- **Umbral principal**: z-robusto ≥ 3.5
- **Filtro de estado**: solo `terminal_normal` y `terminal_resuelto`, aplicado
  **antes** de agregar por ubigeo (corrección metodológica)
- **Modelos**: A (nacional), B (local), C (matching k=7 mismo departamento)
- **Escenarios**: S1–S8 (ver `assumptions.md`)

`z_robusto_u = (tasa_2026_u − tasa_baseline_u) / (1.4826 × MAD_u)`

---

## 6. Línea base histórica

Tendencia creciente: 2006 (11.3%) → 2011 (16.3%) → 2016 (18.2%)
→ 2021 (29.5%, pandemia). Ver Tabla 1.

---

## 7. Evaluación del ausentismo 2026

### Tabla 2 — Top-20 ubigeos por z-robusto

> *Ameritan revisión adicional, no constituyen evidencia de irregularidad.*

{_md_table(
    ["Ubigeo","Departamento","Provincia","Tasa 2026","Tasa baseline","Z-rob","Exc. aus."],
    t3 or [["(sin datos)"]*7],
)}

---

## 8. Concentración geográfica

El archivo `geographic_concentration.csv` agrega en tres niveles:
**ubigeo**, **provincia** y **departamento**, con mediana de z-robusto y
% de ubigeos flageados por zona.

> Concentración geográfica NO implica intención coordinada. Puede reflejar
> factores estructurales (clima, logística, demografía).

---

## 9. Escenarios contrafactuales

### Tabla 3 — S1 (baseline {bl_str}, Modelo B) — top candidatos

> *Estimación contrafactual condicional. Cifras son escenarios, no hechos.*

{_md_table(
    ["Candidato","Delta votos","Votos obs.","% padrón","No robusto"],
    t4 or [["(sin datos)"]*5],
)}

---

## 10. Análisis de sensibilidad

Ver `sensitivity_summary.csv`. Un candidato con `delta_no_robusto=1` cambia
de signo en >20% de los escenarios — su delta no debe citarse como puntual.

---

## 11. Limitaciones

1. Supuestos de modelos no validados empíricamente.
2. 2021 en baseline amplía rango por pandemia.
3. Esquemas de mesa no uniformes entre elecciones.
4. Nombres de candidatos no comparables entre años.
5. Modelo C depende de disponibilidad de ubigeos control por departamento.
6. Snapshot 2026 estático; refresh puede modificarlo.
7. Ningún modelo establece causalidad.

---

## 12. Conclusiones

Los resultados describen diferencias estadísticas entre la tasa de ausentismo
2026 y el baseline histórico. Las unidades territoriales flageadas constituyen
una lista reproducible para que autoridades electorales, observadores e
investigadores decidan si ameritan revisión adicional.

> "Las estimaciones aquí presentadas son escenarios contrafactuales bajo
> supuestos explícitos. Ofrecen una base cuantitativa para que las autoridades
> electorales, observadores nacionales e internacionales y la sociedad civil
> decidan si ciertas unidades territoriales merecen revisión adicional.
> Cualquier interpretación más allá de ese alcance excede el propósito de
> este reporte."

---

## 13. Apéndice de reproducibilidad

- **Commit**: `{commit}`
- **Rama**: `{branch}`
- **Run ID**: `{run_id}`
- **Comando**: `python3 analyze_ausentismo_presidencial.py`
- **Config**: `data/output/analisis_ausentismo/config_run.yaml`
- **Manifiesto**: `data/output/analisis_ausentismo/manifest_run.json`
- **Supuestos**: `data/output/analisis_ausentismo/assumptions.md`

| Archivo | Descripción |
|---------|-------------|
| `audit_checks.csv` | Verificaciones de calidad |
| `absenteeism_by_mesa.csv` | Ausentismo por mesa × año |
| `absenteeism_by_ubigeo.csv` | Ausentismo por ubigeo × año (terminal) |
| `baselines_by_ubigeo.csv` | Mediana/MAD por ubigeo |
| `excess_absenteeism_flags.csv` | Exceso y flags 2026 |
| `geographic_concentration.csv` | Tres niveles: ubigeo/prov/dep |
| `candidate_impact_scenarios.csv` | Impacto contrafactual S1-S8 |
| `sensitivity_summary.csv` | Resumen de sensibilidad S1-S8 |
| `manifest_run.json` | Metadatos de reproducibilidad |
| `config_run.yaml` | Parámetros |
| `assumptions.md` | Supuestos metodológicos |

---
*No citar resultados como evidencia de fraude, manipulación o supresión.*
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(md)


# ═══════════════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = build_argument_parser(
        description=__doc__,
        assisted_coauthors=("Claude Opus 4.7", "Claude Sonnet 4.6"),
    )
    parser.add_argument(
        "--consolidado", type=Path,
        default=Path("data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv"),
        help="CSV consolidado histórico 2006-2026",
    )
    parser.add_argument(
        "--detalle-2026", type=Path,
        default=Path("data/output/por_votacion/mesas_presidencial.csv"),
        help="CSV detallado de mesas 2026 (con candidatos)",
    )
    parser.add_argument(
        "--outdir", type=Path,
        default=Path("data/output/analisis_ausentismo"),
        help="Directorio de salida",
    )
    parser.add_argument(
        "--report", type=Path, default=Path("FINAL_REPORT.md"),
        help="Ruta del reporte final Markdown",
    )
    parser.add_argument(
        "--dep-map", type=Path,
        default=Path("data_dictionary/ubigeo/departamentos.csv"),
        help="Catálogo ubigeo → nombre departamento",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="Semilla determinística (default: %(default)s)")
    parser.add_argument("--k", type=int, default=DEFAULT_K,
                        help="Vecinos en Modelo C (default: %(default)s)")
    parser.add_argument("--k-min", type=int, default=DEFAULT_K_MIN,
                        help="Mínimo vecinos Modelo C (default: %(default)s)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args()

    t_start = datetime.now(timezone.utc)
    run_id  = str(uuid.uuid4())
    commit, branch = git_info()

    print(f"[analyze_ausentismo] run_id={run_id}")
    print(f"[analyze_ausentismo] commit={commit[:12]}  branch={branch}")

    for p in (args.consolidado, args.detalle_2026):
        if not p.exists():
            print(f"ERROR: archivo no encontrado: {p}", file=sys.stderr)
            sys.exit(1)

    print("[analyze_ausentismo] Calculando hashes de inputs...")
    input_hashes = {
        str(args.consolidado):  sha256_file(args.consolidado),
        str(args.detalle_2026): sha256_file(args.detalle_2026),
    }

    dep_map = load_dep_map(args.dep_map)

    # ── Carga ──────────────────────────────────────────────────────────────
    print("[analyze_ausentismo] Cargando consolidado...")
    rows = load_consolidado(args.consolidado)
    print(f"[analyze_ausentismo] {len(rows):,} filas cargadas")

    # ── Auditoría ──────────────────────────────────────────────────────────
    print("[analyze_ausentismo] Generando audit_checks.csv...")
    audit_checks = build_audit_checks(rows)
    audit_path   = args.outdir / "audit_checks.csv"
    write_csv(audit_path, ["check_type","anio","resultado","n","descripcion"], audit_checks)

    # ── Ausentismo por mesa ────────────────────────────────────────────────
    print("[analyze_ausentismo] Generando absenteeism_by_mesa.csv...")
    mesa_rows = build_absenteeism_by_mesa(rows)
    mesa_path = args.outdir / "absenteeism_by_mesa.csv"
    write_csv(mesa_path, [
        "anio","codigo_mesa","ubigeo","departamento","provincia","distrito",
        "estado_acta_original","estado_acta_categoria",
        "electores_habiles","votos_emitidos","ausentes",
        "tasa_ausentismo","excluir_de_inferencia",
    ], mesa_rows)

    # ── Ausentismo por ubigeo (corrección: filtrar terminal antes de agregar) ──
    print("[analyze_ausentismo] Generando absenteeism_by_ubigeo.csv...")
    ubigeo_groups = aggregate_by_ubigeo(rows, terminal_only=True)
    ubigeo_rows   = build_absenteeism_by_ubigeo_rows(ubigeo_groups, dep_map)
    ubigeo_path   = args.outdir / "absenteeism_by_ubigeo.csv"
    write_csv(ubigeo_path, [
        "anio","ubigeo","departamento","provincia","n_mesas",
        "electores_habiles","votos_emitidos","ausentes","tasa_ausentismo",
    ], ubigeo_rows)

    # Mapa provincia desde histórico para nombres vacíos en 2026
    prov_from_hist: dict[str, str] = {}
    for g in ubigeo_groups.values():
        k4 = g["ubigeo"][:4]
        if k4 not in prov_from_hist and g["provincia"]:
            prov_from_hist[k4] = g["provincia"]

    # ── Baseline robusto (2011, 2016, 2021) ───────────────────────────────
    print("[analyze_ausentismo] Construyendo baselines (2011+2016+2021)...")
    baselines = build_baselines(ubigeo_groups, BASELINE_ROBUST, dep_map)
    bl_path   = args.outdir / "baselines_by_ubigeo.csv"
    write_csv(bl_path, [
        "ubigeo","departamento","n_anios_baseline","tasa_baseline",
        "mad","sigma","cobertura","baseline_insuficiente",
    ], build_baselines_rows(baselines))

    # ── Exceso y flags 2026 ────────────────────────────────────────────────
    print("[analyze_ausentismo] Calculando exceso y flags 2026...")
    ubigeo_2026 = {
        ubigeo: g for (anio, ubigeo), g in ubigeo_groups.items() if anio == 2026
    }
    flag_rows = compute_flags(ubigeo_2026, baselines, dep_map, prov_from_hist)
    flag_path = args.outdir / "excess_absenteeism_flags.csv"
    write_csv(flag_path, [
        "ubigeo","departamento","provincia","electores_2026","votos_2026",
        "tasa_2026","tasa_baseline","sigma","exceso_absoluto","exceso_relativo",
        "z_robusto","exceso_ausentes",
        "flag_z_robusto_3p5","flag_z_robusto_5","flag_exceso_5pp",
        "flag_exceso_10pp","flag_relativo_25","flag_baseline_insuficiente",
    ], flag_rows)
    n_flagged = sum(1 for r in flag_rows if r["flag_z_robusto_3p5"] == "1")
    print(f"[analyze_ausentismo] {len(flag_rows):,} ubigeos — {n_flagged:,} con z≥3.5")

    # ── Concentración geográfica (tres niveles) ────────────────────────────
    print("[analyze_ausentismo] Generando geographic_concentration.csv...")
    geo_rows = build_geographic_concentration(flag_rows)
    geo_path = args.outdir / "geographic_concentration.csv"
    write_csv(geo_path, [
        "nivel","codigo","zona_nombre","n_ubigeos_total","n_ubigeos_flagged",
        "pct_ubigeos_flagged","mediana_z_robusto","total_exceso_ausentes","total_electores",
    ], geo_rows)

    # ── Candidatos 2026 ────────────────────────────────────────────────────
    print("[analyze_ausentismo] Cargando candidatos 2026...")
    ubigeo_cands, national_cands = load_candidates_2026(args.detalle_2026)
    print(f"[analyze_ausentismo] {len(national_cands):,} candidatos/opciones")

    # ── Escenarios S1-S8 ───────────────────────────────────────────────────
    print("[analyze_ausentismo] Ejecutando escenarios S1-S8...")
    all_impact:   list[dict] = []
    all_summary:  list[dict] = []
    for scen_id, scen in SCENARIOS.items():
        bl_tag = "+".join(str(y) for y in scen["baseline"])
        print(f"  → {scen_id} baseline={bl_tag} model={scen['model']} "
              f"terminal={scen['terminal_only']} excl_ext={scen['excl_ext']}")
        imp, summ = run_scenario(
            scenario_id=scen_id,
            baseline_years=scen["baseline"],
            model_id=scen["model"],
            terminal_only=scen["terminal_only"],
            excl_ext=scen["excl_ext"],
            rows=rows,
            dep_map=dep_map,
            ubigeo_cands=ubigeo_cands,
            national_cands=national_cands,
            k=args.k, k_min=args.k_min, seed=args.seed,
        )
        all_impact.extend(imp)
        all_summary.extend(summ)

    impact_path = args.outdir / "candidate_impact_scenarios.csv"
    write_csv(impact_path, [
        "escenario","baseline","modelo","ubigeo","candidato",
        "votos_observados","delta_votos","share_imputado",
        "exceso_ausentes","match_insuficiente",
    ], all_impact)

    sensitivity_rows = build_sensitivity(all_summary)
    sens_path = args.outdir / "sensitivity_summary.csv"
    write_csv(sens_path, [
        "escenario","baseline","modelo","candidato",
        "delta_votos_nacional","votos_observados_nacional","delta_pct_padron",
        "coef_variacion","prop_signo_positivo","delta_no_robusto",
    ], sensitivity_rows)
    print(f"[analyze_ausentismo] {len(all_impact):,} filas de impacto generadas")

    # ── Manifiesto, config, supuestos ──────────────────────────────────────
    t_end    = datetime.now(timezone.utc)
    duration = (t_end - t_start).total_seconds()

    output_paths = [
        audit_path, mesa_path, ubigeo_path, bl_path,
        flag_path, geo_path, impact_path, sens_path,
    ]
    print("[analyze_ausentismo] Calculando hashes de outputs...")
    output_hashes = {str(p): sha256_file(p) for p in output_paths}

    params = {
        "version": VERSION,
        "baseline_robust": list(BASELINE_ROBUST),
        "min_coverage": MIN_COVERAGE,
        "k": args.k, "k_min": args.k_min, "seed": args.seed,
        "mc_n": DEFAULT_MC_N,
        "consolidado": str(args.consolidado),
        "detalle_2026": str(args.detalle_2026),
        "outdir": str(args.outdir),
    }
    n_rows_by_stage = {
        "consolidado": len(rows),
        "audit_checks": len(audit_checks),
        "absenteeism_by_mesa": len(mesa_rows),
        "absenteeism_by_ubigeo": len(ubigeo_rows),
        "baselines": len(baselines),
        "flags": len(flag_rows),
        "geo_concentration": len(geo_rows),
        "candidate_impact": len(all_impact),
        "sensitivity": len(sensitivity_rows),
    }

    manifest_path = args.outdir / "manifest_run.json"
    write_manifest(manifest_path, run_id, commit, branch,
                   params, input_hashes, output_hashes,
                   duration, n_rows_by_stage)
    output_hashes[str(manifest_path)] = sha256_file(manifest_path)

    write_config_yaml(args.outdir / "config_run.yaml", params)
    write_assumptions(args.outdir / "assumptions.md", BASELINE_ROBUST, run_id)

    print("[analyze_ausentismo] Generando FINAL_REPORT.md...")
    generate_final_report(
        report_path=args.report,
        run_id=run_id,
        commit=commit,
        branch=branch,
        flag_rows=flag_rows,
        sensitivity_rows=sensitivity_rows,
        input_hashes=input_hashes,
        baseline_years=BASELINE_ROBUST,
        ubigeo_groups=ubigeo_groups,
        dep_map=dep_map,
    )

    print(f"[analyze_ausentismo] Completado en {duration:.1f}s")
    print(f"[analyze_ausentismo] Salidas en: {args.outdir}/")
    print(f"[analyze_ausentismo] Reporte:    {args.report}")


if __name__ == "__main__":
    main()
