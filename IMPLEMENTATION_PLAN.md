# Plan de Implementación

## Alcance

Este documento describe cómo implementar el análisis en una fase posterior. No incluye código. La implementación deberá producir resultados auditables, reproducibles y acompañados de supuestos explícitos. Todo impacto de voto será contrafactual y no deberá interpretarse como evidencia de manipulación electoral.

## 1. Vista general del pipeline

```text
Fuentes ONPE históricas + outputs 2026
        ↓
Validación de archivos y checksums
        ↓
Normalización de campos
        ↓
Construcción de tabla analítica
        ↓
Construcción de baselines históricos
        ↓
Detección de exceso de ausentismo
        ↓
Modelos contrafactuales de imputación de votos
        ↓
Sensibilidad e incertidumbre
        ↓
Tablas, gráficos y reporte final
```

## 2. Entradas

Archivos principales:

- `data/output/ausentismo/mesas_ausentismo_presidencial_2006_2026.csv`
- `data/output/por_votacion/mesas_presidencial.csv`
- `data/input/onpe_historico/presidencial_primera_vuelta/2006_EG2006_Presidencial.csv`
- `data/input/onpe_historico/presidencial_primera_vuelta/2011_EG2011_Presidencial_0.zip`
- `data/input/onpe_historico/presidencial_primera_vuelta/2016_EG2016_Presidencial.csv`
- `data/input/onpe_historico/presidencial_primera_vuelta/2021_Resultados_1ra_vuelta_Version_PCM.csv`
- Diccionarios `*.xlsx` en `data/input/onpe_historico/presidencial_primera_vuelta/`

## 3. Capa de validación

Validaciones mínimas:

- Existencia de archivos esperados.
- Checksum SHA-256 de cada input.
- Conteo de filas por año.
- Validación de columnas obligatorias.
- Duplicados por `anio`, `codigo_mesa`.
- `codigo_mesa` como texto de seis dígitos.
- `ubigeo` como texto normalizado de seis dígitos cuando aplique.
- `electores_habiles >= votos_emitidos`.
- `ausentes = electores_habiles - votos_emitidos`.
- `0 <= tasa_ausentismo <= 1`.
- Reconciliación de votos válidos, blancos, nulos e impugnados contra votos emitidos.
- Estados de acta disponibles y distribución por año.

Salida sugerida:

- `data/output/auditoria_ausentismo/audit_checks.csv`
- `data/output/auditoria_ausentismo/audit_summary.json`

## 4. Transformaciones de datos

### Normalización de campos

Crear una tabla analítica con campos estándar:

- `anio`
- `codigo_mesa`
- `ubigeo`
- `departamento`
- `provincia`
- `distrito`
- `estado_acta`
- `electores_habiles`
- `votos_emitidos`
- `ausentes`
- `tasa_ausentismo`
- `votos_validos`
- `votos_blancos`
- `votos_nulos`
- `votos_impugnados`
- `votos_no_validos`

### Normalización de mesa

Reglas:

- Convertir a texto.
- Remover espacios.
- Rellenar con ceros a la izquierda hasta seis dígitos cuando el valor sea numérico.
- Mantener valor original en una columna auxiliar si se requiere auditoría.

### Normalización de UBIGEO

Reglas:

- Convertir a texto.
- Remover espacios.
- Si es numérico y tiene menos de seis dígitos, evaluar `zfill(6)`.
- Validar contra diccionario territorial si está disponible.
- Marcar casos no normalizables, especialmente en 2006.

### Estados de acta

Crear una clasificación operacional:

- `contabilizada_normal`
- `resuelta`
- `anulada`
- `sin_instalar`
- `en_proceso`
- `otro`

La clasificación debe conservar el texto original y no reemplazarlo.

### Manejo de faltantes

Reglas:

- No imputar electores hábiles ni votos emitidos en la capa de auditoría.
- Excluir de inferencia primaria unidades sin núcleo completo.
- Reportar cobertura perdida por año y estado.
- Mantener filas incompletas en anexos de auditoría.

## 5. Construcción de baselines

Baselines a producir:

