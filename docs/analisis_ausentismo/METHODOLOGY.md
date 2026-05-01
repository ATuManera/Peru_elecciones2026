# Metodología Propuesta

## Declaración de alcance

Esta metodología está diseñada para evaluar ausentismo electoral y escenarios contrafactuales de impacto en distribución de votos. No asume fraude, manipulación, supresión, intencionalidad ni conducta irregular. Cualquier estimación de votos debe interpretarse como resultado contrafactual bajo supuestos explícitos, no como evidencia de manipulación electoral.

## 1. Pregunta de investigación

Pregunta central:

```text
¿La elección presidencial de primera vuelta 2026 muestra exceso de ausentismo estadísticamente significativo respecto de patrones históricos comparables, y cuál sería el impacto contrafactual sobre la distribución de votos bajo distintos supuestos de asignación?
```

Subpreguntas:

- ¿El ausentismo 2026 supera el ausentismo esperado por mesa, UBIGEO o unidad territorial comparable?
- ¿El exceso se concentra geográficamente o aparece distribuido de manera amplia?
- ¿Qué tan sensibles son los resultados al baseline histórico usado?
- ¿Qué tan sensibles son los escenarios de impacto a la regla de imputación de votos?

## 2. Definiciones de baseline

### Baseline corto: 2011 y 2016

Racionalidad:

- Usa años previos con estructura moderna relativamente comparable.
- Excluye 2006 por problemas de normalización territorial y excluye 2021 por contexto extraordinario.

Fortalezas:

- Mejor comparabilidad operativa que 2006.
- Evita que 2021 eleve artificialmente el ausentismo esperado.
- Útil como baseline principal conservador para identificar cambios respecto de patrones prepandemia.

Debilidades:

- Solo dos observaciones históricas por unidad.
- Baja capacidad para estimar dispersión local.
- Puede no capturar tendencias estructurales de largo plazo.

Uso recomendado:

- Baseline principal para estimación central, combinado con análisis robusto y sensibilidad.

### Baseline largo: 2006, 2011 y 2016

Racionalidad:

- Amplía historia prepandemia.
- Permite observar una trayectoria más larga.

Fortalezas:

- Mayor horizonte temporal.
- Reduce dependencia de solo dos elecciones.

Debilidades:

- 2006 tiene problemas de UBIGEO no estándar y diferencias de estructura.
- Cambios demográficos, administrativos y de mesa pueden afectar comparabilidad.

Uso recomendado:

- Prueba de robustez, no baseline primario sin normalización validada.

### Baseline reciente: 2016 y 2021

Racionalidad:

- Incluye el año más reciente antes de 2026.
- Puede capturar cambios contemporáneos de participación.

Fortalezas:

- Mayor cercanía temporal.
- Útil para evaluar si 2026 revierte, continúa o se aparta del patrón observado en 2021.

Debilidades:

- 2021 puede reflejar condiciones contextuales extraordinarias.
- Puede elevar el ausentismo esperado y reducir la detección de exceso 2026.

Uso recomendado:

- Escenario alternativo y sensibilidad, no baseline único.

### Baseline robusto: mediana y MAD

Racionalidad:

- Usa una medida resistente a valores extremos.
- Reduce impacto de años atípicos o unidades con variabilidad alta.

Definiciones:

```text
baseline_robusto_u = mediana(tasa_ausentismo_u,años_históricos)
MAD_u = mediana(|tasa_ausentismo_u,año - baseline_robusto_u|)
```

Fortalezas:

- Menos sensible a 2021 si se incluye.
- Adecuado para generación de flags de revisión.

Debilidades:

- Con pocos años, la estimación de MAD puede ser inestable o cero.
- Requiere reglas para empates, MAD cero y datos faltantes.

Uso recomendado:

- Método principal de señalización de anomalías, junto con baseline corto como referencia central.

### Recomendación

Usar un enfoque híbrido:

