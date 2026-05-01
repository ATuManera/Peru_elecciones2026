# Estructura del Reporte Final

## Principio rector

El reporte final deberá comunicar resultados de forma clara, sobria y auditable. Todo resultado de impacto en votos deberá presentarse como estimación contrafactual bajo supuestos explícitos, no como evidencia de manipulación electoral.

## 1. Resumen Ejecutivo

Propósito:

- Resumir hallazgos principales sin lenguaje acusatorio.
- Explicar si 2026 presenta señales de ausentismo superiores al baseline bajo escenarios específicos.
- Indicar sensibilidad de resultados.

Tablas requeridas:

- Resumen de tasas de ausentismo por año.
- Resumen de exceso estimado por baseline.
- Rango de impacto contrafactual por modelo.

Gráficos requeridos:

- Serie histórica de tasa nacional de ausentismo.
- Barra de escenarios principales de exceso de ausentes.

Caveats:

- Los resultados dependen del baseline y de filtros de estado de acta.
- El impacto en votos es contrafactual.

Límites de interpretación:

- No afirmar fraude, manipulación ni causalidad.

## 2. Alcance y Disclaimer

Propósito:

- Delimitar qué evalúa y qué no evalúa el reporte.
- Incluir advertencia metodológica obligatoria.

Texto obligatorio:

```text
Estos resultados son estimaciones contrafactuales bajo supuestos explícitos. No constituyen evidencia de manipulación electoral, fraude ni causalidad. Su propósito es analítico y exploratorio.
```

Tablas requeridas:

- Ninguna obligatoria.

Gráficos requeridos:

- Ninguno obligatorio.

Caveats:

- El reporte no reemplaza fuentes oficiales ni auditorías electorales formales.

## 3. Fuentes de Datos

Propósito:

- Documentar rutas, años, granularidad y origen.
- Permitir reproducibilidad.

Tablas requeridas:

- Inventario de datasets.
- Checksums de archivos principales.
- Conteo de filas por archivo.

Gráficos requeridos:

- Diagrama simple de flujo de datos.

Caveats:

- Los datos 2026 pueden cambiar con refresh/rebuild/split.

## 4. Calidad y Comparabilidad de Datos

Propósito:

- Presentar resultados de validaciones.
- Discutir comparabilidad entre años.

Tablas requeridas:

- Checks de duplicados, faltantes e inconsistencias.
- Estados de acta por año.
- Campos comparables y no comparables.

Gráficos requeridos:

- Barras de cobertura por año.
- Heatmap opcional de disponibilidad de campos.

Caveats:

- 2006 requiere normalización de UBIGEO.
- 2021 puede tener condiciones contextuales atípicas.

Límites de interpretación:

- Diferencias de estructura no implican irregularidades.

## 5. Metodología

Propósito:

- Explicar baseline, unidad de análisis, fórmulas y criterios de flags.

Tablas requeridas:

- Comparación de baselines.
- Fórmulas y variables.
- Umbrales de flags.

Gráficos requeridos:

- Esquema de pipeline analítico.

Caveats:

- Los flags son señales estadísticas para revisión.

## 6. Baseline Histórico de Ausentismo

Propósito:

- Mostrar comportamiento histórico esperado.

Tablas requeridas:

- Tasa nacional por año.
- Baseline por UBIGEO.
- Distribución de tasas históricas.

Gráficos requeridos:

- Línea histórica nacional.
- Boxplots o violines por año.
- Mapa histórico por UBIGEO si es viable.

Caveats:

- La comparabilidad de mesa a mesa es limitada.

## 7. Evaluación de Ausentismo 2026

Propósito:

- Comparar 2026 contra baselines definidos.

Tablas requeridas:

- Exceso por UBIGEO.
- Top unidades por exceso absoluto y relativo.
- Flags por umbral.

Gráficos requeridos:

- Histograma de exceso relativo.
- Mapa de exceso por UBIGEO.
- Ranking de contribuciones.

Caveats:

- Separar estados de acta si no todos están contabilizados.

Límites de interpretación:

- Exceso estadístico no prueba intencionalidad.

## 8. Concentración Geográfica

Propósito:

- Evaluar si el exceso estimado está concentrado territorialmente.

Tablas requeridas:

- Exceso por departamento/provincia/UBIGEO.
- Porcentaje del exceso total explicado por top unidades.

Gráficos requeridos:

- Mapa coroplético.
- Curva de concentración acumulada.
- Barras top 20 UBIGEO.

Caveats:

- Concentración puede explicarse por demografía, logística o contexto local.

## 9. Escenarios Contrafactuales de Impacto en Votos

Propósito:

- Estimar cómo se distribuirían votos hipotéticos bajo modelos explícitos.

Tablas requeridas:

- Impacto por candidato y modelo.
- Totales observados vs ajustados contrafactuales.
- Diferencias de ranking bajo cada escenario.

Gráficos requeridos:

- Barras de impacto por candidato.
- Intervalos por escenario.
- Comparación de ranking observado vs contrafactual.

Caveats:

- Los votos imputados no son votos observados.
- El modelo de asignación determina el resultado.

Límites de interpretación:

- No declarar cambio real de resultado electoral.

## 10. Análisis de Sensibilidad

Propósito:

- Mostrar robustez o fragilidad de resultados.

Tablas requeridas:

- Sensibilidad por baseline.
- Sensibilidad por modelo de imputación.
- Sensibilidad por umbral.
- Sensibilidad con y sin 2006/2021.

Gráficos requeridos:

- Tornado chart de sensibilidad.
- Matriz baseline vs modelo.
- Rangos de impacto por candidato.

Caveats:

- Si los resultados cambian fuertemente entre escenarios, la conclusión debe ser cautelosa.

## 11. Limitaciones

Propósito:

- Explicitar restricciones de datos, modelos y alcance.

Temas mínimos:

- Comparabilidad histórica imperfecta.
- Cambios en partidos y candidatos.
- Posible atipicidad de 2021.
- Normalización de UBIGEO 2006.
- Diferencias de estado de acta.
- Ausentes no observados: preferencias desconocidas.

Tablas requeridas:

- Lista de limitaciones y mitigaciones.

Gráficos requeridos:

- Ninguno obligatorio.

## 12. Conclusiones

Propósito:

- Responder la pregunta de investigación con lenguaje calibrado.

Debe incluir:

- Resultado descriptivo principal.
- Rango de escenarios.
- Robustez o sensibilidad.
- Recomendaciones de revisión adicional.

No debe incluir:

- Acusaciones.
- Conclusiones determinísticas.
- Afirmaciones de causalidad no identificada.

## 13. Apéndice de Reproducibilidad

Propósito:

- Permitir replicar el análisis completo.

Contenido requerido:

- Commit.
- Checksums.
- Rutas de entrada.
- Parámetros.
- Filtros.
- Versiones de herramientas.
- Semillas de simulación.
- Diccionario de outputs.

Tablas requeridas:

- Manifiesto de ejecución.
- Parámetros de modelos.
- Lista de archivos generados.

Gráficos requeridos:

- Ninguno obligatorio.
