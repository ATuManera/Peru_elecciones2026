# Supuestos y decisiones metodológicas

> **AVISO OBLIGATORIO.** Los resultados de este análisis son **estimaciones
> contrafactuales bajo supuestos explícitos**. No constituyen evidencia de
> fraude, manipulación, supresión ni intención. Son señales para revisión
> adicional por las autoridades electorales competentes (ONPE, JNE, JEE)
> y la sociedad civil.

## Identificador de corrida

`47105560-29b5-42e7-b132-2051e092ee98`

## Baseline elegido

**Baseline principal**: mediana/MAD sobre años 2011, 2016, 2021.

**Justificación**:
- 2011 y 2016 son las elecciones pre-pandemia comparables estructuralmente a 2026.
- 2021 se incluye para capturar variabilidad reciente, aunque es atípica (pandemia).
- La mediana y MAD minimizan el peso de un único año atípico.
- Se excluye 2006 del baseline principal por diferencias estructurales
  (tasa agregada 11.29 %, esquema de mesas distinto, padrón menor).

**Corrección metodológica aplicada**: `baseline_robust_median_mad` usa los años
(2011, 2016, 2021), **no** solo (2011, 2016). Ver METHODOLOGY.md §2.4.

## Filtros aplicados

- **Estado del acta**: solo `terminal_normal` y `terminal_resuelto`.
  Se excluyen `no_instalada`, `anulada_no_contabilizada`, `pendiente`, `desconocido`.
  **Corrección metodológica aplicada**: el filtro se aplica **antes** de agregar
  por ubigeo, no después.
- **Mesas con `electores_habiles = 0`** o vacío: excluidas.
- **Mesas con `votos_emitidos > electores_habiles`**: excluidas.
- **Ubigeos con cobertura de baseline < 0.5**: marcados `baseline_insuficiente`.

## Modelos activados

- **Modelo A**: distribución nacional 2026.
- **Modelo B**: distribución local 2026 por ubigeo (estimación central).
- **Modelo C**: distritos pareados (k=7, mismo departamento, cobertura=1.0).
- **Modelo D**: desactivado (requiere bloques pre-registrados).

## Escenarios ejecutados

S1–S8 según METHODOLOGY.md §7.1.

## geographic_concentration.csv

**Corrección metodológica aplicada**: tres niveles (ubigeo, provincia,
departamento) con mediana z-robusto y % ubigeos flageados.

## Limitaciones reconocidas

1. Supuestos de modelos no validados empíricamente.
2. 2021 en baseline amplía rango por efecto pandemia.
3. Esquemas de mesa distintos entre elecciones.
4. Nombres de candidatos no comparables entre años.
5. Cobertura de matching (Modelo C) puede ser insuficiente.
6. Snapshot 2026 estático; refresh puede modificarlo.

## Aviso de no atribución de fraude

Ningún resultado puede interpretarse como evidencia de fraude,
manipulación electoral o supresión de votos.