1. Estimación central: baseline corto 2011-2016 a nivel UBIGEO.
2. Señalización robusta: mediana + MAD con 2011, 2016 y, como sensibilidad, 2006 y 2021.
3. Sensibilidad obligatoria: repetir resultados con baseline largo y baseline reciente.

## 3. Unidad de análisis

### Mesa

Ventajas:

- Máxima granularidad.
- Permite identificar concentración puntual.
- Conserva detalle operativo.

Limitaciones:

- Las mesas no necesariamente son estables entre años.
- Cambios en tamaño de mesa, electorado y composición territorial pueden hacer riesgosa la comparación directa mesa-a-mesa.

### UBIGEO o distrito

Ventajas:

- Mayor estabilidad territorial que la mesa.
- Facilita comparación histórica.
- Reduce ruido idiosincrático de mesas pequeñas.

Limitaciones:

- Puede ocultar patrones intra-distritales.
- Requiere normalización cuidadosa de UBIGEO, especialmente para 2006.

### Enfoque híbrido

Recomendación:

- Unidad primaria: UBIGEO/distrito.
- Unidad secundaria: mesa, para descomposición y ranking de contribución al exceso.

Justificación:

El objetivo principal es comparar 2026 con patrones históricos. El UBIGEO ofrece una base territorial más comparable. La mesa debe usarse para granularidad posterior, pero no como única base de inferencia histórica.

## 4. Métricas de ausentismo

Para unidad `u` y año `t`:

```text
electores_habiles_u,t = total de ciudadanos habilitados para votar
votos_emitidos_u,t = total de votos emitidos o cédulas válidas para cómputo de participación
ausentes_u,t = electores_habiles_u,t - votos_emitidos_u,t
tasa_ausentismo_u,t = ausentes_u,t / electores_habiles_u,t
```

Ausentismo esperado:

```text
tasa_esperada_u,2026 = baseline histórico de tasa_ausentismo para unidad u
ausentes_esperados_u,2026 = electores_habiles_u,2026 * tasa_esperada_u,2026
```

Exceso absoluto de ausentismo:

```text
exceso_ausentes_u = ausentes_observados_u,2026 - ausentes_esperados_u,2026
```

Exceso relativo:

```text
exceso_relativo_u = tasa_ausentismo_u,2026 - tasa_esperada_u,2026
```

Exceso estandarizado:

```text
z_u = (tasa_ausentismo_u,2026 - media_histórica_u) / desviación_histórica_u
robust_z_u = (tasa_ausentismo_u,2026 - mediana_histórica_u) / (1.4826 * MAD_u)
```

Reglas:

- Si `MAD_u = 0`, usar umbral mínimo de escala o clasificar como no evaluable para robust z.
- No permitir `exceso_ausentes_u < 0` en modelos de impacto; registrar valores negativos como menor ausentismo observado, no como votos adicionales.

## 5. Detección de señales de ausentismo inusual

Métodos propuestos:

| Método | Uso | Interpretación |
| --- | --- | --- |
| Exceso absoluto | Cuantificar número de ausentes sobre esperado | Magnitud operativa |
| Exceso relativo | Comparar tasas entre unidades | Intensidad proporcional |
| z-score | Señal bajo supuestos aproximadamente normales | Usar con cautela por pocos años |
| MAD robusto | Señal resistente a outliers | Preferido para flags |
| Percentiles | Identificar cola superior | Útil para mapas/rankings |
| Concentración geográfica | Evaluar clustering territorial | Señal descriptiva, no prueba causal |

Umbrales sugeridos para revisión:

- `robust_z >= 3.5` como flag fuerte.
- Percentil 95 o 99 de exceso relativo como flag exploratorio.
- Top contribuciones por exceso absoluto para priorizar revisión.

Estos umbrales son banderas de revisión estadística. No prueban fraude, manipulación ni intencionalidad.

## 6. Modelos contrafactuales de impacto en votos

El impacto estimado parte de una pregunta contrafactual:

