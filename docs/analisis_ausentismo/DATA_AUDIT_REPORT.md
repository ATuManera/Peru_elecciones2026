# Reporte de Auditoría de Datos

## Alcance

Este reporte documenta una inspección de solo lectura de los datos disponibles en el repositorio para diseñar un análisis de ausentismo electoral presidencial. No contiene conclusiones de fraude, manipulación ni intencionalidad. Cualquier análisis posterior sobre impacto en votos deberá interpretarse como estimación contrafactual bajo supuestos explícitos, no como evidencia de manipulación electoral.

Commit auditado:

```text
36751e349ee44fe703c71672d4bbe2acba11cf0b
```

## 1. Inventario de datasets

| Dataset | Ruta | Años | Tipo | Granularidad | Observaciones |
| --- | --- | --- | --- | --- | --- |
| Consolidado de ausentismo presidencial | `data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv` | 2006, 2011, 2016, 2021, 2026 | Generado | Mesa-año | Dataset normalizado principal para análisis de ausentismo. |
| Presidencial 2026 | `data/output/por_votacion/mesas_presidencial.csv` | 2026 | Generado desde JSON ONPE | Mesa | Detalle presidencial 2026, con votos por organización, totales y estado del acta. |
| Consolidado ONPE 2026 | `data/output/mesas_consolidado.csv` | 2026 | Generado desde JSON ONPE | Mesa-elección | Incluye las cinco elecciones separables por `idEleccion`. |
| Histórico presidencial 2006 | `data/input/onpe_historico/presidencial_primera_vuelta/2006_EG2006_Presidencial.csv` | 2006 | Fuente histórica ONPE | Mesa | CSV de resultados presidenciales de primera vuelta. |
| Histórico presidencial 2011 | `data/input/onpe_historico/presidencial_primera_vuelta/2011_EG2011_Presidencial_0.zip` | 2011 | Fuente histórica ONPE | Mesa | ZIP con `2011_EG2011_Presidencial.xlsx`. |
| Histórico presidencial 2016 | `data/input/onpe_historico/presidencial_primera_vuelta/2016_EG2016_Presidencial.csv` | 2016 | Fuente histórica ONPE | Mesa | CSV de resultados presidenciales de primera vuelta. |
| Histórico presidencial 2021 | `data/input/onpe_historico/presidencial_primera_vuelta/2021_Resultados_1ra_vuelta_Version_PCM.csv` | 2021 | Fuente histórica ONPE | Mesa | CSV de resultados presidenciales de primera vuelta. |
| Diccionarios históricos | `data/input/onpe_historico/presidencial_primera_vuelta/*Diccionario*.xlsx` | 2006, 2011, 2016, 2021 | Diccionario ONPE | Variable | Describen variables históricas y códigos de observación cuando están disponibles. |
| Manifiesto de descarga 2026 | `data/manifests/download_manifest.csv` | 2026 | Generado | Mesa | Inventario operativo de descargas. |
| Resumen de refresh presidencial | `data/reports/refresh_presidencial_summary.csv` | 2026 | Generado | Mesa modificada | Último reporte de cambios detectados en refresh presidencial. |

Fuente oficial declarada para históricos:

```text
https://www.onpe.gob.pe/elecciones/historico-elecciones/
```

## 2. Revisión de esquemas

### Campos históricos comunes

Los archivos históricos 2006, 2011, 2016 y 2021 comparten una estructura base:

| Concepto | Campo histórico |
| --- | --- |
| Ubigeo | `UBIGEO` |
| Departamento | `DEPARTAMENTO` |
| Provincia | `PROVINCIA` |
| Distrito | `DISTRITO` |
| Tipo de elección | `TIPO_ELECCION` |
| Mesa | `MESA_DE_VOTACION` |
| Estado de acta | `DESCRIP_ESTADO_ACTA` |
| Observación | `TIPO_OBSERVACION` |
| Votos emitidos | `N_CVAS` |
| Electores hábiles | `N_ELEC_HABIL` |
| Votos por candidatura | `VOTOS_P1`, `VOTOS_P2`, ... |
| Votos blancos | `VOTOS_VB` |
| Votos nulos | `VOTOS_VN` |
| Votos impugnados | `VOTOS_VI` |

Cantidad de columnas inspeccionadas:

| Año | Formato | Columnas | Columnas de candidatura |
| --- | --- | ---: | ---: |
| 2006 | CSV | 33 | 20 |
| 2011 | XLSX dentro de ZIP | 24 | 11 |
| 2016 | CSV | 27 | 14 |
| 2021 | CSV | 31 | 18 |

