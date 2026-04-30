#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from project_metadata import build_argument_parser


def pick_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lower_map = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def normalize(value: str | None, default: str) -> str:
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def main() -> int:
    parser = build_argument_parser(
        description="Resume anomalias.csv por tipo, severidad y mesas más problemáticas"
    )
    parser.add_argument(
        "--input",
        default="./data/reports/anomalias.csv",
        help="Ruta al anomalias.csv",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Cantidad de tipos más frecuentes a mostrar",
    )
    parser.add_argument(
        "--top-mesas",
        type=int,
        default=20,
        help="Cantidad de mesas más problemáticas a mostrar",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Directorio opcional para exportar resúmenes CSV",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"No existe el archivo: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if not fieldnames:
        raise SystemExit("El CSV no tiene cabecera o está vacío.")

    tipo_col = pick_column(
        fieldnames,
        ["tipo_anomalia", "tipo", "anomalia", "anomaly_type"],
    )
    sev_col = pick_column(
        fieldnames,
        ["severity", "severidad", "nivel", "criticidad"],
    )
    mesa_col = pick_column(
        fieldnames,
        ["codigoMesa", "codigo_mesa", "mesa"],
    )
    detalle_col = pick_column(
        fieldnames,
        ["detalle", "detail", "descripcion", "description"],
    )

    if not tipo_col:
        raise SystemExit(
            f"No encontré columna de tipo. Columnas detectadas: {fieldnames}"
        )

    tipo_counter: Counter[str] = Counter()
    sev_counter: Counter[str] = Counter()
    tipo_sev_counter: Counter[tuple[str, str]] = Counter()
    mesas_por_tipo: dict[str, set[str]] = defaultdict(set)
    ejemplos_por_tipo: dict[str, str] = {}

    mesa_counter: Counter[str] = Counter()
    mesa_tipo_counter: dict[str, Counter[str]] = defaultdict(Counter)
    mesa_sev_counter: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        tipo = normalize(row.get(tipo_col), "DESCONOCIDO")
        sev = normalize(row.get(sev_col), "SIN_SEVERIDAD") if sev_col else "SIN_SEVERIDAD"
        mesa = normalize(row.get(mesa_col), "") if mesa_col else ""
        detalle = normalize(row.get(detalle_col), "") if detalle_col else ""

        tipo_counter[tipo] += 1
        sev_counter[sev] += 1
        tipo_sev_counter[(tipo, sev)] += 1

        if mesa:
            mesas_por_tipo[tipo].add(mesa)
            mesa_counter[mesa] += 1
            mesa_tipo_counter[mesa][tipo] += 1
            mesa_sev_counter[mesa][sev] += 1

        if tipo not in ejemplos_por_tipo and detalle:
            ejemplos_por_tipo[tipo] = detalle[:200]

    total = len(rows)
    mesas_unicas_total = len(mesa_counter)

    print("=" * 72)
    print("RESUMEN GENERAL")
    print("=" * 72)
    print(f"Archivo: {input_path}")
    print(f"Total de anomalías: {total}")
    if mesa_col:
        print(f"Mesas únicas con anomalías: {mesas_unicas_total}")
    print()

    print("=" * 72)
    print("RESUMEN POR SEVERIDAD")
    print("=" * 72)
    for sev, count in sev_counter.most_common():
        pct = (count / total * 100) if total else 0
        print(f"{sev:20s} {count:10d}  ({pct:6.2f}%)")
    print()

    print("=" * 72)
    print(f"TOP {args.top} TIPOS DE ANOMALÍA")
    print("=" * 72)
    for tipo, count in tipo_counter.most_common(args.top):
        pct = (count / total * 100) if total else 0
        mesas_unicas = len(mesas_por_tipo.get(tipo, set()))
        ejemplo = ejemplos_por_tipo.get(tipo, "")
        print(f"- {tipo}")
        print(f"  ocurrencias      : {count}")
        print(f"  % del total      : {pct:.2f}%")
        if mesa_col:
            print(f"  mesas únicas     : {mesas_unicas}")
        if sev_col:
            sev_breakdown = {
                sev: tipo_sev_counter[(tipo, sev)]
                for sev in sev_counter
                if tipo_sev_counter[(tipo, sev)] > 0
            }
            sev_str = ", ".join(f"{k}={v}" for k, v in sorted(sev_breakdown.items()))
            print(f"  severidades      : {sev_str}")
        if ejemplo:
            print(f"  ejemplo detalle  : {ejemplo}")
        print()

    if mesa_col:
        print("=" * 72)
        print(f"TOP {args.top_mesas} MESAS MÁS PROBLEMÁTICAS")
        print("=" * 72)
        for mesa, count in mesa_counter.most_common(args.top_mesas):
            tipos_top = mesa_tipo_counter[mesa].most_common(3)
            sevs_top = mesa_sev_counter[mesa].most_common(3)

            tipos_str = ", ".join(f"{t}={n}" for t, n in tipos_top)
            sevs_str = ", ".join(f"{s}={n}" for s, n in sevs_top)

            print(f"- Mesa {mesa}")
            print(f"  anomalías totales : {count}")
            print(f"  top tipos         : {tipos_str}")
            if sev_col:
                print(f"  top severidades   : {sevs_str}")
            print()

    if args.outdir:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        by_type_path = outdir / "anomalias_resumen_por_tipo.csv"
        by_sev_path = outdir / "anomalias_resumen_por_severidad.csv"
        by_type_sev_path = outdir / "anomalias_resumen_por_tipo_y_severidad.csv"
        by_mesa_path = outdir / "anomalias_resumen_por_mesa.csv"

        with by_type_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["tipo_anomalia", "ocurrencias", "mesas_unicas", "ejemplo_detalle"])
            for tipo, count in tipo_counter.most_common():
                writer.writerow([
                    tipo,
                    count,
                    len(mesas_por_tipo.get(tipo, set())),
                    ejemplos_por_tipo.get(tipo, ""),
                ])

        with by_sev_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["severity", "ocurrencias"])
            for sev, count in sev_counter.most_common():
                writer.writerow([sev, count])

        with by_type_sev_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["tipo_anomalia", "severity", "ocurrencias"])
            for (tipo, sev), count in sorted(
                tipo_sev_counter.items(),
                key=lambda x: (-x[1], x[0][0], x[0][1]),
            ):
                writer.writerow([tipo, sev, count])

        with by_mesa_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "codigoMesa",
                "anomalias_totales",
                "top_tipo_1",
                "top_tipo_2",
                "top_tipo_3",
                "top_severidad_1",
                "top_severidad_2",
                "top_severidad_3",
            ])
            for mesa, count in mesa_counter.most_common():
                tipos_top = [f"{t}={n}" for t, n in mesa_tipo_counter[mesa].most_common(3)]
                sevs_top = [f"{s}={n}" for s, n in mesa_sev_counter[mesa].most_common(3)]

                while len(tipos_top) < 3:
                    tipos_top.append("")
                while len(sevs_top) < 3:
                    sevs_top.append("")

                writer.writerow([
                    mesa,
                    count,
                    tipos_top[0],
                    tipos_top[1],
                    tipos_top[2],
                    sevs_top[0],
                    sevs_top[1],
                    sevs_top[2],
                ])

        print("=" * 72)
        print("ARCHIVOS EXPORTADOS")
        print("=" * 72)
        print(by_type_path)
        print(by_sev_path)
        print(by_type_sev_path)
        print(by_mesa_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
