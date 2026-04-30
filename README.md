# ONPE Actas Scraper - Elecciones 2026

Herramientas operativas para descargar actas desde la API pública de ONPE, reconstruir un CSV consolidado y separar los resultados por tipo de elección.

Este repositorio queda enfocado en cuatro tareas:

1. Descargar JSON crudos de actas ONPE por código de mesa.
2. Mantener estado local de descarga en SQLite para poder reanudar.
3. Reconstruir `mesas_consolidado.csv` desde los JSON descargados.
4. Separar el consolidado en archivos por elección.

## Licencia

Este proyecto se publica bajo la **Apache License 2.0**.

Copyright 2026 A Tu Manera Digital - Fernando Gallarday.

Ver `LICENSE` para los términos completos y `NOTICE` para la atribución del proyecto.

## Alcance Actual

El proyecto simplificado conserva solo el flujo operativo de datos ONPE:

- `onpe_scraper.py`: descarga, estado SQLite, rebuild de CSV y reportes básicos.
- `refresh_presidencial_only_v2.py`: refresh incremental solo de Presidencial (`idEleccion = 10`).
- `split_mesas_por_votacion.py`: split del consolidado en 5 archivos por elección.
- `README_OPERACION.md`: guía corta de operación diaria.

Queda fuera del flujo principal el pipeline grande de análisis estadístico ubicado en `src/fraud_detector`. Ese código se considera legado/experimental y no es necesario para descargar, consolidar ni separar los datos ONPE.

También quedan fuera de esta simplificación:

- API o dashboard web.
- FastAPI, Next.js o Supabase Auth.
- LLMs para explicaciones automáticas.
- OCR o carga manual de actas PDF.
- Ranking estadístico en Postgres.

## Requisitos

Python 3.11 o superior.

Los scripts principales usan librerías estándar de Python y `curl` para las consultas protegidas por cookie. El script de auditoría temporal `analyze_timeline_presidencial.py` es opcional y requiere dependencias extra:

```bash
python3 -m pip install -e ".[audit]"
```

## Instalación Opcional

Puedes ejecutar los scripts directamente:

```bash
python3 onpe_scraper.py --help
python3 split_mesas_por_votacion.py --help
python3 refresh_presidencial_only_v2.py --help
```

O instalar los comandos locales:

```bash
python3 -m pip install -e .
```

Comandos instalados:

```bash
onpe-scraper --help
onpe-split-votacion --help
onpe-refresh-presidencial --help
```

## Flujo Principal

### 1. Descargar o reconstruir datos

Para descargar un rango:

```bash
python3 onpe_scraper.py \
  --start 1 \
  --end 999999 \
  --out ./data \
  --workers 4 \
  --rps 1 \
  --resume \
  --cookie-file ./cookie.txt
```

Para reconstruir el CSV desde JSON ya descargados:

```bash
python3 onpe_scraper.py --out ./data --rebuild-csv
```

### 2. Separar por elección

```bash
python3 split_mesas_por_votacion.py \
  --input ./data/output/mesas_consolidado.csv \
  --outdir ./data/output/por_votacion
```

Genera:

- `mesas_presidencial.csv`
- `mesas_parlamento_andino.csv`
- `mesas_diputados.csv`
- `mesas_senadores_distrito_electoral_multiple.csv`
- `mesas_senadores_distrito_electoral_unico.csv`

El detalle del resultado de la votación presidencial está en:

```text
data/output/por_votacion/mesas_presidencial.csv
```

El detalle del resto de elecciones está en los demás CSV de:

```text
data/output/por_votacion/
```

### 3. Refresh presidencial incremental

Para refrescar solo mesas presidenciales pendientes:

```bash
python3 refresh_presidencial_only_v2.py \
  --out ./data \
  --db ./data/state/onpe_scraper.sqlite \
  --cookie-file ./cookie.txt \
  --rps 0.3 \
  --estado Pendiente
```

Para revisar también las que están `Para envío al JEE`:

```bash
python3 refresh_presidencial_only_v2.py \
  --out ./data \
  --db ./data/state/onpe_scraper.sqlite \
  --cookie-file ./cookie.txt \
  --rps 0.3 \
  --estado "Para envío al JEE"
```

Después de un refresh con cambios:

```bash
python3 onpe_scraper.py --out ./data --rebuild-csv
python3 split_mesas_por_votacion.py \
  --input ./data/output/mesas_consolidado.csv \
  --outdir ./data/output/por_votacion
```

## Estructura de Datos

Directorios generados:

- `data/raw_json/`: JSON crudos por mesa.
- `data/state/onpe_scraper.sqlite`: estado local de descarga y control.
- `data/output/mesas_consolidado.csv`: consolidado reconstruido.
- `data/output/por_votacion/mesas_presidencial.csv`: detalle del resultado de la votación presidencial.
- `data/output/por_votacion/`: detalle del resto de elecciones en CSV separados por elección.
- `data/reports/`: reportes básicos del scraper.
- `data/manifests/`: manifiesto de descarga.

Estos archivos son reconstruibles y pueden ser grandes, por eso están fuera de git por defecto.

## Cookie

La API de ONPE puede requerir cookie vigente. Guarda la cookie completa en:

```text
cookie.txt
```

Debe estar en una sola línea, sin prefijo `cookie:` y sin comillas.

`cookie.txt` está ignorado por git porque contiene información de sesión local.

## Validación Rápida

```bash
python3 onpe_scraper.py --help
python3 refresh_presidencial_only_v2.py --help
python3 split_mesas_por_votacion.py --help
python3 onpe_scraper.py --out ./data --rebuild-csv
python3 split_mesas_por_votacion.py \
  --input ./data/output/mesas_consolidado.csv \
  --outdir ./data/output/por_votacion
```

## Nota Sobre Código Legado

El directorio `src/fraud_detector` y sus pruebas pertenecen a una línea de trabajo anterior: detección estadística, snapshots, Postgres y rankings de anomalía. No forma parte del flujo operativo simplificado.

Se deja en el repositorio solo como referencia histórica mientras se decide si se elimina, se archiva o se mueve a otro proyecto.
