# ONPE Actas Scraper - Elecciones 2026

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](pyproject.toml)

Herramientas operativas para descargar actas desde la API pública de ONPE, reconstruir un CSV consolidado y separar los resultados por tipo de elección.

Este repositorio queda enfocado en cuatro tareas:

1. Descargar JSON crudos de actas ONPE por código de mesa.
2. Mantener estado local de descarga en SQLite para poder reanudar.
3. Reconstruir `mesas_consolidado.csv` desde los JSON descargados.
4. Separar el consolidado en archivos por elección.
5. Consolidar una tabla comparativa de ausentismo presidencial por mesa para 2006, 2011, 2016, 2021 y 2026.

## Disponibilidad Pública de los Datos

La información resultante se pone a disposición pública con fines de transparencia técnica, investigación cívica, desarrollo de analítica electoral y estudio independiente de patrones que pudieran ameritar revisión adicional.

Los archivos publicados deben entenderse como una transformación reproducible de información obtenida desde la aplicación pública de resultados de ONPE. Su publicación no constituye certificación oficial, auditoría electoral, conclusión sobre irregularidades ni atribución de responsabilidad. Cualquier análisis derivado debe contrastarse con las fuentes oficiales, las actas correspondientes y el marco normativo aplicable.

## Licencia

Este proyecto se publica bajo la **Apache License 2.0**.

Copyright 2026 A Tu Manera Digital - Fernando Gallarday.

Ver `LICENSE` para los términos completos y `NOTICE` para la atribución del proyecto.

## Alcance Actual

El proyecto simplificado conserva solo el flujo operativo de datos ONPE:

- `onpe_scraper.py`: descarga, estado SQLite, rebuild de CSV y reportes básicos.
- `refresh_presidencial_only_v2.py`: refresh incremental solo de Presidencial (`idEleccion = 10`).
- `split_mesas_por_votacion.py`: split del consolidado en 5 archivos por elección.
- `build_ausentismo_presidencial.py`: consolidación de ausentismo presidencial por mesa con fuentes históricas ONPE y datos 2026.
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
onpe-build-ausentismo --help
```

## Uso de la API de ONPE

Este proyecto utiliza el endpoint que consume la propia aplicación pública de resultados de ONPE para consultar actas por código de mesa.

La forma de uso documentada aquí **no proviene de una especificación oficial publicada por ONPE**. Fue investigada mediante revisión técnica de la comunicación interna entre el frontend público de ONPE y su backend, observando las solicitudes HTTP que realiza la aplicación al consultar actas. Por esa razón, esta integración debe considerarse una adaptación operativa y no un contrato formal de API: el endpoint, sus headers, el esquema de respuesta o los requisitos de sesión pueden cambiar sin aviso.

Endpoint observado:

```text
GET https://resultadoelectoral.onpe.gob.pe/presentacion-backend/actas/buscar/mesa?codigoMesa=<codigoMesa>
```

Ejemplo:

```text
https://resultadoelectoral.onpe.gob.pe/presentacion-backend/actas/buscar/mesa?codigoMesa=000755
```

El parámetro `codigoMesa` debe enviarse como código de seis dígitos, con ceros a la izquierda cuando corresponda.

Buenas prácticas aplicadas por este repositorio:

- Usar la misma semántica de consulta que la aplicación pública: una mesa por solicitud.
- Mantener una tasa de consultas conservadora mediante `--rps`.
- Reanudar descargas con `--resume` para evitar repetir solicitudes innecesarias.
- Guardar la respuesta original como JSON crudo en `data/raw_json/` para preservar trazabilidad.
- Reconstruir los CSV desde los JSON descargados, en vez de depender de transformaciones no reproducibles.
- Registrar estado local en SQLite para identificar mesas descargadas, inexistentes o pendientes de reintento.
- No versionar cookies ni información de sesión. `cookie.txt` está excluido del repositorio.

Algunas solicitudes pueden requerir una cookie vigente de navegación. Esa cookie debe obtenerse desde una sesión propia en el navegador y guardarse localmente en `cookie.txt`; no debe publicarse ni compartirse en commits, issues o documentación.

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
python3 build_ausentismo_presidencial.py
```

### 4. Consolidar ausentismo presidencial histórico

Los archivos históricos oficiales descargados de ONPE para primera vuelta presidencial se ubican en:

```text
data/input/onpe_historico/presidencial_primera_vuelta/
```

La fuente oficial de descarga es:

```text
https://www.onpe.gob.pe/elecciones/historico-elecciones/
```

Esta ubicación separa insumos externos de ONPE (`data/input`) de archivos reconstruidos por el proyecto (`data/output`). Se conservan los nombres originales de los archivos para mantener trazabilidad con la descarga oficial.

Para generar la tabla consolidada de ausentismo presidencial por mesa:

```bash
python3 build_ausentismo_presidencial.py \
  --input-dir ./data/input/onpe_historico/presidencial_primera_vuelta \
  --presidencial-2026 ./data/output/por_votacion/mesas_presidencial.csv \
  --out ./data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv
```

La salida contiene una fila por mesa y año, con electores hábiles, votos emitidos, ausentes y tasa de ausentismo. Para 2006, 2011, 2016 y 2021 utiliza los archivos históricos oficiales de ONPE; para 2026 utiliza el CSV presidencial generado por este repositorio. Algunas mesas pueden tener campos centrales vacíos si el acta no cuenta con cómputo completo en la fuente disponible; esas filas se conservan para no alterar la cobertura territorial.

## Estructura de Datos

Directorios y archivos principales:

