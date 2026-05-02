# README_OPERACION

Guía corta para operar el flujo actual del scraper ONPE.

## Flujo Normal

### 1. Validar cookie

```bash
curl -s -D - 'https://resultadoelectoral.onpe.gob.pe/presentacion-backend/actas/buscar/mesa?codigoMesa=000755' \
  -H 'accept: */*' \
  -H 'accept-language: es-419,es;q=0.9' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -b "$(cat cookie.txt)" \
  -H 'pragma: no-cache' \
  -H 'priority: u=1, i' \
  -H 'referer: https://resultadoelectoral.onpe.gob.pe/main/actas' \
  -H 'sec-ch-ua: "Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  -o /dev/null
```

Debe devolver:

```text
content-type: application/json
```

Si devuelve HTML, refrescar `cookie.txt`.

### 2.A. Refresh frecuente solo Presidencial en `Pendiente`

```bash
python3 refresh_presidencial_only_v2.py \
  --out ./data \
  --db ./data/state/onpe_scraper.sqlite \
  --cookie-file ./cookie.txt \
  --rps 0.3 \
  --estado Pendiente
```

### 2.B. Refresh frecuente Presidencial en `Pendiente` y `Para envío al JEE`

```bash
python3 refresh_presidencial_only_v2.py \
  --out ./data \
  --db ./data/state/onpe_scraper.sqlite \
  --cookie-file ./cookie.txt \
  --rps 1 \
  --estado Pendiente \
  --estado "Para envío al JEE"
```

### 3. Reconstruir consolidado

```bash
python3 onpe_scraper.py --out ./data --rebuild-csv
```

### 4. Separar archivos por elección

```bash
python3 split_mesas_por_votacion.py \
  --input ./data/output/mesas_consolidado.csv \
  --outdir ./data/output/por_votacion
```

Archivos esperados:

- `mesas_presidencial.csv`
- `mesas_parlamento_andino.csv`
- `mesas_diputados.csv`
- `mesas_senadores_distrito_electoral_multiple.csv`
- `mesas_senadores_distrito_electoral_unico.csv`

### 5. Actualizar estado publicado en README

Después del rebuild y del split, recalcular la sección `Estado de Actualización de Datos`
de `README.md` desde el CSV presidencial actualizado:

```bash
python3 update_readme_status.py
```

Este paso actualiza automáticamente:

- avance de mesas contabilizadas;
- snapshot de datos con CSV fuente, fecha/hora de modificación del CSV y commit local de base;
- resumen por estado;
- resumen territorial en README por estado, ámbito y región para `Para envío al JEE` y `Pendiente`;
- CSV UTF-8 con BOM y vista Markdown renderizada con desagregado territorial por `PERU` / `EXTRANJERO`, región, provincia y distrito para `Para envío al JEE` y `Pendiente`;
- cuadro de votos válidos con los primeros 5 grupos y `Otros candidatos`;
- nota de blancos, nulos e impugnados excluidos del denominador ONPE de votos válidos.

La versión del proyecto no cambia por refresh de datos. La evidencia del refresh queda en
`README.md`, sección `Estado de Actualización de Datos`, y en el commit que incluya los CSV
y el README regenerado.

### 6. Reconstruir consolidado de ausentismo

Si el refresh presidencial cambió datos 2026, después del rebuild y del split también se debe regenerar el consolidado histórico de ausentismo:

```bash
python3 build_ausentismo_presidencial.py
```

Salida esperada:

```text
data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv
data/output/catalogos/ubigeo_onpe_catalog.csv
```

El catálogo `ubigeo_onpe_catalog.csv` se deriva de históricos ONPE del repositorio y es la fuente de verdad territorial para completar nombres de departamento, provincia y distrito en 2026 cuando el mismo `ubigeo` existe. No usar `data_dictionary/ubigeo/departamentos.csv` para etiquetar estos datasets ONPE salvo demostración explícita de compatibilidad: la codificación territorial ONPE observada aquí no debe asumirse equivalente a catálogos externos.

Validación territorial mínima:

```bash
python3 validate_ubigeo_onpe_mapping.py
```

Debe confirmar que la mesa `050915` de 2026 queda en `ubigeo=140130`, `LIMA / LIMA / SANTIAGO DE SURCO`, y que ningún registro ONPE del consolidado de ausentismo con prefijo `14` queda rotulado como `LAMBAYEQUE`.

## Flujo Ocasional

### Revisar Presidencial en `Para envío al JEE`

```bash
python3 refresh_presidencial_only_v2.py \
  --out ./data \
  --db ./data/state/onpe_scraper.sqlite \
  --cookie-file ./cookie.txt \
  --rps 0.3 \
  --estado "Para envío al JEE"
```

Después, volver a correr rebuild, split, actualización de README y consolidado de ausentismo:

```bash
python3 onpe_scraper.py --out ./data --rebuild-csv
python3 split_mesas_por_votacion.py \
  --input ./data/output/mesas_consolidado.csv \
  --outdir ./data/output/por_votacion
python3 update_readme_status.py
python3 build_ausentismo_presidencial.py
```

## Smoke Test

```bash
python3 refresh_presidencial_only_v2.py \
  --out ./data \
  --db ./data/state/onpe_scraper.sqlite \
  --cookie-file ./cookie.txt \
  --rps 0.3 \
  --estado Pendiente \
  --limit 20
```

## Bootstrap Presidencial

Solo usar si necesitas crear o recargar `mesa_presidencial_control` desde el consolidado.

```bash
python3 refresh_presidencial_only_v2.py \
  --db ./data/state/onpe_scraper.sqlite \
  --bootstrap-from-csv \
  --csv ./data/output/mesas_consolidado.csv \
  --truncate-bootstrap
```

## Archivos Importantes

- `./data/output/mesas_consolidado.csv`
- `./data/output/por_votacion/mesas_presidencial.csv`
- `./data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv`
- `./data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.md`
- `./data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv`
- `./data/state/onpe_scraper.sqlite`
- `./README.md`
- `./cookie.txt`

## SQL Útil

```sql
SELECT estado_control, COUNT(*)
FROM mesa_presidencial_control
GROUP BY estado_control
ORDER BY estado_control;
```

```sql
SELECT COUNT(*)
FROM mesa_presidencial_control
WHERE estado_control = 'Pendiente';
```

```sql
SELECT COUNT(*)
FROM mesa_presidencial_control
WHERE estado_control = 'Para envío al JEE';
```

## Fuera Del Flujo Actual

No usar para la operación simplificada:

- `src/fraud_detector/`
- `docker-compose.yml`
- `fraud-detector`
- specs de dashboard, API, LLM u OCR
