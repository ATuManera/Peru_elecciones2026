# REPORTE FINAL — Análisis de Ausentismo Presidencial 2026

> **AVISO OBLIGATORIO.** Los resultados de este reporte son **estimaciones
> contrafactuales bajo supuestos explícitos**. No constituyen evidencia de
> fraude, manipulación, supresión ni intención. Son señales para revisión
> adicional por las autoridades electorales competentes (ONPE, JNE, JEE)
> y la sociedad civil.

- **Fecha**: 2026-05-01 09:03 UTC  |  **Run ID**: `47105560-29b5-42e7-b132-2051e092ee98`
- **Commit**: `4833784f13d9`  |  **Rama**: `codex/analisis-ausentismo-2026-metodologia`
- **Baseline principal**: mediana/MAD sobre 2011+2016+2021

---

## 1. Resumen ejecutivo

### Tabla 1 — Indicadores agregados nacionales por año

|Año|Electores hábiles|Votos emitidos|Ausentes|Tasa|N mesas|
|----|-----------------|--------------|--------|----|-------|
|2006|16,493,087|14,632,003|1,861,084|0.1128|88460|
|2011|19,941,435|16,699,734|3,241,701|0.1626|107408|
|2016|22,895,434|18,734,130|4,161,304|0.1818|77281|
|2021|24,850,075|17,508,068|7,342,007|0.2955|85005|
|2026|25,748,032|19,120,194|6,627,838|0.2574|87771|

### Ubigeos flageados (z-robusto ≥ 3.5)

- Ubigeos analizados: **2,093**
- Flageados z ≥ 3.5: **552** (26.4 %)
- Exceso total de ausentes estimado: **1,901,585** electores

> Los ubigeos flageados **ameritan revisión adicional**; no constituyen
> evidencia de irregularidad.

---

## 2. Alcance y aviso obligatorio

Este análisis NO afirma: fraude, manipulación, supresión, intencionalidad,
ni que el resultado oficial sea incorrecto.

Este análisis SÍ produce: medición de diferencias estadísticas, distribución
geográfica de ubigeos con desviaciones grandes, rangos contrafactuales bajo
supuestos explícitos.

Instituciones competentes para investigar irregularidades: ONPE, JNE, JEE,
Ministerio Público, Defensoría del Pueblo, observadores nacionales/internacionales.

---

## 3. Fuentes de datos

| Archivo | SHA-256 (primeros 16 chars) |
|---------|------------------------------|
| `mesas_ausentismo_presidencial_2006_2026.csv` | `8ac800a890c8dc25…` |
| `mesas_presidencial.csv` | `9526347f86b3cd58…` |

---

## 4. Calidad y comparabilidad

| Año | Recomendación de uso |
|-----|---------------------|
| 2006 | Robustez secundaria — diferencias estructurales |
| 2011 | Robustez secundaria — ~107k mesas vs ~77-88k |
| 2016 | Baseline principal — pre-pandemia, alta comparabilidad |
| 2021 | Incluido con etiqueta "ciclo atípico" (pandemia) |
| 2026 | Año de evaluación |

---

## 5. Metodología

- **Unidad de inferencia**: ubigeo distrital (~2,000)
- **Baseline**: mediana/MAD sobre 2011+2016+2021 (corrección metodológica: incluye 2021)
- **Umbral principal**: z-robusto ≥ 3.5
- **Filtro de estado**: solo `terminal_normal` y `terminal_resuelto`, aplicado
  **antes** de agregar por ubigeo (corrección metodológica)
- **Modelos**: A (nacional), B (local), C (matching k=7 mismo departamento)
- **Escenarios**: S1–S8 (ver `assumptions.md`)

`z_robusto_u = (tasa_2026_u − tasa_baseline_u) / (1.4826 × MAD_u)`

---

## 6. Línea base histórica

Tendencia creciente: 2006 (11.3%) → 2011 (16.3%) → 2016 (18.2%)
→ 2021 (29.5%, pandemia). Ver Tabla 1.

---

## 7. Evaluación del ausentismo 2026

### Tabla 2 — Top-20 ubigeos por z-robusto

> *Ameritan revisión adicional, no constituyen evidencia de irregularidad.*

|Ubigeo|Departamento|Provincia|Tasa 2026|Tasa baseline|Z-rob|Exc. aus.|
|------|------------|---------|---------|-------------|-----|---------|
|932801|ASIA|KUWAIT|1.000000|0.333333|66.666667|2.7|
|931302|ASIA|JORDANIA|1.000000|0.346154|65.384615|32.7|
|922802|AMÉRICAS|VENEZUELA|1.000000|0.399577|58.396819|9916.0|
|930801|ASIA|LIBANO|1.000000|0.416667|58.333333|16.3|
|931904|ASIA|ARABIA SAUDITA|1.000000|0.666667|33.333333|18.0|
|920207|AMÉRICAS|ARGENTINA|0.549098|0.290147|25.895169|258.4|
|921320|AMÉRICAS|ESTADOS UNIDOS DE AM|0.884776|0.642857|24.191928|1444.5|
|040506|AREQUIPA|CASTILLA|0.618857|0.387516|23.134031|230.6|
|010403|AMAZONAS|LUYA|0.677032|0.406667|22.711020|382.6|
|160301|LORETO|TAHUAMANU|0.382604|0.191199|19.140497|336.7|
|020904|ÁNCASH|MARISCAL LUZURIAGA|0.590861|0.405928|18.493351|352.1|
|050804|AYACUCHO|HUANCA SANCOS|0.472357|0.295814|17.654246|364.0|
|050714|AYACUCHO|VICTOR FAJARDO|0.499809|0.324740|17.506857|457.1|
|022008|ÁNCASH|OCROS|0.670118|0.487805|17.381589|123.2|
|250301|UCAYALI|ATALAYA|0.499980|0.328403|17.157760|4344.9|
|930731|ASIA|JAPON|0.695978|0.525886|17.009263|249.5|
|921328|AMÉRICAS|ESTADOS UNIDOS DE AM|0.805732|0.555200|16.934247|865.3|
|150603|LIMA|MARISCAL RAMON CASTI|0.579100|0.411834|16.726541|1735.0|
|091005|HUANCAVELICA|LAURICOCHA|0.527294|0.362674|16.462026|557.9|
|091007|HUANCAVELICA|LAURICOCHA|0.520202|0.356907|16.329521|226.3|

