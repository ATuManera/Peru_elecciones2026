# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El proyecto sigue versionado semántico para el código y las herramientas operativas. Los CSV publicados pueden actualizarse entre versiones mediante refresh, rebuild y split; para reproducibilidad, citar también el commit usado.

## 0.3.2 - 2026-05-02

- Genera `data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.md` como vista renderizada en GitHub del desagregado territorial.
- Escribe `data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv` con BOM UTF-8 para mejorar compatibilidad con visores crudos y hojas de cálculo.
- Actualiza README para enlazar primero la vista Markdown y dejar el CSV como descarga directa.

## 0.3.1 - 2026-05-02

- Agrega `update_readme_status.py` y el comando instalable `onpe-update-readme-status` para recalcular automáticamente el estado de avance presidencial en README después de cada refresh/rebuild/split.
- El estado generado en README ahora incluye snapshot de datos con CSV fuente, fecha/hora de modificación del CSV y commit local de base.
- Genera `data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv` con desagregado territorial por `PERU` / `EXTRANJERO`, región, provincia y distrito para mesas `Para envío al JEE` y `Pendiente`.
- Reemplaza la tabla territorial extensa del README por un enlace al CSV derivado.
- Actualiza el estado de datos presidenciales documentado en README.

## 0.3.0 - 2026-05-02

- Agrega `consultar_padron_mesas.py` para consultar mesa de votación desde una lista cerrada de DNIs provistos explícitamente en TXT.
- Agrega el comando instalable `onpe-consultar-padron-mesas`.
- Corrige el rebuild de `mesas_consolidado.csv` para incluir todo JSON descargado válido, aunque el estado agregado de `mesas` haya quedado desfasado después de un refresh presidencial.
- Regenera `mesas_consolidado.csv` y los splits por votación con cobertura presidencial alineada al control SQLite local.

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
