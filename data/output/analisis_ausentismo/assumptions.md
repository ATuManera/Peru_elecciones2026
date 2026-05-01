# Supuestos y decisiones metodológicas

Run ID: `c84e4256-df72-45e1-8c50-757b83401520`
Commit: `e26740bdf8d1f4e14a0f4ef365c121cf77280cc3`
Fecha: `2026-05-01T08:35:08.168183+00:00`

## Baseline elegido

Baseline principal: **mediana/MAD sobre 2011, 2016 y 2021** (`baseline_robust_median_mad`).

**Por qué:** Combina los tres ciclos electorales históricos más recientes. La mediana es robusta
ante el dato atípico de 2021 (pandemia). El MAD mide dispersión sin asumir normalidad.
2006 se excluye del baseline principal por diferencias estructurales (tasa 11.3 %, padrón distinto).

Baselines de robustez calculados en paralelo: corto (2011/16), largo (2006/11/16), reciente (2016/21).

## Filtros aplicados

- **Estado del acta**: solo mesas con estado terminal (`contabilizada_normal`, `resuelta`).
  Se excluyen `sin_instalar`, `anulada`, `en_proceso`, `otro`.
- **Electores hábiles**: se excluyen mesas con `electores_habiles = 0` o vacío.
- **Votos emitidos**: se excluyen mesas con `votos_emitidos > electores_habiles`.
- **Núcleo incompleto**: filas sin `electores_habiles`, `votos_emitidos` o `ausentes` no
  entran a la inferencia de ubigeo.

## Modelos activados

- **Modelo A** (distribución nacional 2026): `distribucion_nacional`
- **Modelo B** (distribución local por ubigeo 2026): `distribucion_ubigeo`
- **Modelo C** (matching territorial aproximado): `matching_ubigeos_aproximado`
- **Modelo D** (bloque partidario): **no activado** — requiere archivo `bloques_partidarios.yaml`
  pre-registrado.

## Decisiones no automatizables

- Los años de baseline fueron elegidos por el diseño metodológico en `docs/analisis_ausentismo/METHODOLOGY.md`;
  no se optimizaron para producir ningún resultado específico.
- El umbral de flag principal es z-robusto ≥ 3.5, conservador por diseño.

## Limitaciones reconocidas

- El matching territorial usa distancia euclidiana sobre variables disponibles; no es causal.
- 2021 incluye efectos pandemia; elevar el baseline esperado puede subestimar el exceso.
- Los ubigeos sin dato en al menos un año de baseline quedan marcados `baseline_insuficiente`.
- Las preferencias no observadas de electores ausentes **no** pueden conocerse; los modelos
  A, B y C son supuestos, no observaciones.

## Estos resultados son estimaciones contrafactuales bajo supuestos explícitos. No constituyen evidencia de manipulación electoral, fraude ni causalidad. Su propósito es analítico y exploratorio.