### Campos 2026

El archivo `data/output/por_votacion/mesas_presidencial.csv` contiene 306 columnas. Entre las columnas principales están:

- Identificación: `codigoMesa`, `id`, `idEleccion`.
- Ubicación: `ubigeoNivel01`, `ubigeoNivel02`, `ubigeoNivel03`, `centroPoblado`, `nombreLocalVotacion`.
- Totales: `totalElectoresHabiles`, `totalVotosEmitidos`, `totalVotosValidos`.
- Estado: `estadoActa`, `estadoComputo`, `codigoEstadoActa`, `descripcionEstadoActa`.
- Detalle de votos: `detalle_1_*` a `detalle_38_*`, más `detalle_80_*`, `detalle_81_*`, `detalle_82_*`.
- Línea de tiempo: `lineaTiempo_1_*` a `lineaTiempo_31_*`.

### Equivalencias para análisis de ausentismo

| Concepto normalizado | Históricos | 2026 | Consolidado de ausentismo |
| --- | --- | --- | --- |
| Año electoral | Derivado del archivo | Fijo 2026 | `anio` |
| Mesa | `MESA_DE_VOTACION` | `codigoMesa` | `codigo_mesa` |
| Ubigeo | `UBIGEO` | `ubigeoNivel03` | `ubigeo` |
| Electores hábiles | `N_ELEC_HABIL` | `totalElectoresHabiles` | `electores_habiles` |
| Votos emitidos | `N_CVAS` | `totalVotosEmitidos` | `votos_emitidos` |
| Votos válidos | Suma de `VOTOS_P*` | `totalVotosValidos` | `votos_validos` |
| Blancos | `VOTOS_VB` | `detalle_80_nvotos` | `votos_blancos` |
| Nulos | `VOTOS_VN` | `detalle_81_nvotos` | `votos_nulos` |
| Impugnados | `VOTOS_VI` | `detalle_82_nvotos` | `votos_impugnados` |
| Estado de acta | `DESCRIP_ESTADO_ACTA` | `descripcionEstadoActa` | `estado_acta` |

## 3. Controles de calidad observados

Resumen del consolidado de ausentismo:

| Año | Filas | Filas con núcleo completo | Electores hábiles | Votos emitidos | Ausentes | Tasa global de ausentismo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2006 | 88,481 | 88,481 | 16,494,906 | 14,632,003 | 1,862,903 | 11.2938% |
| 2011 | 107,455 | 107,455 | 19,949,915 | 16,699,734 | 3,250,181 | 16.2917% |
| 2016 | 77,307 | 77,307 | 22,901,954 | 18,734,130 | 4,167,824 | 18.1986% |
| 2021 | 86,488 | 85,989 | 25,141,212 | 17,713,716 | 7,427,496 | 29.5431% |
| 2026 | 87,771 | 87,771 | 25,748,032 | 19,120,194 | 6,627,838 | 25.7411% |

Controles de calidad inspeccionados:

| Control | Resultado observado |
| --- | --- |
| Duplicados por `anio` + `codigo_mesa` | No se detectaron duplicados en el consolidado de ausentismo. |
| `codigo_mesa` faltante o malformado | No se detectaron faltantes ni códigos malformados en el consolidado. |
| `UBIGEO` faltante | No se detectaron faltantes en el consolidado. |
| `UBIGEO` malformado | Se detectaron 20,900 filas 2006 con UBIGEO de cinco dígitos, principalmente compatibles con pérdida de cero inicial. Requiere normalización y validación antes de comparar territorialmente. |
| Ausentismo negativo | No se detectaron casos. |
| `votos_emitidos > electores_habiles` | No se detectaron casos. |
| `ausentes = electores_habiles - votos_emitidos` | No se detectaron inconsistencias en filas con núcleo completo. |
| Reconciliación de votos | No se detectaron discrepancias entre votos válidos + no válidos y votos emitidos en filas con campos disponibles. |
| Núcleo incompleto | 499 filas en 2021 tienen núcleo incompleto, asociadas a estados como `SIN INSTALAR`. |

Estados de acta observados por año:

