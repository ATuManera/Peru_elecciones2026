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

### 5. Reconstruir consolidado de ausentismo

Si el refresh presidencial cambió datos 2026, después del rebuild y del split también se debe regenerar el consolidado histórico de ausentismo:

```bash
python3 build_ausentismo_presidencial.py
```

Salida esperada:

```text
data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv
```

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

Después, volver a correr rebuild, split y consolidado de ausentismo:

```bash
python3 onpe_scraper.py --out ./data --rebuild-csv
python3 split_mesas_por_votacion.py \
  --input ./data/output/mesas_consolidado.csv \
  --outdir ./data/output/por_votacion
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
- `./data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv`
- `./data/state/onpe_scraper.sqlite`
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
