# ONPE Actas Scraper - Elecciones 2026

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Version](https://img.shields.io/badge/version-0.3.4-green.svg)](pyproject.toml)

Herramientas operativas para descargar actas desde la API pública de ONPE, reconstruir un CSV consolidado y separar los resultados por tipo de elección.

Este repositorio queda enfocado en seis tareas:

1. Descargar JSON crudos de actas ONPE por código de mesa.
2. Mantener estado local de descarga en SQLite para poder reanudar.
3. Reconstruir `mesas_consolidado.csv` desde los JSON descargados.
4. Separar el consolidado en archivos por elección.
5. Consolidar una tabla comparativa de ausentismo presidencial por mesa para 2006, 2011, 2016, 2021 y 2026.
6. Consultar mesa de votación para una lista cerrada de DNIs provistos explícitamente.

## Disponibilidad Pública de los Datos

La información resultante se pone a disposición pública con fines de transparencia técnica, investigación cívica, desarrollo de analítica electoral y estudio independiente de patrones que pudieran ameritar revisión adicional.

Los archivos publicados deben entenderse como una transformación reproducible de información obtenida desde la aplicación pública de resultados de ONPE. Su publicación no constituye certificación oficial, auditoría electoral, conclusión sobre irregularidades ni atribución de responsabilidad. Cualquier análisis derivado debe contrastarse con las fuentes oficiales, las actas correspondientes y el marco normativo aplicable.

## Licencia

Este proyecto se publica bajo la **Apache License 2.0**.

Copyright 2026 A Tu Manera Digital - Fernando Gallarday.

Ver `LICENSE` para los términos completos y `NOTICE` para la atribución del proyecto.

## Versionado

El proyecto usa versionado semántico para el código y las herramientas operativas. La versión actual es **0.3.4**.

- `0.1.0`: flujo base para descargar, reconstruir y separar resultados ONPE 2026.
- `0.2.0`: incorpora insumos históricos oficiales de ONPE, el script `build_ausentismo_presidencial.py` y el CSV consolidado de ausentismo presidencial 2006-2026.
- `0.3.0`: agrega `consultar_padron_mesas.py`, el comando `onpe-consultar-padron-mesas` y corrige el rebuild de `mesas_consolidado.csv` para incluir todo JSON descargado válido, evitando excluir mesas cuyo estado agregado quedó desfasado.
- `0.3.1`: agrega `update_readme_status.py`, el comando `onpe-update-readme-status`, el snapshot de datos en README y el CSV territorial de mesas presidenciales `Para envío al JEE` o `Pendiente`.
- `0.3.2`: agrega una vista Markdown renderizada para el desagregado territorial y emite el CSV territorial con BOM UTF-8 para mejorar compatibilidad de visualización.
- `0.3.3`: agrega al README un resumen automático por estado, ámbito y región para ubicar de un vistazo las mesas `Para envío al JEE` o `Pendiente`.
- `0.3.4`: agrega `Electores hábiles` a los resúmenes de estado, región y detalle territorial para estimar el techo potencial de votos no contabilizados.

Los datos publicados tienen un ciclo de actualización distinto al del código: pueden cambiar con cada refresh incremental, rebuild y split. Para reproducibilidad, se recomienda citar la ruta del archivo, la fecha de descarga o actualización y el commit de GitHub usado como referencia.

## Estado de Actualización de Datos

Según `data/output/por_votacion/mesas_presidencial.csv` y el control SQLite local, las mesas presidenciales consolidadas cubren un universo de **92,766** mesas. Con corte de refresh al **6 de mayo de 2026**, el avance de mesas contabilizadas es **98.24%**.

Snapshot de datos: generado automáticamente por `update_readme_status.py` desde `data/output/por_votacion/mesas_presidencial.csv`; CSV modificado el **6 de mayo de 2026 17:32:25 PET**. Commit local de base: `af89426`.

Resumen de mesas presidenciales por estado:

| Estado | Mesas | Electores hábiles | % del universo |
|---|---:|---:|---:|
| Contabilizadas | 91,129 | 26,826,623 | 98.24% |
| Para envío al JEE | 1,637 | 498,809 | 1.76% |
| Pendientes | 0 | 0 | 0.00% |

Desagregado territorial de mesas presidenciales para envío al JEE o pendientes:

Resumen por ámbito y región:

| Estado | Ámbito | Región | Mesas | Electores hábiles | % del universo |
|---|---|---|---:|---:|---:|
| Para envío al JEE | PERU | LIMA | 587 | 173,724 | 0.63% |
| Para envío al JEE | PERU | LORETO | 229 | 66,271 | 0.25% |
| Para envío al JEE | PERU | PIURA | 131 | 37,781 | 0.14% |
| Para envío al JEE | PERU | CUSCO | 118 | 33,858 | 0.13% |
| Para envío al JEE | PERU | UCAYALI | 66 | 18,983 | 0.07% |
| Para envío al JEE | PERU | ICA | 64 | 18,761 | 0.07% |
| Para envío al JEE | PERU | SAN MARTIN | 55 | 15,820 | 0.06% |
| Para envío al JEE | PERU | CALLAO | 44 | 13,037 | 0.05% |
| Para envío al JEE | PERU | CAJAMARCA | 43 | 12,382 | 0.05% |
| Para envío al JEE | PERU | HUANCAVELICA | 30 | 8,276 | 0.03% |
| Para envío al JEE | PERU | HUANUCO | 30 | 8,682 | 0.03% |
| Para envío al JEE | PERU | PUNO | 26 | 7,550 | 0.03% |
| Para envío al JEE | PERU | AMAZONAS | 21 | 5,639 | 0.02% |
| Para envío al JEE | PERU | APURIMAC | 17 | 4,730 | 0.02% |
| Para envío al JEE | PERU | MADRE DE DIOS | 14 | 4,144 | 0.02% |
| Para envío al JEE | PERU | AYACUCHO | 13 | 3,638 | 0.01% |
| Para envío al JEE | PERU | ANCASH | 10 | 2,963 | 0.01% |
| Para envío al JEE | PERU | AREQUIPA | 8 | 2,400 | 0.01% |
| Para envío al JEE | PERU | JUNIN | 7 | 2,045 | 0.01% |
| Para envío al JEE | PERU | LA LIBERTAD | 4 | 1,189 | 0.00% |
| Para envío al JEE | PERU | MOQUEGUA | 4 | 1,173 | 0.00% |
| Para envío al JEE | PERU | PASCO | 3 | 818 | 0.00% |
| Para envío al JEE | PERU | TACNA | 1 | 293 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | 85 | 41,701 | 0.09% |
| Para envío al JEE | EXTRANJERO | EUROPA | 22 | 10,625 | 0.02% |
| Para envío al JEE | EXTRANJERO | OCEANIA | 3 | 1,401 | 0.00% |
| Para envío al JEE | EXTRANJERO | ASIA | 2 | 925 | 0.00% |
| Pendientes | PERU | - | 0 | 0 | 0.00% |
| Pendientes | EXTRANJERO | - | 0 | 0 | 0.00% |

Ver vista renderizada: [data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.md](data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.md). CSV descargable: [data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv](data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv).

Votos válidos por organización política en mesas contabilizadas:

| Grupo | Votos válidos | % votos válidos |
|---|---:|---:|
| FUERZA POPULAR | 2,825,324 | 17.14% |
| JUNTOS POR EL PERÚ | 1,984,549 | 12.04% |
| RENOVACIÓN POPULAR | 1,960,890 | 11.89% |
| PARTIDO DEL BUEN GOBIERNO | 1,810,953 | 10.99% |
| PARTIDO CÍVICO OBRAS | 1,673,421 | 10.15% |
| Otros candidatos | 6,230,106 | 37.79% |

Blancos, nulos e impugnados suman **3,337,441** votos y no forman parte del denominador de votos válidos ONPE.

## Alcance Actual

El proyecto simplificado conserva solo el flujo operativo de datos ONPE:

- `onpe_scraper.py`: descarga, estado SQLite, rebuild de CSV y reportes básicos.
- `refresh_presidencial_only_v2.py`: refresh incremental solo de Presidencial (`idEleccion = 10`).
- `split_mesas_por_votacion.py`: split del consolidado en 5 archivos por elección.
- `update_readme_status.py`: recalcula la sección `Estado de Actualización de Datos` desde el CSV presidencial.
- `build_ausentismo_presidencial.py`: consolidación de ausentismo presidencial por mesa con fuentes históricas ONPE y datos 2026.
- `consultar_padron_mesas.py`: consulta de mesa de votación para una lista cerrada de DNIs provistos en TXT.
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
onpe-consultar-padron-mesas --help
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

### Consulta de padrón por lista cerrada de DNIs

Para consultar el número de mesa desde el endpoint público de padrón:

```bash
python3 consultar_padron_mesas.py \
  --input ./dnis.txt \
  --output ./data/output/padron_mesas.csv \
  --rps 0.5
```

El TXT debe contener un DNI de 8 dígitos por línea. El script deduplica entradas, no genera ni barre rangos y por defecto escribe sólo `dni_mask`, `dni_sha256`, estado, mesa y metadatos de consulta. Si necesitas conservar el DNI completo en el CSV, debe indicarse explícitamente:

```bash
python3 consultar_padron_mesas.py \
  --input ./dnis.txt \
  --output ./data/output/padron_mesas.csv \
  --include-dni
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
python3 update_readme_status.py
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
- [`data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv`](data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.csv): detalle territorial de mesas presidenciales `Para envío al JEE` o `Pendiente`.
- [`data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.md`](data/output/reportes/desagregado_territorial_mesas_presidencial_pendientes.md): vista renderizada del mismo detalle territorial para lectura en GitHub.
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

## Campos del CSV de Ausentismo

El archivo `data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv` contiene una fila por mesa y año para elecciones presidenciales de primera vuelta. Integra fuentes históricas oficiales de ONPE para 2006, 2011, 2016 y 2021, junto con el CSV presidencial 2026 generado por este repositorio.

Resumen ejecutivo de campos:

| Familia de campos | Columnas | Descripción para analítica |
| --- | --- | --- |
| Identificación temporal y fuente | `anio`, `fuente`, `fuente_url` | Indican el año electoral, el archivo de origen usado y, cuando corresponde, la URL oficial de referencia. Sirven para trazabilidad y reproducibilidad. |
| Identificación de mesa | `codigo_mesa` | Código de mesa normalizado como texto de seis dígitos. Debe tratarse como texto para conservar ceros a la izquierda. |
| Ubicación electoral | `ubigeo`, `departamento`, `provincia`, `distrito`, `centro_poblado`, `local_votacion` | Variables territoriales según codificación ONPE. En 2026 los nombres de departamento/provincia/distrito se derivan del catálogo ONPE histórico del repositorio cuando el mismo `ubigeo` existe. |
| Contexto electoral y estado | `tipo_eleccion`, `estado_acta`, `tipo_observacion` | Permiten filtrar por elección presidencial y separar mesas según estado o condición del acta antes de comparar tasas. |
| Totales de participación | `electores_habiles`, `votos_emitidos`, `ausentes`, `tasa_ausentismo` | Núcleo del análisis de ausentismo. `ausentes = electores_habiles - votos_emitidos`; `tasa_ausentismo = ausentes / electores_habiles`. |
| Composición del voto | `votos_validos`, `votos_blancos`, `votos_nulos`, `votos_impugnados`, `votos_no_validos` | Métricas complementarias para reconciliar participación y calidad del voto. `votos_no_validos` consolida blancos, nulos e impugnados cuando esos campos están disponibles. |

Consideraciones de uso:

- `codigo_mesa` y `ubigeo` deben leerse como texto, no como enteros.
- La codificación territorial ONPE de estos datasets no debe asumirse equivalente a INEI, RENIEC u otros catálogos externos. Por ejemplo, en estos archivos `140130` corresponde a `LIMA / LIMA / SANTIAGO DE SURCO`.
- El catálogo territorial compatible con ONPE se genera en `data/output/catalogos/ubigeo_onpe_catalog.csv` desde históricos ONPE ya presentes en el repositorio. Sus columnas son `ubigeo`, `departamento`, `provincia`, `distrito`, `fuente_anios` y `n_observaciones`.
- `data_dictionary/ubigeo/departamentos.csv` no debe usarse para etiquetar estos outputs ONPE salvo demostración explícita de compatibilidad; en ese catálogo externo `14` no representa la misma codificación que el `14` observado en los JSON ONPE 2026 del repo.
- La comparabilidad territorial debe hacerse preferentemente por `ubigeo`; los nombres de departamento, provincia y distrito pueden variar entre años o no estar disponibles con el mismo nivel de detalle. Si un `ubigeo` 2026 no existe en el histórico ONPE usado como fuente de verdad, queda marcado como `NO_RESUELTO_ONPE` en lugar de recibir un fallback externo.
- Algunas filas pueden tener campos centrales vacíos si el acta no cuenta con cómputo completo en la fuente disponible. Se conservan para preservar cobertura y trazabilidad.
- Antes de calcular tendencias, conviene filtrar o segmentar por `estado_acta`, porque mezclar actas contabilizadas con actas pendientes u observadas puede distorsionar la tasa de ausentismo.
- Para 2026, el consolidado depende del último refresh, rebuild y split ejecutado; si cambia `mesas_presidencial.csv`, debe regenerarse este archivo.
- La validación operativa del mapeo se ejecuta con `python3 validate_ubigeo_onpe_mapping.py`; verifica, entre otros casos, que la mesa `050915` quede asociada a `ubigeo=140130`, `LIMA`, `LIMA`, `SANTIAGO DE SURCO`.

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
python3 update_readme_status.py
```

## Nota Sobre Código Legado

El directorio `src/fraud_detector` y sus pruebas pertenecen a una línea de trabajo anterior: detección estadística, snapshots, Postgres y rankings de anomalía. No forma parte del flujo operativo simplificado.

Se deja en el repositorio solo como referencia histórica mientras se decide si se elimina, se archiva o se mueve a otro proyecto.
