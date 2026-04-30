#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria de cobertura y linea de tiempo de mesas presidenciales ONPE.

El punto metodologico central es separar universos:

1. Universo electoral presidencial: mesa_presidencial_control.
2. Universo operacional con detalle descargado: mesas.status = DETAIL_OK.
3. Universo disponible en el CSV presidencial: mesas_presidencial.csv.
4. Universo auditable por timeline: filas del CSV con eventos de linea de tiempo.

Una mesa en estado operacional no final, como "Para envio al JEE" o "Pendiente",
se reporta como cobertura no comparable salvo que exista una linea de tiempo que
permita evaluar un flujo temporal concreto.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from project_metadata import build_argument_parser

np = None
pd = None
plt = None


def load_audit_dependencies() -> None:
    global np, pd
    if np is not None and pd is not None:
        return
    try:
        import numpy as numpy
        import pandas as pandas
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Faltan dependencias opcionales para auditoría. "
            "Instala con: python3 -m pip install -e '.[audit]'"
        ) from exc
    np = numpy
    pd = pandas


def get_pyplot():
    global plt
    if plt is not None:
        return plt
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as pyplot
    except Exception:  # pragma: no cover
        return None
    plt = pyplot
    return plt

PHASE_DIGITALIZACION = "Digitalizacion"
PHASE_DIGITACION = "Digitacion"
PHASE_CONTABILIZADA = "Contabilizada"
PHASE_JEE = "Para envio al JEE"
PHASE_OBSERVADA = "Observada"
PHASE_RECIBIDA_JEE = "Recibida del JEE"
PHASE_RES_ONPE = "Resolucion de la ONPE"


def pct(n: float, d: float) -> float:
    return float(n) / float(d) * 100 if d else 0.0


def norm_text(x: object) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def norm_code(x: object) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(6) if s.isdigit() and len(s) < 6 else s


def canonical_status(x: object) -> str:
    s = norm_text(x)
    low = s.lower()
    if "para" in low and "env" in low and "jee" in low:
        return "Para envio al JEE"
    if "contabil" in low:
        return PHASE_CONTABILIZADA
    if "pendiente" in low:
        return "Pendiente"
    return s


def canonical_phase(desc: object) -> str:
    s = norm_text(desc).lower()
    if not s:
        return ""
    if "digitaliz" in s:
        return PHASE_DIGITALIZACION
    if "digitaci" in s:
        return PHASE_DIGITACION
    if "contabil" in s:
        return PHASE_CONTABILIZADA
    if "env" in s and "jee" in s:
        return PHASE_JEE
    if "observ" in s:
        return PHASE_OBSERVADA
    if "recib" in s and "jee" in s:
        return PHASE_RECIBIDA_JEE
    if "resol" in s and "onpe" in s:
        return PHASE_RES_ONPE
    return norm_text(desc)


def discover_timeline_indexes(columns: Iterable[str]) -> List[int]:
    idxs = set()
    pat = re.compile(r"^lineaTiempo_(\d+)_")
    for c in columns:
        m = pat.match(c)
        if m:
            idxs.add(int(m.group(1)))
    return sorted(idxs)


def sqlite_uri(path: Path) -> str:
    return f"file:{path.resolve()}?mode=ro"