---

## 8. Concentración geográfica

El archivo `geographic_concentration.csv` agrega en tres niveles:
**ubigeo**, **provincia** y **departamento**, con mediana de z-robusto y
% de ubigeos flageados por zona.

> Concentración geográfica NO implica intención coordinada. Puede reflejar
> factores estructurales (clima, logística, demografía).

---

## 9. Escenarios contrafactuales

### Tabla 3 — S1 (baseline 2011+2016+2021, Modelo B) — top candidatos

> *Estimación contrafactual condicional. Cifras son escenarios, no hechos.*

|Candidato|Delta votos|Votos obs.|% padrón|No robusto|
|---------|-----------|----------|--------|----------|
|FUERZA POPULAR|330214.15|2718252|1.2825|0|
|JUNTOS POR EL PERÚ|297695.12|1917873|1.1562|0|
|RENOVACIÓN POPULAR|221384.86|1894045|0.8598|0|
|PARTIDO CÍVICO OBRAS|190120.69|1619958|0.7384|0|
|PARTIDO DEL BUEN GOBIERNO|179244.19|1758439|0.6961|0|
|PARTIDO PAÍS PARA TODOS|141102.48|1256150|0.5480|0|
|AHORA NACIÓN - AN|127912.77|1169855|0.4968|0|
|PRIMERO LA GENTE – COMUNIDAD, ECOLOGÍA, |56305.05|545678|0.2187|0|
|PARTIDO SICREO|53811.88|537036|0.2090|0|
|PODEMOS PERÚ|35162.23|252601|0.1366|0|
|PARTIDO FRENTE DE LA ESPERANZA 2021|30771.25|294864|0.1195|0|
|ALIANZA PARA EL PROGRESO|25266.69|180580|0.0981|0|
|PARTIDO POLÍTICO COOPERACIÓN POPULAR|20565.50|207322|0.0799|0|
|PARTIDO DEMOCRÁTICO SOMOS PERÚ|20105.92|142942|0.0781|0|
|PARTIDO APRISTA PERUANO|17229.10|152791|0.0669|0|

---

## 10. Análisis de sensibilidad

Ver `sensitivity_summary.csv`. Un candidato con `delta_no_robusto=1` cambia
de signo en >20% de los escenarios — su delta no debe citarse como puntual.

---

## 11. Limitaciones

1. Supuestos de modelos no validados empíricamente.
2. 2021 en baseline amplía rango por pandemia.
3. Esquemas de mesa no uniformes entre elecciones.
4. Nombres de candidatos no comparables entre años.
5. Modelo C depende de disponibilidad de ubigeos control por departamento.
6. Snapshot 2026 estático; refresh puede modificarlo.
7. Ningún modelo establece causalidad.

---

## 12. Conclusiones

Los resultados describen diferencias estadísticas entre la tasa de ausentismo
2026 y el baseline histórico. Las unidades territoriales flageadas constituyen
una lista reproducible para que autoridades electorales, observadores e
investigadores decidan si ameritan revisión adicional.

> "Las estimaciones aquí presentadas son escenarios contrafactuales bajo
> supuestos explícitos. Ofrecen una base cuantitativa para que las autoridades
> electorales, observadores nacionales e internacionales y la sociedad civil
> decidan si ciertas unidades territoriales merecen revisión adicional.
> Cualquier interpretación más allá de ese alcance excede el propósito de
> este reporte."

---

## 13. Apéndice de reproducibilidad

- **Commit**: `4833784f13d98cf1ea9ecf1937b1928df6c429be`
- **Rama**: `codex/analisis-ausentismo-2026-metodologia`
- **Run ID**: `47105560-29b5-42e7-b132-2051e092ee98`
- **Comando**: `python3 analyze_ausentismo_presidencial.py`
- **Config**: `data/output/analisis_ausentismo/config_run.yaml`
- **Manifiesto**: `data/output/analisis_ausentismo/manifest_run.json`
- **Supuestos**: `data/output/analisis_ausentismo/assumptions.md`

| Archivo | Descripción |
|---------|-------------|
| `audit_checks.csv` | Verificaciones de calidad |
| `absenteeism_by_mesa.csv` | Ausentismo por mesa × año |
| `absenteeism_by_ubigeo.csv` | Ausentismo por ubigeo × año (terminal) |
| `baselines_by_ubigeo.csv` | Mediana/MAD por ubigeo |
| `excess_absenteeism_flags.csv` | Exceso y flags 2026 |
| `geographic_concentration.csv` | Tres niveles: ubigeo/prov/dep |
| `candidate_impact_scenarios.csv` | Impacto contrafactual S1-S8 |
| `sensitivity_summary.csv` | Resumen de sensibilidad S1-S8 |
| `manifest_run.json` | Metadatos de reproducibilidad |
| `config_run.yaml` | Parámetros |
| `assumptions.md` | Supuestos metodológicos |

---
*No citar resultados como evidencia de fraude, manipulación o supresión.*