| Año | Estados principales |
| --- | --- |
| 2006 | `CONTABILIZADAS NORMALES` 87,336; `CONTABILIZADAS ANULADAS` 1,126; `MESA NO INSTALADA` 19 |
| 2011 | `ACTA ELECTORAL NORMAL` 103,200; `ACTA ELECTORAL RESUELTA` 4,208; `MESA NO INSTALADA` 47 |
| 2016 | `ACTA ELECTORAL NORMAL` 73,547; `ACTA ELECTORAL RESUELTA` 3,734; `MESA NO INSTALADA` 26 |
| 2021 | `CONTABILIZADA` 81,924; `COMPUTADA RESUELTA` 3,081; `ANULADA` 949; `SIN INSTALAR` 499; otros menores |
| 2026 | `Contabilizada` 87,771 |

## 4. Evaluación de comparabilidad

### Comparabilidad de 2006

El año 2006 aporta una base histórica valiosa, pero no debe tratarse como perfectamente comparable sin controles adicionales:

- Presenta 20,900 filas con `UBIGEO` no estándar de cinco dígitos.
- Tiene 20 columnas de candidatura, frente a 11 en 2011, 14 en 2016, 18 en 2021 y 38 en 2026.
- Usa etiquetas de estado distintas, por ejemplo `CONTABILIZADAS NORMALES`.
- El volumen de mesas y la estructura operativa difieren de años posteriores.

Recomendación: usar 2006 como baseline largo o prueba de robustez, no como componente principal del baseline primario sin normalización de UBIGEO y análisis de sensibilidad.

### Comparabilidad de 2021

2021 tiene condiciones contextuales extraordinarias y 499 filas sin núcleo completo. Puede ser informativo como baseline reciente, pero debe analizarse con sensibilidad separada. No conviene mezclarlo sin advertencia con 2011 y 2016 si el objetivo es estimar un patrón histórico operativo estable.

### Comparabilidad de 2026

El estado actual de `data/output/por_votacion/mesas_presidencial.csv` muestra 87,771 filas presidenciales, todas con `descripcionEstadoActa = Contabilizada`. Aun así, el repositorio documenta un flujo de refresh incremental, por lo que versiones anteriores o futuras del archivo podrían depender de estados de acta, fecha de actualización y commit.

## 5. Estado de datos 2026

En el corte auditado:

- Filas presidenciales 2026: 87,771.
- Estado de acta: 100% `Contabilizada`.
- Totales faltantes en presidencial 2026: 0.
- El reporte `data/reports/refresh_presidencial_summary.csv` contiene 263 filas de cambios más encabezado.

Recomendaciones:

- Registrar commit y checksums antes de ejecutar inferencia.
- Si aparece más de un estado de acta en cortes posteriores, estratificar por `estado_acta` antes de inferir exceso de ausentismo.
- No comparar mesas pendientes, anuladas o sin instalar contra mesas contabilizadas sin modelar esa diferencia.

## 6. Notas de auditabilidad

Checksums SHA-256 de archivos principales:

| Archivo | SHA-256 |
| --- | --- |
| `data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv` | `8ac800a890c8dc25286e267195683e58fed130fbdbb2348aa884062f05c90827` |
| `data/output/por_votacion/mesas_presidencial.csv` | `9526347f86b3cd58db06aeae804f66391ed997f92122e12d2383f0190bf2e3d1` |
| `data/input/onpe_historico/presidencial_primera_vuelta/2006_EG2006_Presidencial.csv` | `ac7fb25f56cfe637c91c4bca0b3bc4ce7d7460a02dcd2223ace8c1b754d69227` |
| `data/input/onpe_historico/presidencial_primera_vuelta/2011_EG2011_Presidencial_0.zip` | `cd6aee7a9fa7d41a97890c99c83d8957fc031273e962cbd6ceea97704293afc4` |
| `data/input/onpe_historico/presidencial_primera_vuelta/2016_EG2016_Presidencial.csv` | `e9134dbe2650057b71af5792e2294c0582d0621dd7bd8cc65ca9a032652bbaf8` |
| `data/input/onpe_historico/presidencial_primera_vuelta/2021_Resultados_1ra_vuelta_Version_PCM.csv` | `f325f303615b02ea746217e312be1b78e07c61c82149fec27a7ec0021d0a3047` |

Requisitos mínimos de reproducibilidad para cualquier análisis posterior:

- Registrar commit exacto del repositorio.
- Registrar checksums de datasets usados.
- Registrar fecha y hora de refresh/rebuild/split si se actualiza 2026.
- Registrar parámetros de baseline, filtros de estados de acta y reglas de imputación.
- Mantener salidas intermedias de auditoría para revisión externa.