- `data/input/onpe_historico/presidencial_primera_vuelta/`: insumos históricos oficiales de ONPE para primera vuelta presidencial 2006, 2011, 2016 y 2021, junto con sus diccionarios de datos.
- `data/raw_json/`: JSON crudos por mesa.
- `data/state/onpe_scraper.sqlite`: estado local de descarga y control.
- `data/output/mesas_consolidado.csv`: consolidado reconstruido.
- [`data/output/por_votacion/mesas_presidencial.csv`](https://github.com/ATuManera/Peru_elecciones2026/raw/main/data/output/por_votacion/mesas_presidencial.csv?download=1): detalle del resultado de la votación presidencial. Click para descargar el CSV directamente.
- `data/output/por_votacion/`: detalle del resto de elecciones en CSV separados por elección.
- [`data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv`](https://github.com/ATuManera/Peru_elecciones2026/raw/main/data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv?download=1): tabla consolidada de ausentismo presidencial por mesa y año. Click para descargar el CSV directamente.
- `data/reports/`: reportes básicos del scraper.
- `data/manifests/`: manifiesto de descarga.

Los archivos en `data/output/`, `data/reports/` y `data/manifests/` son reconstruibles y pueden ser grandes. Los insumos bajo `data/input/` son fuentes externas históricas conservadas para reproducibilidad del análisis.

Para descargar el CSV presidencial desde terminal:

```bash
curl -L \
  -o mesas_presidencial.csv \
  "https://github.com/ATuManera/Peru_elecciones2026/raw/main/data/output/por_votacion/mesas_presidencial.csv?download=1"
```

Para descargar el CSV consolidado de ausentismo presidencial desde terminal:

```bash
curl -L \
  -o mesas_ausentismo_presidencial_2006_2026.csv \
  "https://github.com/ATuManera/Peru_elecciones2026/raw/main/data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv?download=1"
```

Nota: los archivos de resultados están versionados con extensión `.csv`. GitHub puede mostrarlos en el navegador como texto por el tipo de visualización del sitio o por Git LFS, pero el archivo descargado conserva la extensión y estructura CSV. Para archivos grandes, se recomienda usar el enlace con `?download=1`, `curl -L` o la opción del navegador "Guardar enlace como...".

## Campos del CSV Presidencial

El archivo `data/output/por_votacion/mesas_presidencial.csv` contiene una fila por mesa de sufragio para la elección presidencial (`idEleccion = 10`). Es un CSV plano generado desde los JSON de ONPE, por lo que algunas estructuras anidadas del origen se representan como familias de columnas repetitivas.

Resumen ejecutivo de campos:

| Familia de campos | Columnas | Descripción para analítica |
| --- | --- | --- |
| Identificación de mesa | `codigoMesa`, `id`, `idEleccion` | Identifican la mesa y el registro interno de la elección. `codigoMesa` debe tratarse como texto para conservar ceros a la izquierda. |
| Ubicación electoral | `ubigeoNivel01`, `ubigeoNivel02`, `ubigeoNivel03`, `centroPoblado`, `nombreLocalVotacion` | Permiten agrupar resultados por ámbito geográfico y local de votación. Los códigos de ubigeo deben conservarse como texto. |
| Totales de participación | `totalElectoresHabiles`, `totalVotosEmitidos`, `totalVotosValidos` | Métricas principales por mesa. Sirven para calcular participación, votos válidos y consistencias básicas. |
| Estado del acta | `estadoActa`, `estadoComputo`, `codigoEstadoActa`, `descripcionEstadoActa`, `estadoActaResolucion`, `estadoDescripcionActaResolucion`, `descripcionSubEstadoActa` | Describen la situación operativa y de cómputo del acta al momento de la descarga o refresh. Son claves para separar mesas contabilizadas, pendientes, observadas o enviadas a revisión. |
| Votos por organización política | `detalle_1_*` a `detalle_38_*` | Cada bloque representa una opción presidencial en el orden publicado por ONPE. Incluye `descripcion`, `cdocumentoIdentidad`, `nposicion` y `nvotos`. Para agregaciones, usar principalmente `detalle_N_descripcion`, `detalle_N_nposicion` y `detalle_N_nvotos`. |
| Votos especiales | `detalle_80_*`, `detalle_81_*`, `detalle_82_*` | Bloques reservados para `VOTOS EN BLANCO`, `VOTOS NULOS` y `VOTOS IMPUGNADOS`, respectivamente. Ayudan a reconciliar `totalVotosEmitidos` con votos válidos y no válidos. |
| Línea de tiempo del acta | `lineaTiempo_1_*` a `lineaTiempo_31_*` | Secuencia de eventos registrada para el acta. Cada bloque puede incluir `codigoEstadoActa`, `descripcionEstadoActa`, `descripcionEstadoActaResolucion` y `fechaRegistro`. Sirve para análisis de tiempos, transiciones y estados finales. |

Consideraciones de uso:

- Los campos numéricos pueden llegar vacíos cuando ONPE no publica un valor para una mesa o estado específico; conviene normalizarlos antes de calcular.
- Las columnas `detalle_N_nvotos` de organizaciones políticas representan votos válidos por opción. Los bloques `detalle_80`, `detalle_81` y `detalle_82` representan votos no válidos o especiales.
- Para análisis territoriales, mantener `codigoMesa` y los `ubigeo*` como texto evita perder ceros iniciales.
- Para estudios de potenciales anomalías, separar primero las mesas por `descripcionEstadoActa` o `codigoEstadoActa`; comparar mesas en estados distintos puede producir conclusiones erróneas.
- La línea de tiempo debe interpretarse como eventos observados en la respuesta pública disponible al momento de la descarga, no como una bitácora oficial completa ni inmutable.

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