- `baseline_short_2011_2016`
- `baseline_long_2006_2011_2016`
- `baseline_recent_2016_2021`
- `baseline_robust_median_mad`

Unidad primaria:

- UBIGEO/distrito.

Unidad secundaria:

- Mesa, solo para descomposición, ranking y exploración.

Medidas:

- `tasa_esperada`
- `ausentes_esperados`
- `exceso_ausentes`
- `exceso_relativo`
- `z_score`
- `robust_z`
- `flag_mad`
- `flag_percentil`

## 6. Modelo de detección de señales

Estructura:

1. Calcular tasa 2026 por unidad.
2. Calcular tasa esperada según baseline.
3. Calcular exceso absoluto y relativo.
4. Calcular indicadores estandarizados.
5. Asignar flags de revisión.
6. Agregar resultados por departamento/provincia/UBIGEO.

Los flags deberán presentarse como señales estadísticas para revisión, no como hallazgos de irregularidad.

## 7. Modelos contrafactuales de impacto de votos

### Modelo A: distribución nacional

Entradas:

- Exceso total de ausentes.
- Participación nacional observada de cada candidatura en 2026.

Salida:

- Votos contrafactuales por candidato.
- Escenario de totales ajustados.

### Modelo B: distribución UBIGEO

Entradas:

- Exceso de ausentes por UBIGEO.
- Participación observada por candidato en el mismo UBIGEO.

Salida:

- Votos imputados por candidato y UBIGEO.
- Agregado nacional.

### Modelo C: distritos emparejados

Entradas:

- Variables de similitud territorial y electoral.
- Exceso de ausentes por UBIGEO.
- Votos observados en unidades comparables.

Salida:

- Votos imputados por candidato.
- Calidad de matching.
- Sensibilidad a número de vecinos o ponderaciones.

## 8. Incertidumbre

Implementar escenarios:

- Conservador.
- Central.
- Alto impacto.

Implementar sensibilidad por:

- Baseline.
- Inclusión/exclusión de 2006.
- Inclusión/exclusión de 2021.
- Filtro de estados de acta.
- Umbral de flag.
- Modelo de imputación.

Monte Carlo opcional:

- Definir semilla determinística.
- Simular tasas esperadas e imputación de votos.
- Reportar intervalos percentiles 5, 50 y 95.

## 9. Salidas esperadas

Archivos sugeridos:

| Archivo | Contenido |
| --- | --- |
| `data/output/analisis_ausentismo/absenteeism_by_mesa.csv` | Métricas de ausentismo por mesa-año. |
| `data/output/analisis_ausentismo/absenteeism_by_ubigeo.csv` | Métricas agregadas por UBIGEO-año. |
| `data/output/analisis_ausentismo/baselines_by_ubigeo.csv` | Tasas esperadas por baseline. |
| `data/output/analisis_ausentismo/excess_absenteeism_flags.csv` | Flags de exceso y métricas estandarizadas. |
| `data/output/analisis_ausentismo/geographic_concentration.csv` | Concentración por departamento/provincia/UBIGEO. |
| `data/output/analisis_ausentismo/candidate_impact_scenarios.csv` | Impacto contrafactual por candidato y escenario. |
| `data/output/analisis_ausentismo/sensitivity_summary.csv` | Resumen de sensibilidad. |
| `data/output/analisis_ausentismo/audit_checks.csv` | Resultados de validación. |

Documentos:

- `FINAL_REPORT.md`
- Anexo metodológico con parámetros.
- Anexo de reproducibilidad.

## 10. Reproducibilidad

Cada ejecución debe registrar:

- Commit del repositorio.
- Fecha y hora de ejecución.
- Checksums de inputs.
- Parámetros usados.
- Filtros aplicados.
- Versiones de Python y librerías.
- Semilla determinística si hay simulación.
- Rutas exactas de inputs y outputs.

## 11. Criterios de aceptación

La implementación futura será aceptable solo si:

- Reproduce los conteos base del reporte de auditoría.
- No mezcla estados de acta incompatibles sin documentarlo.
- Permite replicar cada tabla final desde inputs identificados.
- No emite afirmaciones acusatorias.
- Presenta resultados como rangos o escenarios, no como verdades determinísticas.
