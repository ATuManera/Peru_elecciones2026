# Reporte Final Preliminar - Analisis de Ausentismo Presidencial 2006-2026

## Alcance y disclaimer

Estos resultados son estimaciones contrafactuales bajo supuestos explícitos. No constituyen evidencia de manipulación electoral, fraude ni causalidad. Su propósito es analítico y exploratorio.

Este reporte preliminar resume un flujo reproducible construido desde archivos versionados del repositorio. Los flags se interpretan exclusivamente como senales estadisticas para revision, no como prueba de irregularidad ni de intencionalidad.

## Reproducibilidad

- Commit: `8c4c018ff37386fe2345a4c9d2059a8b04e4893d`
- Fecha UTC de ejecucion: `2026-05-01T08:06:36.016619+00:00`
- Directorio de outputs: `data/output/analisis_ausentismo`
- Script: `analyze_ausentismo_presidencial.py`

## Tasa nacional de ausentismo

| Anio | Electores habiles | Votos emitidos | Ausentes | Tasa ausentismo |
| --- | ---: | ---: | ---: | ---: |
| 2006 | 16,276,548 | 14,442,707 | 1,833,841 | 0.112668 |
| 2011 | 19,941,435 | 16,699,734 | 3,241,701 | 0.162561 |
| 2016 | 22,895,434 | 18,734,130 | 4,161,304 | 0.181753 |
| 2021 | 24,850,075 | 17,508,068 | 7,342,007 | 0.295452 |
| 2026 | 25,748,032 | 19,120,194 | 6,627,838 | 0.257411 |

## Exceso estimado por baseline

| Baseline | UBIGEOs evaluados | Exceso positivo de ausentes | Flags MAD >= 3.5 |
| --- | ---: | ---: | ---: |
| baseline_short_2011_2016 | 2,041 | 2206128.261931 | 1,163 |
| baseline_long_2006_2011_2016 | 2,043 | 2684410.712872 | 809 |
| baseline_recent_2016_2021 | 2,063 | 580779.175581 | 119 |
| baseline_robust_median_mad | 2,065 | 1901586.438030 | 554 |

## Principales contribuciones bajo baseline central

Baseline central: `baseline_short_2011_2016`.

| UBIGEO | Departamento | Provincia | Exceso positivo | Exceso relativo | Interpretacion |
| --- | --- | --- | ---: | ---: | --- |
| 140137 | LIMA | LIMA | 54025.313753 | 0.068488 | senal_estadistica_fuerte_para_revision |
| 140126 | LIMA | LIMA | 39167.481430 | 0.075728 | senal_estadistica_fuerte_para_revision |
| 140103 | LIMA | LIMA | 34997.342056 | 0.073000 | senal_estadistica_fuerte_para_revision |
| 240101 | CALLAO | CALLAO | 34533.710715 | 0.091751 | senal_estadistica_fuerte_para_revision |
| 140106 | LIMA | LIMA | 32953.886208 | 0.077012 | senal_estadistica_fuerte_para_revision |
| 140132 | LIMA | LIMA | 28276.385925 | 0.079200 | senal_estadistica_fuerte_para_revision |
| 140136 | LIMA | LIMA | 26339.534295 | 0.088875 | senal_estadistica_fuerte_para_revision |
| 140141 | LIMA | LIMA | 23379.879811 | 0.073213 | senal_estadistica_fuerte_para_revision |
| 140130 | LIMA | LIMA | 23268.437176 | 0.070118 | senal_estadistica_fuerte_para_revision |
| 140101 | LIMA | LIMA | 23228.584426 | 0.079001 | senal_estadistica_fuerte_para_revision |

## Escenarios contrafactuales de votos

Los votos imputados no son votos observados. Cada fila depende del baseline y del modelo de imputacion.

| Baseline | Modelo | Votos imputados contrafactuales |
| --- | --- | ---: |
| baseline_long_2006_2011_2016 | distribucion_nacional | 2684410.712875 |
| baseline_long_2006_2011_2016 | distribucion_ubigeo | 2684410.712870 |
| baseline_long_2006_2011_2016 | matching_ubigeos_aproximado | 2684410.712873 |
| baseline_recent_2016_2021 | distribucion_nacional | 580779.175580 |
| baseline_recent_2016_2021 | distribucion_ubigeo | 580779.175581 |
| baseline_recent_2016_2021 | matching_ubigeos_aproximado | 580779.175581 |
| baseline_robust_median_mad | distribucion_nacional | 1901586.438029 |
| baseline_robust_median_mad | distribucion_ubigeo | 1901586.438031 |
| baseline_robust_median_mad | matching_ubigeos_aproximado | 1901586.438030 |
| baseline_short_2011_2016 | distribucion_nacional | 2206128.261930 |
| baseline_short_2011_2016 | distribucion_ubigeo | 2206128.261930 |
| baseline_short_2011_2016 | matching_ubigeos_aproximado | 2206128.261933 |

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