```text
Si el exceso de ausentismo estimado hubiera votado, ¿cómo se habrían distribuido esos votos bajo una regla explícita de imputación?
```

### Modelo A: distribución nacional

Asignación:

```text
votos_imputados_c = exceso_ausentes_total * participación_nacional_c,2026
```

Supuestos:

- Los ausentes excedentes habrían votado como el promedio nacional observado.
- No existe sesgo geográfico o partidario en la abstención excedente.

Sesgos:

- Ignora heterogeneidad territorial.
- Puede diluir efectos locales.
- Tiende a ser conservador para cambios geográficamente concentrados.

### Modelo B: distribución distrital/UBIGEO

Asignación:

```text
votos_imputados_c,u = exceso_ausentes_u * participación_c,u,2026
```

Alternativas:

- Usar distribución observada 2026 en el mismo UBIGEO.
- Usar distribución histórica local cuando exista una correspondencia defendible.

Supuestos:

- Los ausentes excedentes de una unidad habrían votado como los votantes observados de esa misma unidad.

Sesgos:

- Si la abstención excedente está correlacionada con preferencia política, puede subestimar o sobreestimar impacto.
- Requiere suficiente volumen de votos observados por unidad.

### Modelo C: distritos emparejados

Emparejamiento:

- Tasa histórica de ausentismo.
- Tamaño del electorado.
- Región/departamento.
- Perfil urbano/rural aproximado si está disponible.
- Distribución de votos observada.
- Tendencia histórica de participación.

Asignación:

```text
votos_imputados_c,u = exceso_ausentes_u * promedio_ponderado(participación_c,unidades_matched)
```

Supuestos:

- Las unidades comparables aproximan el comportamiento contrafactual de la unidad afectada.

Sesgos:

- El resultado depende de variables de matching y distancia.
- Puede introducir sesgo si faltan variables relevantes.
- Debe reportar calidad del match.

### Modelo D opcional: bloques históricos o familias políticas

Solo debe usarse si se construye una correspondencia defendible entre candidaturas, partidos, alianzas o bloques. Dado que las organizaciones políticas cambian entre elecciones, este modelo debe tratarse como exploratorio y no como evidencia principal.

## 7. Incertidumbre y sensibilidad

Análisis obligatorios:

- Baseline corto vs largo vs reciente vs robusto.
- Inclusión y exclusión de 2006.
- Inclusión y exclusión de 2021.
- Filtros por estado de acta.
- Modelo de imputación A, B y C.
- Umbrales de detección: MAD 2.5, 3.0 y 3.5; percentiles 90, 95 y 99.

Escenarios:

- Conservador: solo exceso positivo fuerte, baseline reciente, imputación nacional.
- Central: baseline corto, unidad UBIGEO, imputación local.
- Alto impacto: baseline corto o largo, exceso positivo moderado, imputación por distritos emparejados.

Monte Carlo opcional:

- Simular tasa esperada usando distribución empírica histórica por UBIGEO.
- Simular asignación de votos con distribución Dirichlet-multinomial por candidato y unidad.
- Fijar semilla determinística.
- Reportar intervalos, no puntos únicos.

## 8. Reglas de interpretación

Puede concluirse:

- Si 2026 presenta tasas de ausentismo superiores o inferiores a ciertos baselines.
- Qué unidades contribuyen más al exceso estimado.
- Cómo varían los resultados bajo diferentes supuestos.
- Qué tan sensible es el impacto contrafactual a cada modelo.

No puede concluirse:

- Que hubo fraude, manipulación, supresión o intencionalidad.
- Que los ausentes habrían votado de una forma observada.
- Que los votos imputados son votos reales.
- Que un escenario contrafactual reemplaza el resultado oficial.

Toda conclusión deberá incluir:

```text
Estos resultados son estimaciones contrafactuales bajo supuestos explícitos. No constituyen evidencia de manipulación electoral ni determinan causalidad.
```