def load_sqlite_tables(sqlite_path: Optional[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if sqlite_path is None or not sqlite_path.exists():
        empty_control = pd.DataFrame(
            columns=["codigo_mesa", "estado_control", "codigo_estado_acta", "json_path"]
        )
        empty_mesas = pd.DataFrame(columns=["codigo_mesa", "status", "json_path", "detail_url"])
        return empty_control, empty_mesas

    conn = sqlite3.connect(sqlite_uri(sqlite_path), uri=True)
    try:
        control = pd.read_sql_query(
            """
            select codigo_mesa, codigo_estado_acta, estado_control,
                   total_votos_validos, total_votos_emitidos,
                   total_electores_habiles, json_path
            from mesa_presidencial_control
            """,
            conn,
            dtype={"codigo_mesa": "string"},
        )
        mesas = pd.read_sql_query(
            """
            select codigo_mesa, status, json_path, detail_url,
                   http_status_search, http_status_detail, ultimo_error
            from mesas
            """,
            conn,
            dtype={"codigo_mesa": "string"},
        )
    finally:
        conn.close()

    control["codigo_mesa_key"] = control["codigo_mesa"].map(norm_code)
    control["estado_control_norm"] = control["estado_control"].map(canonical_status)
    mesas["codigo_mesa_key"] = mesas["codigo_mesa"].map(norm_code)
    mesas["status_norm"] = mesas["status"].map(canonical_status)
    return control, mesas


def parse_events(df: pd.DataFrame, timeline_indexes: List[int]) -> pd.DataFrame:
    pieces = []
    for i in timeline_indexes:
        desc_col = f"lineaTiempo_{i}_descripcionEstadoActa"
        res_col = f"lineaTiempo_{i}_descripcionEstadoActaResolucion"
        code_col = f"lineaTiempo_{i}_codigoEstadoActa"
        date_col = f"lineaTiempo_{i}_fechaRegistro"
        if date_col not in df.columns:
            continue
        tmp = pd.DataFrame(
            {
                "row_id": df.index,
                "event_n": i,
                "codigo_mesa": df["codigo_mesa_key"],
                "codigoEstadoActa_evento": df.get(
                    code_col, pd.Series(index=df.index, dtype="object")
                ),
                "descripcion_evento_raw": df.get(
                    desc_col, pd.Series(index=df.index, dtype="object")
                ),
                "descripcion_resolucion_raw": df.get(
                    res_col, pd.Series(index=df.index, dtype="object")
                ),
                "fechaRegistro_raw": df.get(date_col, pd.Series(index=df.index, dtype="object")),
            }
        )
        tmp = tmp[tmp["fechaRegistro_raw"].notna() | tmp["descripcion_evento_raw"].notna()]
        if len(tmp):
            pieces.append(tmp)
    if not pieces:
        return pd.DataFrame(
            columns=[
                "row_id",
                "event_n",
                "codigo_mesa",
                "phase",
                "fechaRegistro",
                "descripcion_evento_raw",
            ]
        )
    ev = pd.concat(pieces, ignore_index=True)
    ev["phase"] = ev["descripcion_evento_raw"].map(canonical_phase)
    ev["fechaRegistro"] = pd.to_datetime(ev["fechaRegistro_raw"], errors="coerce", utc=True)
    ev = ev[ev["phase"].ne("") | ev["fechaRegistro"].notna()].copy()
    ev.sort_values(["row_id", "event_n"], inplace=True)
    return ev


def first_phase_times(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["row_id"])
    ev = events.dropna(subset=["fechaRegistro"]).copy()
    if ev.empty:
        return pd.DataFrame(columns=["row_id"])
    phase_first = (
        ev.sort_values(["row_id", "fechaRegistro", "event_n"])
        .groupby(["row_id", "phase"], as_index=False)
        .agg(fecha=("fechaRegistro", "first"), event_n=("event_n", "first"))
    )
    wide = phase_first.pivot(index="row_id", columns="phase", values="fecha")
    wide.columns = [f"ts_{c}" for c in wide.columns]
    wide_n = phase_first.pivot(index="row_id", columns="phase", values="event_n")
    wide_n.columns = [f"event_n_{c}" for c in wide_n.columns]
    return pd.concat([wide, wide_n], axis=1).reset_index()


def add_duration_hours(df: pd.DataFrame, start_phase: str, end_phase: str, out_col: str) -> None:
    a = f"ts_{start_phase}"
    b = f"ts_{end_phase}"
    if a in df.columns and b in df.columns:
        df[out_col] = (df[b] - df[a]).dt.total_seconds() / 3600.0
    else:
        df[out_col] = np.nan


def describe_numeric(s: pd.Series) -> Dict[str, float]:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if x.empty:
        return {
            "n": 0,
            "mean": np.nan,
            "median": np.nan,
            "p90": np.nan,
            "p95": np.nan,
            "p99": np.nan,
            "min": np.nan,
            "max": np.nan,
        }
    return {
        "n": int(x.count()),
        "mean": float(x.mean()),
        "median": float(x.median()),
        "p90": float(x.quantile(0.90)),
        "p95": float(x.quantile(0.95)),
        "p99": float(x.quantile(0.99)),
        "min": float(x.min()),
        "max": float(x.max()),
    }


def save_histogram(
    series: pd.Series, title: str, xlabel: str, path: Path, bins: int = 60, max_percentile: float = 0.99
) -> None:
    plt = get_pyplot()
    if plt is None:
        return
    x = pd.to_numeric(series, errors="coerce").dropna()
    x = x[np.isfinite(x)]
    if x.empty:
        return
    upper = x.quantile(max_percentile)
    x_plot = x[x <= upper] if upper > 0 else x
    fig = plt.figure(figsize=(10, 6))
    plt.hist(x_plot, bins=bins)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Cantidad de mesas")
    plt.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    path: Path,
    top_n: int = 30,
) -> None:
    plt = get_pyplot()
    if plt is None or df.empty:
        return
    d = df.sort_values(y_col, ascending=False).head(top_n).copy()
    if d.empty:
        return
    fig = plt.figure(figsize=(12, max(6, len(d) * 0.25)))
    plt.barh(d[x_col].astype(str), d[y_col])
    plt.gca().invert_yaxis()
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def coverage_row(capa: str, categoria: str, mesas: int, denom: int, nota: str = "") -> dict:
    return {
        "capa": capa,
        "categoria": categoria,
        "mesas": int(mesas),
        "porcentaje_sobre_capa": pct(mesas, denom),
        "denominador_capa": int(denom),
        "nota": nota,
    }


def bool_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    return df[col].fillna(False).astype(bool)


def main() -> int:
    ap = build_argument_parser(description="Auditoria de cobertura y timeline presidencial ONPE")
    ap.add_argument(
        "--input",
        default="data/output/por_votacion/mesas_presidencial.csv",
        help="Ruta del CSV presidencial",
    )
    ap.add_argument(
        "--sqlite",
        default="data/state/onpe_scraper.sqlite",
        help="SQLite con tablas mesas y mesa_presidencial_control",
    )
    ap.add_argument("--outdir", default="data/output/auditoria_timeline", help="Carpeta de salida")
    ap.add_argument(
        "--special-threshold",
        type=int,
        default=900001,
        help="Umbral para serie especial; default 900001",
    )
    ap.add_argument("--top-districts", type=int, default=40)
    ap.add_argument("--outlier-pct", type=float, default=0.99)
    ap.add_argument("--charts", action="store_true", help="Generar graficos PNG opcionales")
    ap.add_argument("--no-charts", action="store_true", help="No generar graficos PNG")
    args = ap.parse_args()
    load_audit_dependencies()

    input_path = Path(args.input)
    sqlite_path = Path(args.sqlite) if args.sqlite else None
    outdir = Path(args.outdir)
    charts_dir = outdir / "charts"
    outdir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path, dtype=str, low_memory=False)
    df.insert(0, "row_id", df.index)
    if "codigoMesa" not in df.columns:
        raise SystemExit("ERROR: No existe la columna codigoMesa en el CSV.")

    df["codigo_mesa_key"] = df["codigoMesa"].map(norm_code)
    df["codigoMesa_num"] = pd.to_numeric(df["codigo_mesa_key"], errors="coerce")
    df["serie_especial_900001_mas"] = df["codigoMesa_num"] >= args.special_threshold
    df["estado_csv_norm"] = df.get("descripcionEstadoActa", "").map(canonical_status)

    control, mesas_sql = load_sqlite_tables(sqlite_path)
    control_keys = set(control["codigo_mesa_key"]) if not control.empty else set()
    detail_ok = mesas_sql[mesas_sql["status"].eq("DETAIL_OK")].copy()
    detail_ok_keys = set(detail_ok["codigo_mesa_key"]) if not detail_ok.empty else set()
    csv_keys = set(df["codigo_mesa_key"])

    timeline_indexes = discover_timeline_indexes(df.columns)
    events = parse_events(df, timeline_indexes)
    events.to_csv(outdir / "eventos_linea_tiempo_long.csv", index=False)

    phase_wide = first_phase_times(events)
    event_counts = (
        events.groupby("row_id")
        .agg(eventos_timeline=("event_n", "count"), eventos_con_fecha=("fechaRegistro", "count"))
        .reset_index()
    )

    geo_cols = [
        c
        for c in [
            "ubigeoNivel01",
            "ubigeoNivel02",
            "ubigeoNivel03",
            "centroPoblado",
            "nombreLocalVotacion",
        ]
        if c in df.columns
    ]
    base_cols = [
        "row_id",
        "codigoMesa",
        "codigo_mesa_key",
        "codigoMesa_num",
        "serie_especial_900001_mas",
    ] + geo_cols
    base_cols += [
        c
        for c in [
            "estadoActa",
            "estadoComputo",
            "codigoEstadoActa",
            "descripcionEstadoActa",
            "descripcionSubEstadoActa",
        ]
        if c in df.columns
    ]
    mesas = df[base_cols].merge(event_counts, on="row_id", how="left")
    mesas = mesas.merge(phase_wide, on="row_id", how="left")
    mesas["eventos_timeline"] = mesas["eventos_timeline"].fillna(0).astype(int)
    mesas["eventos_con_fecha"] = mesas["eventos_con_fecha"].fillna(0).astype(int)
    mesas["tiene_timeline"] = mesas["eventos_timeline"] > 0

    for phase in [
        PHASE_DIGITALIZACION,
        PHASE_DIGITACION,
        PHASE_CONTABILIZADA,
        PHASE_JEE,
        PHASE_OBSERVADA,
        PHASE_RECIBIDA_JEE,
        PHASE_RES_ONPE,
    ]:
        mesas[f"has_{phase}"] = f"ts_{phase}" in mesas.columns and mesas.get(f"ts_{phase}").notna()

    add_duration_hours(mesas, PHASE_DIGITALIZACION, PHASE_DIGITACION, "h_digitalizacion_a_digitacion")
    add_duration_hours(mesas, PHASE_DIGITACION, PHASE_CONTABILIZADA, "h_digitacion_a_contabilizada")
    add_duration_hours(mesas, PHASE_DIGITACION, PHASE_JEE, "h_digitacion_a_envio_jee")
    add_duration_hours(
        mesas, PHASE_DIGITALIZACION, PHASE_CONTABILIZADA, "h_digitalizacion_a_contabilizada"
    )
    add_duration_hours(mesas, PHASE_DIGITALIZACION, PHASE_JEE, "h_digitalizacion_a_envio_jee")

    has_dig = bool_col(mesas, f"has_{PHASE_DIGITALIZACION}")
    has_digit = bool_col(mesas, f"has_{PHASE_DIGITACION}")
    has_cont = bool_col(mesas, f"has_{PHASE_CONTABILIZADA}")
    has_jee = bool_col(mesas, f"has_{PHASE_JEE}")
    has_timeline = bool_col(mesas, "tiene_timeline")

    mesas["flujo_clasificado"] = np.select(
        [
            ~has_timeline,
            has_dig & has_digit & has_cont,
            has_dig & has_digit & has_jee & ~has_cont,
            has_timeline & ~has_dig & has_digit & has_cont,
            has_timeline & ~has_dig & has_digit & has_jee,
            has_dig & ~has_digit & has_cont,
            has_dig & ~has_digit & has_jee,
            has_timeline & ~has_dig,
        ],
        [
            "Sin timeline",
            "Digitalizacion -> Digitacion -> Contabilizada",
            "Digitalizacion -> Digitacion -> Para envio al JEE",
            "SIN Digitalizacion -> Digitacion -> Contabilizada",
            "SIN Digitalizacion -> Digitacion -> Para envio al JEE",
            "Digitalizacion -> SIN Digitacion -> Contabilizada",
            "Digitalizacion -> SIN Digitacion -> Para envio al JEE",
            "Timeline existente SIN Digitalizacion",
        ],
        default="Otro / incompleto con timeline",
    )

    mesas["anomalia_sin_digitalizacion_con_timeline"] = has_timeline & ~has_dig
    mesas["anomalia_sin_digitacion_con_final"] = has_timeline & ~has_digit & (has_cont | has_jee)
    mesas["anomalia_digitacion_antes_digitalizacion"] = mesas["h_digitalizacion_a_digitacion"] < 0
    mesas["anomalia_contabilizada_antes_digitacion"] = mesas["h_digitacion_a_contabilizada"] < 0
    mesas["anomalia_jee_antes_digitacion"] = mesas["h_digitacion_a_envio_jee"] < 0

    duration_cols = [
        "h_digitalizacion_a_digitacion",
        "h_digitacion_a_contabilizada",
        "h_digitacion_a_envio_jee",
        "h_digitalizacion_a_contabilizada",
        "h_digitalizacion_a_envio_jee",
    ]
    outlier_thresholds = {}
    for c in duration_cols:
        x = pd.to_numeric(mesas[c], errors="coerce")
        x_pos = x[x >= 0].dropna()
        thr = float(x_pos.quantile(args.outlier_pct)) if len(x_pos) else np.nan
        outlier_thresholds[c] = thr
        mesas[f"outlier_{c}"] = x.notna() & (x >= 0) & (x > thr) if not math.isnan(thr) else False

    anomaly_cols = [c for c in mesas.columns if c.startswith("anomalia_") or c.startswith("outlier_")]
    mesas["n_flags_anomalia"] = mesas[anomaly_cols].sum(axis=1)
    mesas["tiene_alguna_anomalia"] = mesas["n_flags_anomalia"] > 0

    priority_conditions = [
        mesas["anomalia_contabilizada_antes_digitacion"],
        mesas["anomalia_digitacion_antes_digitalizacion"],
        mesas["anomalia_jee_antes_digitacion"],
        mesas["serie_especial_900001_mas"] & mesas["anomalia_sin_digitalizacion_con_timeline"],
        mesas["anomalia_sin_digitalizacion_con_timeline"],
        mesas["anomalia_sin_digitacion_con_final"],
        mesas[[c for c in anomaly_cols if c.startswith("outlier_")]].any(axis=1),
    ]
    priority_labels = [
        "Alta: contabilizacion antes de digitacion",
        "Alta: digitacion antes de digitalizacion",
        "Alta: envio JEE antes de digitacion",
        "Media-alta: serie 900001+ sin digitalizacion con timeline",
        "Media: sin digitalizacion con timeline",
        "Media: final sin digitacion con timeline",
        "Baja: outlier de duracion positiva",
    ]
    mesas["prioridad_revision"] = np.select(priority_conditions, priority_labels, default="")

    total_csv = len(mesas)
    total_control = len(control)
    total_detail_ok = len(detail_ok)

    cobertura_rows = []
    if not control.empty:
        for estado, n in (
            control.groupby("estado_control_norm", dropna=False).size().sort_values(ascending=False).items()
        ):
            cobertura_rows.append(
                coverage_row(
                    "01_universo_presidencial_control",
                    estado or "Sin estado",
                    n,
                    total_control,
                    "Fuente: mesa_presidencial_control",
                )
            )
    cobertura_rows.extend(
        [
            coverage_row(
                "02_universo_detail_ok",
                "DETAIL_OK",
                total_detail_ok,
                total_detail_ok,
                "Fuente: mesas.status = DETAIL_OK",
            ),
            coverage_row(
                "03_universo_csv_presidencial",
                "Filas CSV",
                total_csv,
                total_csv,
                "Fuente: mesas_presidencial.csv",
            ),
            coverage_row(
                "04_universo_auditable_timeline",
                "CSV con timeline",
                int(has_timeline.sum()),
                total_csv,
                "Subconjunto donde aplica analisis temporal",
            ),
            coverage_row(
                "04_universo_auditable_timeline",
                "CSV sin timeline",
                int((~has_timeline).sum()),
                total_csv,
                "No comparable para orden temporal",
            ),
        ]
    )
    cobertura_universo = pd.DataFrame(cobertura_rows)

    csv_vs_sqlite = pd.DataFrame(
        [
            {"metrica": "mesas_csv_presidencial", "valor": total_csv},
            {"metrica": "mesas_control_presidencial", "valor": total_control},
            {"metrica": "mesas_status_DETAIL_OK", "valor": total_detail_ok},
            {"metrica": "csv_en_control", "valor": len(csv_keys & control_keys)},
            {"metrica": "control_fuera_csv", "valor": len(control_keys - csv_keys)},
            {"metrica": "csv_fuera_control", "valor": len(csv_keys - control_keys)},
            {"metrica": "csv_en_DETAIL_OK", "valor": len(csv_keys & detail_ok_keys)},
            {"metrica": "DETAIL_OK_fuera_csv", "valor": len(detail_ok_keys - csv_keys)},
            {"metrica": "csv_fuera_DETAIL_OK", "valor": len(csv_keys - detail_ok_keys)},
            {
                "metrica": "mesas_fuera_csv_no_DETAIL_OK_ni_NOT_FOUND",
                "valor": int(
                    len(
                        mesas_sql[
                            ~mesas_sql["codigo_mesa_key"].isin(csv_keys)
                            & ~mesas_sql["status"].isin(["DETAIL_OK", "NOT_FOUND"])
                        ]
                    )
                )
                if not mesas_sql.empty
                else 0,
            },
        ]
    )

    if not mesas_sql.empty:
        mesas_fuera_csv = mesas_sql[~mesas_sql["codigo_mesa_key"].isin(csv_keys)].copy()
        mesas_fuera_csv_por_estado = (
            mesas_fuera_csv.groupby("status_norm", dropna=False)
            .size()
            .reset_index(name="mesas_fuera_csv")
            .rename(columns={"status_norm": "estado_operacional_sqlite"})
            .sort_values("mesas_fuera_csv", ascending=False)
        )
    else:
        mesas_fuera_csv = pd.DataFrame()
        mesas_fuera_csv_por_estado = pd.DataFrame(
            columns=["estado_operacional_sqlite", "mesas_fuera_csv"]
        )

    control_fuera_csv = (
        control[~control["codigo_mesa_key"].isin(csv_keys)].copy()
        if not control.empty
        else pd.DataFrame()
    )
    if not control_fuera_csv.empty:
        control_extra = (
            control_fuera_csv.groupby("estado_control_norm", dropna=False)
            .size()
            .reset_index(name="mesas_control_fuera_csv")
            .rename(columns={"estado_control_norm": "estado_control_presidencial"})
            .sort_values("mesas_control_fuera_csv", ascending=False)
        )
        mesas_fuera_csv_por_estado = mesas_fuera_csv_por_estado.merge(
            control_extra,
            left_on="estado_operacional_sqlite",
            right_on="estado_control_presidencial",
            how="outer",
        )

    resumen_flujos = (
        mesas[mesas["tiene_timeline"]]
        .groupby("flujo_clasificado", dropna=False)
        .size()
        .reset_index(name="mesas")
        .assign(porcentaje_sobre_timeline=lambda d: d["mesas"].map(lambda n: pct(n, has_timeline.sum())))
        .sort_values("mesas", ascending=False)
    )

    sin_digitalizacion_con_timeline = mesas[mesas["anomalia_sin_digitalizacion_con_timeline"]].copy()

    no_comparables = []
    csv_sin_timeline = mesas[~mesas["tiene_timeline"]].copy()
    if not csv_sin_timeline.empty:
        tmp = csv_sin_timeline[
            ["codigo_mesa_key", "codigoMesa", "descripcionEstadoActa", "flujo_clasificado"]
            + geo_cols
        ].copy()
        tmp["fuente"] = "CSV presidencial"
        tmp["razon_no_comparable"] = "Fila CSV sin eventos de linea de tiempo"
        no_comparables.append(tmp)
    if not control_fuera_csv.empty:
        tmp = control_fuera_csv[
            ["codigo_mesa_key", "codigo_mesa", "estado_control", "codigo_estado_acta", "json_path"]
        ].copy()
        tmp["fuente"] = "mesa_presidencial_control"
        tmp["razon_no_comparable"] = "Presente en control presidencial pero fuera del CSV"
        no_comparables.append(tmp)
    if not mesas_fuera_csv.empty:
        tmp = mesas_fuera_csv[
            ["codigo_mesa_key", "codigo_mesa", "status", "status_norm", "json_path", "detail_url"]
        ].copy()
        tmp = tmp[tmp["status_norm"].isin(["Para envio al JEE", "Pendiente"])]
        if not tmp.empty:
            tmp["fuente"] = "mesas"
            tmp["razon_no_comparable"] = "Estado operacional no final fuera del CSV"
            no_comparables.append(tmp)
    sin_timeline_o_no_comparables = (
        pd.concat(no_comparables, ignore_index=True, sort=False)
        if no_comparables
        else pd.DataFrame(columns=["codigo_mesa_key", "fuente", "razon_no_comparable"])
    )

    serie_analisis = (
        mesas.groupby("serie_especial_900001_mas", dropna=False)
        .agg(
            mesas_csv=("codigoMesa", "count"),
            con_timeline=("tiene_timeline", "sum"),
            sin_timeline=("tiene_timeline", lambda s: int((~s).sum())),
            sin_digitalizacion_con_timeline=("anomalia_sin_digitalizacion_con_timeline", "sum"),
            con_digitalizacion=(f"has_{PHASE_DIGITALIZACION}", "sum"),
            con_digitacion=(f"has_{PHASE_DIGITACION}", "sum"),
            contabilizadas=(f"has_{PHASE_CONTABILIZADA}", "sum"),
            envio_jee=(f"has_{PHASE_JEE}", "sum"),
            alguna_anomalia=("tiene_alguna_anomalia", "sum"),
        )
        .reset_index()
    )
    for c in [
        "con_timeline",
        "sin_timeline",
        "sin_digitalizacion_con_timeline",
        "con_digitalizacion",
        "con_digitacion",
        "contabilizadas",
        "envio_jee",
        "alguna_anomalia",
    ]:
        serie_analisis[f"pct_{c}"] = serie_analisis.apply(lambda r: pct(r[c], r["mesas_csv"]), axis=1)

    dur_rows = []
    for c in duration_cols:
        d = describe_numeric(mesas.loc[mesas["tiene_timeline"], c])
        d["metrica"] = c
        d["outlier_threshold_horas"] = outlier_thresholds[c]
        dur_rows.append(d)
    resumen_duraciones = pd.DataFrame(dur_rows)[
        ["metrica", "n", "mean", "median", "p90", "p95", "p99", "min", "max", "outlier_threshold_horas"]
    ]

    distrito_col = "ubigeoNivel03" if "ubigeoNivel03" in mesas.columns else (geo_cols[-1] if geo_cols else None)
    if distrito_col:
        resumen_distritos = (
            mesas.groupby(distrito_col, dropna=False)
            .agg(
                mesas_csv=("codigoMesa", "count"),
                con_timeline=("tiene_timeline", "sum"),
                sin_timeline=("tiene_timeline", lambda s: int((~s).sum())),
                serie_900001_mas=("serie_especial_900001_mas", "sum"),
                sin_digitalizacion_con_timeline=("anomalia_sin_digitalizacion_con_timeline", "sum"),
                contabilizadas=(f"has_{PHASE_CONTABILIZADA}", "sum"),
                envio_jee=(f"has_{PHASE_JEE}", "sum"),
                alguna_anomalia=("tiene_alguna_anomalia", "sum"),
                mediana_h_dig_a_digit=("h_digitalizacion_a_digitacion", "median"),
                mediana_h_digit_a_cont=("h_digitacion_a_contabilizada", "median"),
            )
            .reset_index()
        )
        resumen_distritos["pct_con_timeline"] = resumen_distritos.apply(
            lambda r: pct(r["con_timeline"], r["mesas_csv"]), axis=1
        )
        resumen_distritos["pct_sin_digitalizacion_con_timeline"] = resumen_distritos.apply(
            lambda r: pct(r["sin_digitalizacion_con_timeline"], r["con_timeline"]), axis=1
        )
        resumen_distritos["pct_serie_900001_mas"] = resumen_distritos.apply(
            lambda r: pct(r["serie_900001_mas"], r["mesas_csv"]), axis=1
        )
        resumen_distritos = resumen_distritos.sort_values(
            ["sin_digitalizacion_con_timeline", "pct_sin_digitalizacion_con_timeline"],
            ascending=False,
        )
    else:
        resumen_distritos = pd.DataFrame()

    flags_priorizados = mesas[mesas["prioridad_revision"].ne("")].copy()
    flags_priorizados = flags_priorizados.sort_values(
        ["prioridad_revision", "n_flags_anomalia", "codigoMesa_num"],
        ascending=[True, False, True],
    )

    anomaly_summary = []
    for c in anomaly_cols:
        n = int(mesas[c].sum())
        denom = int(has_timeline.sum()) if "con_timeline" in c or c.startswith("outlier_") else total_csv
        anomaly_summary.append(
            {"flag": c, "mesas": n, "porcentaje_sobre_denominador": pct(n, denom), "denominador": denom}
        )
    anomaly_summary_df = pd.DataFrame(anomaly_summary).sort_values("mesas", ascending=False)

    cobertura_universo.to_csv(outdir / "01_cobertura_universo_presidencial.csv", index=False)
    csv_vs_sqlite.to_csv(outdir / "02_cobertura_csv_vs_sqlite.csv", index=False)
    mesas_fuera_csv_por_estado.to_csv(outdir / "03_mesas_fuera_csv_por_estado.csv", index=False)
    resumen_flujos.to_csv(outdir / "04_linea_tiempo_flujos_validos.csv", index=False)
    sin_digitalizacion_con_timeline.to_csv(
        outdir / "05_mesas_sin_digitalizacion_con_timeline.csv", index=False
    )
    sin_timeline_o_no_comparables.to_csv(
        outdir / "06_mesas_sin_timeline_o_no_comparables.csv", index=False
    )
    serie_analisis.to_csv(outdir / "07_serie_900001_analisis.csv", index=False)
    if not resumen_distritos.empty:
        resumen_distritos.to_csv(outdir / "08_resumen_por_distrito.csv", index=False)
    else:
        pd.DataFrame().to_csv(outdir / "08_resumen_por_distrito.csv", index=False)
    flags_priorizados.to_csv(outdir / "09_flags_anomalia_priorizada.csv", index=False)

    mesas.to_csv(outdir / "mesas_timeline_features.csv", index=False)
    resumen_duraciones.to_csv(outdir / "resumen_duraciones_horas.csv", index=False)
    anomaly_summary_df.to_csv(outdir / "resumen_flags_anomalia.csv", index=False)
    with open(outdir / "outlier_thresholds.json", "w", encoding="utf-8") as f:
        json.dump(outlier_thresholds, f, indent=2, ensure_ascii=False)

    if args.charts and not args.no_charts:
        save_histogram(
            mesas["h_digitalizacion_a_digitacion"],
            "Horas entre Digitalizacion y Digitacion",
            "Horas",
            charts_dir / "hist_digitalizacion_a_digitacion.png",
        )
        save_histogram(
            mesas["h_digitacion_a_contabilizada"],
            "Horas entre Digitacion y Contabilizacion",
            "Horas",
            charts_dir / "hist_digitacion_a_contabilizada.png",
        )
        save_histogram(
            mesas["h_digitalizacion_a_contabilizada"],
            "Horas entre Digitalizacion y Contabilizacion",
            "Horas",
            charts_dir / "hist_digitalizacion_a_contabilizada.png",
        )
        if not resumen_distritos.empty:
            save_bar(
                resumen_distritos,
                distrito_col,
                "sin_digitalizacion_con_timeline",
                f"Top distritos por mesas sin Digitalizacion con timeline ({distrito_col})",
                "Mesas",
                distrito_col,
                charts_dir / "top_distritos_sin_digitalizacion.png",
                top_n=args.top_districts,
            )
            save_bar(
                resumen_distritos[resumen_distritos["con_timeline"] >= 10],
                distrito_col,
                "pct_sin_digitalizacion_con_timeline",
                f"Top distritos por % sin Digitalizacion con timeline, minimo 10 ({distrito_col})",
                "%",
                distrito_col,
                charts_dir / "top_distritos_pct_sin_digitalizacion.png",
                top_n=args.top_districts,
            )

    sin_dig_timeline = int(mesas["anomalia_sin_digitalizacion_con_timeline"].sum())
    serie_total = int(mesas["serie_especial_900001_mas"].sum())
    serie_sin_dig_timeline = int(
        (mesas["serie_especial_900001_mas"] & mesas["anomalia_sin_digitalizacion_con_timeline"]).sum()
    )

    md = []
    md.append("# Reporte de auditoria de cobertura y linea de tiempo presidencial\n")
    md.append(f"**CSV analizado:** `{input_path}`\n")
    md.append(f"**SQLite analizado:** `{sqlite_path}`\n")
    md.append(
        "\nFrase metodologica central: el analisis de linea de tiempo solo es aplicable "
        "a mesas con detalle disponible y eventos de linea de tiempo registrados. "
        "Las mesas en estados operacionales no finales, como `Para envio al JEE` o "
        "`Pendiente`, se reportan como cobertura no comparable, no como anomalia "
        "temporal por si mismas.\n"
    )

    md.append("\n## 1. Cobertura por universos\n")
    md.append(cobertura_universo.to_markdown(index=False))
    md.append("\n\n## 2. CSV vs SQLite/control\n")
    md.append(csv_vs_sqlite.to_markdown(index=False))
    md.append("\n\n## 3. Mesas fuera del CSV por estado\n")
    md.append(mesas_fuera_csv_por_estado.head(30).to_markdown(index=False))

    md.append("\n\n## 4. Universo auditable por linea de tiempo\n")
    md.append(resumen_flujos.to_markdown(index=False))
    md.append(
        f"\n\nMesas con timeline y sin evento de Digitalizacion: **{sin_dig_timeline:,}** "
        f"({pct(sin_dig_timeline, int(has_timeline.sum())):.2f}% del universo con timeline)."
    )

    md.append("\n\n## 5. Serie 900001+\n")
    md.append(
        f"Serie especial definida como `codigoMesa >= {args.special_threshold}`: "
        f"**{serie_total:,}** mesas en el CSV. De ellas, **{serie_sin_dig_timeline:,}** "
        "tienen timeline pero no evento de Digitalizacion.\n"
    )
    md.append(serie_analisis.to_markdown(index=False))

    md.append("\n\n## 6. Tiempos entre fases, en horas\n")
    md.append(resumen_duraciones.to_markdown(index=False))
    md.append("\n\n## 7. Flags priorizados\n")
    md.append(anomaly_summary_df.to_markdown(index=False))
    if not resumen_distritos.empty:
        md.append("\n\n## 8. Resumen geografico\n")
        md.append(resumen_distritos.head(args.top_districts).to_markdown(index=False))
    md.append("\n\n## 9. Archivos generados\n")
    md.append("- `01_cobertura_universo_presidencial.csv`\n")
    md.append("- `02_cobertura_csv_vs_sqlite.csv`\n")
    md.append("- `03_mesas_fuera_csv_por_estado.csv`\n")
    md.append("- `04_linea_tiempo_flujos_validos.csv`\n")
    md.append("- `05_mesas_sin_digitalizacion_con_timeline.csv`\n")
    md.append("- `06_mesas_sin_timeline_o_no_comparables.csv`\n")
    md.append("- `07_serie_900001_analisis.csv`\n")
    md.append("- `08_resumen_por_distrito.csv`\n")
    md.append("- `09_flags_anomalia_priorizada.csv`\n")
    md.append(
        "- `mesas_timeline_features.csv`, `eventos_linea_tiempo_long.csv` y auxiliares. "
        "Los graficos PNG son opcionales con `--charts`.\n"
    )
    md.append("\n## 10. Advertencia metodologica\n")
    md.append(
        "Este reporte cuantifica cobertura, flujos observables y atipicidades temporales. "
        "No prueba fraude ni perdida de actas por si solo. Las brechas de cobertura deben "
        "contrastarse con JSON originales, PDFs de actas, snapshots historicos del API, "
        "logs de publicacion y procedimientos ONPE/JEE aplicables.\n"
    )
    (outdir / "REPORTE_AUDITORIA_TIMELINE.md").write_text("\n".join(md), encoding="utf-8")

    print("=" * 80)
    print("AUDITORIA COMPLETADA")
    print("=" * 80)
    print(f"CSV presidencial        : {input_path}")
    print(f"SQLite                  : {sqlite_path}")
    print(f"Carpeta de salida       : {outdir}")
    print(f"Control presidencial    : {total_control:,}")
    print(f"DETAIL_OK               : {total_detail_ok:,}")
    print(f"Filas CSV               : {total_csv:,}")
    print(f"CSV con timeline        : {int(has_timeline.sum()):,}")
    print(f"Sin Digitalizacion/tl   : {sin_dig_timeline:,}")
    print(f"Control fuera del CSV   : {len(control_keys - csv_keys):,}")
    print(f"DETAIL_OK fuera del CSV : {len(detail_ok_keys - csv_keys):,}")
    print("Reporte Markdown        :", outdir / "REPORTE_AUDITORIA_TIMELINE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
