# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El proyecto sigue versionado semántico para el código y las herramientas operativas. Los CSV publicados pueden actualizarse entre versiones mediante refresh, rebuild y split; para reproducibilidad, citar también el commit usado.

## Unreleased

- Agrega `analyze_ausentismo_presidencial.py` para generar un flujo reproducible de análisis de ausentismo presidencial 2006-2026.
- Publica salidas analíticas bajo `data/output/analisis_ausentismo/`: auditoría, agregados por mesa/UBIGEO, baselines, flags estadísticos, concentración geográfica, escenarios contrafactuales y sensibilidad.
- Agrega `FINAL_REPORT.md` como reporte preliminar con disclaimer metodológico y límites de interpretación.
- Documenta la operación del análisis en `README.md` y `README_OPERACION.md`.

## 0.2.0 - 2026-05-01

- Agrega insumos históricos oficiales de ONPE para primera vuelta presidencial 2006, 2011, 2016 y 2021.
- Agrega `build_ausentismo_presidencial.py` para consolidar ausentismo presidencial por mesa entre 2006 y 2026.
- Publica `data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv`.
- Documenta la ubicación de fuentes históricas, la salida de ausentismo y el paso operativo para regenerarla después de refresh/rebuild/split.
- Corrige el mapeo territorial UBIGEO ONPE de outputs derivados: 2026 ahora completa `departamento`, `provincia` y `distrito` desde `data/output/catalogos/ubigeo_onpe_catalog.csv`, derivado de históricos ONPE del repo, sin fallback silencioso a catálogos externos incompatibles.
- Agrega `validate_ubigeo_onpe_mapping.py` para verificar que `140130 = LIMA / LIMA / SANTIAGO DE SURCO`, que la mesa `050915` de 2026 queda correctamente etiquetada y que prefijos `14` no se rotulan como `LAMBAYEQUE`.

## 0.1.0 - 2026-04-30

- Publica el flujo operativo base para descargar actas ONPE 2026, reconstruir `mesas_consolidado.csv` y separar los resultados por elección.
- Incorpora documentación de licencia, autoría, uso observado de la API ONPE y estructura de datos.
