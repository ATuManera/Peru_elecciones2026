# ONPE Actas Scraper - Elecciones 2026

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Version](https://img.shields.io/badge/version-0.3.0-green.svg)](pyproject.toml)

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

El proyecto usa versionado semántico para el código y las herramientas operativas. La versión actual es **0.3.0**.

- `0.1.0`: flujo base para descargar, reconstruir y separar resultados ONPE 2026.
- `0.2.0`: incorpora insumos históricos oficiales de ONPE, el script `build_ausentismo_presidencial.py` y el CSV consolidado de ausentismo presidencial 2006-2026.
- `0.3.0`: agrega `consultar_padron_mesas.py`, el comando `onpe-consultar-padron-mesas` y corrige el rebuild de `mesas_consolidado.csv` para incluir todo JSON descargado válido, evitando excluir mesas cuyo estado agregado quedó desfasado.

Los datos publicados tienen un ciclo de actualización distinto al del código: pueden cambiar con cada refresh incremental, rebuild y split. Para reproducibilidad, se recomienda citar la ruta del archivo, la fecha de descarga o actualización y el commit de GitHub usado como referencia.

## Estado de Actualización de Datos

Según `data/output/por_votacion/mesas_presidencial.csv` y el control SQLite local, las mesas presidenciales consolidadas cubren un universo de **92,766** mesas. Con corte de refresh al **2 de mayo de 2026**, el avance de mesas contabilizadas es **97.49%**.

Snapshot de datos: generado automáticamente por `update_readme_status.py` desde `data/output/por_votacion/mesas_presidencial.csv`; CSV modificado el **2 de mayo de 2026 14:00:43 PET**. Commit local de base: `2ed4582`.

Resumen de mesas presidenciales por estado:

| Estado | Mesas | % del universo |
|---|---:|---:|
| Contabilizadas | 90,441 | 97.49% |
| Para envío al JEE | 2,325 | 2.51% |
| Pendientes | 0 | 0.00% |

Desagregado territorial de mesas presidenciales para envío al JEE o pendientes:

| Estado | Ámbito | Región | Provincia | Distrito | Mesas | % del universo |
|---|---|---|---|---|---:|---:|
| Para envío al JEE | PERU | AMAZONAS | BAGUA | IMAZA | 2 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | CHACHAPOYAS | BALSAS | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | CHACHAPOYAS | CHACHAPOYAS | 2 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | CHACHAPOYAS | CHILIQUIN | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | CHACHAPOYAS | LEYMEBAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | CHACHAPOYAS | MAGDALENA | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | CONDORCANQUI | EL CENEPA | 2 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | CONDORCANQUI | NIEVA | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | LUYA | COCABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | UTCUBAMBA | BAGUA GRANDE | 5 | 0.01% |
| Para envío al JEE | PERU | AMAZONAS | UTCUBAMBA | CAJARURO | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | UTCUBAMBA | CUMBA | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | UTCUBAMBA | JAMALCA | 1 | 0.00% |
| Para envío al JEE | PERU | AMAZONAS | UTCUBAMBA | LONYA GRANDE | 3 | 0.00% |
| Para envío al JEE | PERU | ANCASH | ANTONIO RAIMONDI | MIRGAS | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | ASUNCION | ACOCHACA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | ASUNCION | CHACAS | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | CARHUAZ | CARHUAZ | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | CARLOS FERMIN FITZCARRALD | SAN LUIS | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | CARLOS FERMIN FITZCARRALD | SAN NICOLAS | 2 | 0.00% |
| Para envío al JEE | PERU | ANCASH | CASMA | BUENA VISTA ALTA | 2 | 0.00% |
| Para envío al JEE | PERU | ANCASH | CASMA | CASMA | 12 | 0.01% |
| Para envío al JEE | PERU | ANCASH | CASMA | COMANDANTE NOEL | 3 | 0.00% |
| Para envío al JEE | PERU | ANCASH | CASMA | YAUTAN | 2 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARAZ | HUARAZ | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARAZ | INDEPENDENCIA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARAZ | OLLEROS | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARI | CHAVIN DE HUANTAR | 3 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARI | HUANTAR | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARI | MASIN | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARI | RAPAYAN | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARI | SAN MARCOS | 7 | 0.01% |
| Para envío al JEE | PERU | ANCASH | HUARMEY | CULEBRAS | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUARMEY | HUARMEY | 5 | 0.01% |
| Para envío al JEE | PERU | ANCASH | HUARMEY | MALVAS | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUAYLAS | CARAZ | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | HUAYLAS | YURACMARCA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | MARISCAL LUZURIAGA | LLUMPA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | PALLASCA | CONCHUCOS | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | POMABAMBA | QUINUABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SANTA | CACERES DEL PERU | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SANTA | CHIMBOTE | 4 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SANTA | NEPEÑA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SANTA | NUEVO CHIMBOTE | 4 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SANTA | SAMANCO | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SIHUAS | CASHAPAMPA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SIHUAS | HUAYLLABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | ANCASH | SIHUAS | QUICHES | 2 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | ANDAHUAYLAS | ANDAHUAYLAS | 4 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | ANDAHUAYLAS | HUANCARAMA | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | ANDAHUAYLAS | PACOBAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | ANDAHUAYLAS | PAMPACHIRI | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | ANDAHUAYLAS | TALAVERA | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | CHINCHEROS | ANCO-HUALLO | 2 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | CHINCHEROS | COCHARCAS | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | CHINCHEROS | SIN NOMBRE (030712) | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | COTABAMBAS | COYLLURQUI | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | COTABAMBAS | HAQUIRA | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | COTABAMBAS | TAMBOBAMBA | 3 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | GRAU | HUAYLLATI | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | GRAU | MARISCAL GAMARRA | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | GRAU | PATAYPAMPA | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | GRAU | PROGRESO | 1 | 0.00% |
| Para envío al JEE | PERU | APURIMAC | GRAU | VIRUNDO | 1 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | AREQUIPA | ALTO SELVA ALEGRE | 1 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | AREQUIPA | AREQUIPA | 1 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | AREQUIPA | MARIANO MELGAR | 3 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | AREQUIPA | PAUCARPATA | 2 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | CAMANA | MARISCAL CACERES | 2 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | CAMANA | SAMUEL PASTOR | 3 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | CAYLLOMA | COPORAQUE | 1 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | CAYLLOMA | MAJES | 1 | 0.00% |
| Para envío al JEE | PERU | AREQUIPA | ISLAY | MOLLENDO | 2 | 0.00% |
| Para envío al JEE | PERU | ASIA | JAPON | HYOGO | 1 | 0.00% |
| Para envío al JEE | PERU | ASIA | JAPON | MIE | 1 | 0.00% |
| Para envío al JEE | PERU | ASIA | JAPON | NAGOYA | 2 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | HUAMANGA | ACOCRO | 2 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | HUAMANGA | ACOS VINCHOS | 2 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | HUAMANGA | CARMEN ALTO | 2 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | HUAMANGA | SAN JOSE DE TICLLAS | 1 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | HUAMANGA | SOCOS | 1 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | HUAMANGA | TAMBILLO | 1 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | HUANTA | LLOCHEGUA | 1 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | LA MAR | SANTA ROSA | 1 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | VILCAS HUAMAN | HUAMBALPA | 1 | 0.00% |
| Para envío al JEE | PERU | AYACUCHO | VILCAS HUAMAN | VISCHONGO | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CAJABAMBA | CACHACHI | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CAJABAMBA | SITACOCHA | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CAJAMARCA | CAJAMARCA | 2 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CAJAMARCA | JESUS | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CAJAMARCA | LOS BAÑOS DEL INCA | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CELENDIN | CELENDIN | 4 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CHOTA | CHOTA | 2 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CHOTA | CONCHAN | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CHOTA | LAJAS | 2 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CHOTA | QUEROCOTO | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CHOTA | TACABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CONTUMAZA | CUPISNIQUE | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CUTERVO | CALLAYUC | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CUTERVO | CHOROS | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CUTERVO | CUTERVO | 3 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CUTERVO | QUEROCOTILLO | 2 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CUTERVO | SANTA CRUZ | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | CUTERVO | SANTO TOMAS | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | HUALGAYOC | BAMBAMARCA | 6 | 0.01% |
| Para envío al JEE | PERU | CAJAMARCA | HUALGAYOC | HUALGAYOC | 4 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | JAEN | COLASAY | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | JAEN | JAEN | 4 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | JAEN | LAS PIRIAS | 2 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | JAEN | POMAHUACA | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SAN IGNACIO | CHIRINOS | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SAN IGNACIO | HUARANGO | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SAN IGNACIO | LA COIPA | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SAN IGNACIO | SAN IGNACIO | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SAN IGNACIO | SAN JOSE DE LOURDES | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SAN MIGUEL | UNION AGUA BLANCA | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SANTA CRUZ | CATACHE | 2 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SANTA CRUZ | PULAN | 1 | 0.00% |
| Para envío al JEE | PERU | CAJAMARCA | SANTA CRUZ | SANTA CRUZ | 1 | 0.00% |
| Para envío al JEE | PERU | CALLAO | CALLAO | BELLAVISTA | 4 | 0.00% |
| Para envío al JEE | PERU | CALLAO | CALLAO | CALLAO | 27 | 0.03% |
| Para envío al JEE | PERU | CALLAO | CALLAO | CARMEN DE LA LEGUA-REYNOSO | 2 | 0.00% |
| Para envío al JEE | PERU | CALLAO | CALLAO | LA PERLA | 5 | 0.01% |
| Para envío al JEE | PERU | CALLAO | CALLAO | VENTANILLA | 26 | 0.03% |
| Para envío al JEE | PERU | CUSCO | ACOMAYO | POMACANCHI | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | ACOMAYO | SANGARARA | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | ANTA | ANCAHUASI | 3 | 0.00% |
| Para envío al JEE | PERU | CUSCO | ANTA | ANTA | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | ANTA | CACHIMAYO | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | ANTA | HUAROCONDO | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | ANTA | PUCYURA | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CALCA | LAMAY | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CALCA | SAN SALVADOR | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CUSCO | CCORCA | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CUSCO | CUSCO | 10 | 0.01% |
| Para envío al JEE | PERU | CUSCO | CUSCO | POROY | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CUSCO | SAN JERONIMO | 4 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CUSCO | SAN SEBASTIAN | 4 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CUSCO | SANTIAGO | 15 | 0.02% |
| Para envío al JEE | PERU | CUSCO | CUSCO | SAYLLA | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | CUSCO | WANCHAQ | 3 | 0.00% |
| Para envío al JEE | PERU | CUSCO | ESPINAR | ESPINAR | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | ECHARATE | 6 | 0.01% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | HUAYOPATA | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | INKAWASI | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | KIMBIRI | 4 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | MARANURA | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | MEGANTONI | 3 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | OCOBAMBA | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | PICHARI | 13 | 0.01% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | QUELLOUNO | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | SANTA TERESA | 3 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | SIN NOMBRE (070916) | 4 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | SIN NOMBRE (070917) | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | SIN NOMBRE (070918) | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | SIN NOMBRE (070919) | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | VILCABAMBA | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | LA CONVENCION | VILLA VIRGEN | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | PARURO | ACCHA | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | PARURO | CCAPI | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | PARURO | PARURO | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | PAUCARTAMBO | CHALLABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | PAUCARTAMBO | COLQUEPATA | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | QUISPICANCHI | OCONGATE | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | URUBAMBA | HUAYLLABAMBA | 2 | 0.00% |
| Para envío al JEE | PERU | CUSCO | URUBAMBA | OLLANTAYTAMBO | 1 | 0.00% |
| Para envío al JEE | PERU | CUSCO | URUBAMBA | URUBAMBA | 5 | 0.01% |
| Para envío al JEE | PERU | EUROPA | ALEMANIA | FRANKFURT | 2 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ALEMANIA | HAMBURGO | 1 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ESPA¿¿A | OVIEDO | 1 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ESPAÑA | BARCELONA | 6 | 0.01% |
| Para envío al JEE | PERU | EUROPA | ESPAÑA | BILBAO | 2 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ESPAÑA | MADRID | 8 | 0.01% |
| Para envío al JEE | PERU | EUROPA | ESPAÑA | SALAMANCA | 4 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ESPAÑA | SEVILLA | 1 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ESPAÑA | VIGO | 7 | 0.01% |
| Para envío al JEE | PERU | EUROPA | ESPAÑA | ZARAGOZA | 1 | 0.00% |
| Para envío al JEE | PERU | EUROPA | GRAN BRETAÑA | LONDRES | 1 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ITALIA | GENOVA | 1 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ITALIA | MILAN | 6 | 0.01% |
| Para envío al JEE | PERU | EUROPA | ITALIA | ROMA | 1 | 0.00% |
| Para envío al JEE | PERU | EUROPA | ITALIA | TURIN | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | ACOBAMBA | ACOBAMBA | 2 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | ACOBAMBA | ANTA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | ACOBAMBA | PAUCARA | 5 | 0.01% |
| Para envío al JEE | PERU | HUANCAVELICA | ACOBAMBA | POMACOCHA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | ANGARAES | ANCHONGA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | ANGARAES | CONGALLA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | ANGARAES | LIRCAY | 4 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | ANGARAES | SECCLLA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CASTROVIRREYNA | MOLLEPAMPA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CASTROVIRREYNA | TICRAPO | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CHURCAMPA | ANCO | 3 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CHURCAMPA | CHINCHIHUASI | 2 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CHURCAMPA | CHURCAMPA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CHURCAMPA | EL CARMEN | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CHURCAMPA | LA MERCED | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CHURCAMPA | PAUCARBAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | CHURCAMPA | SAN PEDRO DE CORIS | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | HUANCAVELICA | HUANCAVELICA | 2 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | HUANCAVELICA | VILCA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | HUANCAVELICA | YAULI | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | HUAYTARA | HUAYTARA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | HUAYTARA | PILPICHACA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | HUAYTARA | SANTIAGO DE QUIRAHUARA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | ACOSTAMBO | 2 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | ACRAQUIA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | DANIEL HERNANDEZ | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | HUARIBAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | PAMPAS | 2 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | PAZOS | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | QUICHUAS | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | SALCABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | SALCAHUASI | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | SANTIAGO DE TUCUMA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANCAVELICA | TAYACAJA | SURCUBAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | AMBO | AMBO | 4 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | AMBO | CAYNA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | AMBO | COLPAS | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | AMBO | CONCHAMARCA | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | AMBO | HUACAR | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | AMBO | SAN RAFAEL | 4 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | AMBO | TOMAY-KICHWA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | HUANUCO | AMARILIS | 11 | 0.01% |
| Para envío al JEE | PERU | HUANUCO | HUANUCO | CHURUBAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | HUANUCO | HUANUCO | 4 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | HUANUCO | PILLCO MARCA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | HUANUCO | SAN PEDRO DE CHAULAN | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | HUANUCO | SANTA MARIA DEL VALLE | 3 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | HUANUCO | YACUS | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LAURICOCHA | BAÑOS | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LAURICOCHA | JESUS | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LAURICOCHA | JIVIA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | CASTILLO GRANDE | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | DANIEL ALOMIA ROBLES | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | JOSE CRESPO Y CASTILLO | 4 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | LUYANDO | 3 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | MARIANO DAMASO BERAUN | 3 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | PUCAYACU | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | PUEBLO NUEVO | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | LEONCIO PRADO | RUPA-RUPA | 3 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | MARA¿¿ON | SANTA ROSA DE ALTO YANAJANCA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | MARAÑON | HUACRACHUCO | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | PACHITEA | CHAGLLA | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | PACHITEA | MOLINO | 6 | 0.01% |
| Para envío al JEE | PERU | HUANUCO | PACHITEA | PANAO | 6 | 0.01% |
| Para envío al JEE | PERU | HUANUCO | PACHITEA | UMARI | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | PUERTO INCA | CODO DEL POZUZO | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | PUERTO INCA | HONORIA | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | YAROWILCA | APARICIO POMARES | 1 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | YAROWILCA | CHORAS | 2 | 0.00% |
| Para envío al JEE | PERU | HUANUCO | YAROWILCA | OBAS | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | CHINCHA | CHAVIN | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | CHINCHA | CHINCHA ALTA | 9 | 0.01% |
| Para envío al JEE | PERU | ICA | CHINCHA | CHINCHA BAJA | 4 | 0.00% |
| Para envío al JEE | PERU | ICA | CHINCHA | EL CARMEN | 3 | 0.00% |
| Para envío al JEE | PERU | ICA | CHINCHA | GROCIO PRADO | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | CHINCHA | PUEBLO NUEVO | 11 | 0.01% |
| Para envío al JEE | PERU | ICA | CHINCHA | SUNAMPE | 5 | 0.01% |
| Para envío al JEE | PERU | ICA | CHINCHA | TAMBO DE MORA | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | ICA | 13 | 0.01% |
| Para envío al JEE | PERU | ICA | ICA | LA TINGUIÑA | 3 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | LOS AQUIJES | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | PACHACUTEC | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | PARCONA | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | PUEBLO NUEVO | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | SALAS | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | SAN JUAN BAUTISTA | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | SANTIAGO | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | ICA | SUBTANJALLA | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | NAZCA | MARCONA | 3 | 0.00% |
| Para envío al JEE | PERU | ICA | NAZCA | NAZCA | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | NAZCA | VISTA ALEGRE | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | PALPA | TIBILLO | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | PISCO | HUANCANO | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | PISCO | HUMAY | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | PISCO | INDEPENDENCIA | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | PISCO | PARACAS | 1 | 0.00% |
| Para envío al JEE | PERU | ICA | PISCO | PISCO | 14 | 0.02% |
| Para envío al JEE | PERU | ICA | PISCO | SAN ANDRES | 2 | 0.00% |
| Para envío al JEE | PERU | ICA | PISCO | SAN CLEMENTE | 4 | 0.00% |
| Para envío al JEE | PERU | ICA | PISCO | TUPAC AMARU INCA | 2 | 0.00% |
| Para envío al JEE | PERU | JUNIN | CHANCHAMAYO | CHANCHAMAYO | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | CHANCHAMAYO | PERENE | 2 | 0.00% |
| Para envío al JEE | PERU | JUNIN | CHANCHAMAYO | PICHANAQUI | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | CHANCHAMAYO | SAN LUIS DE SHUARO | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | HUANCAYO | EL TAMBO | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | HUANCAYO | PILCOMAYO | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | SATIPO | MAZAMARI | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | SATIPO | PANGOA | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | SATIPO | RIO NEGRO | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | TARMA | HUASAHUASI | 2 | 0.00% |
| Para envío al JEE | PERU | JUNIN | TARMA | LA UNION | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | TARMA | TARMA | 1 | 0.00% |
| Para envío al JEE | PERU | JUNIN | YAULI | LA OROYA | 2 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | CHEPEN | CHEPEN | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | JULCAN | CARABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | OTUZCO | HUARANCHAL | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PACASMAYO | PACASMAYO | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PACASMAYO | SAN PEDRO DE LLOC | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | BULDIBUYO | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | CHILLIA | 5 | 0.01% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | HUAYLILLAS | 2 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | HUAYO | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | ONGON | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | PARCOY | 5 | 0.01% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | PATAZ | 2 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | PIAS | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | TAYABAMBA | 9 | 0.01% |
| Para envío al JEE | PERU | LA LIBERTAD | PATAZ | URPAY | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | TRUJILLO | HUANCHACO | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | TRUJILLO | LAREDO | 2 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | TRUJILLO | TRUJILLO | 11 | 0.01% |
| Para envío al JEE | PERU | LA LIBERTAD | TRUJILLO | VICTOR LARCO HERRERA | 1 | 0.00% |
| Para envío al JEE | PERU | LA LIBERTAD | VIRU | VIRU | 1 | 0.00% |
| Para envío al JEE | PERU | LAMBAYEQUE | CHICLAYO | CHICLAYO | 1 | 0.00% |
| Para envío al JEE | PERU | LAMBAYEQUE | FERREÑAFE | CAÑARIS | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | BARRANCA | BARRANCA | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | BARRANCA | SUPE PUERTO | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | CANTA | CANTA | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | CAÑETE | CHILCA | 3 | 0.00% |
| Para envío al JEE | PERU | LIMA | CAÑETE | IMPERIAL | 5 | 0.01% |
| Para envío al JEE | PERU | LIMA | CAÑETE | NUEVO IMPERIAL | 3 | 0.00% |
| Para envío al JEE | PERU | LIMA | CAÑETE | SAN VICENTE DE CAÑETE | 3 | 0.00% |
| Para envío al JEE | PERU | LIMA | HUARAL | CHANCAY | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | HUARAL | HUARAL | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | HUAURA | HUACHO | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | HUAURA | HUAURA | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | HUAURA | SANTA MARIA | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | HUAURA | VEGUETA | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | ANCON | 14 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | ATE | 20 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | BARRANCO | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | CARABAYLLO | 17 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | CHACLACAYO | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | CHORRILLOS | 22 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | CIENEGUILLA | 10 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | COMAS | 51 | 0.05% |
| Para envío al JEE | PERU | LIMA | LIMA | EL AGUSTINO | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | INDEPENDENCIA | 30 | 0.03% |
| Para envío al JEE | PERU | LIMA | LIMA | JESUS MARIA | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | LA MOLINA | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | LA VICTORIA | 39 | 0.04% |
| Para envío al JEE | PERU | LIMA | LIMA | LIMA | 11 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | LINCE | 12 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | LOS OLIVOS | 18 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | LURIGANCHO | 17 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | LURIN | 19 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | MAGDALENA DEL MAR | 41 | 0.04% |
| Para envío al JEE | PERU | LIMA | LIMA | MIRAFLORES | 8 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | PACHACAMAC | 18 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | PUCUSANA | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | PUEBLO LIBRE | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | PUENTE PIEDRA | 20 | 0.02% |
| Para envío al JEE | PERU | LIMA | LIMA | PUNTA NEGRA | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | RIMAC | 24 | 0.03% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN BARTOLO | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN BORJA | 3 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN ISIDRO | 6 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN JUAN DE LURIGANCHO | 33 | 0.04% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN JUAN DE MIRAFLORES | 103 | 0.11% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN LUIS | 8 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN MARTIN DE PORRES | 45 | 0.05% |
| Para envío al JEE | PERU | LIMA | LIMA | SAN MIGUEL | 7 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | SANTA ANITA | 12 | 0.01% |
| Para envío al JEE | PERU | LIMA | LIMA | SANTA ROSA | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | SANTIAGO DE SURCO | 62 | 0.07% |
| Para envío al JEE | PERU | LIMA | LIMA | SURQUILLO | 2 | 0.00% |
| Para envío al JEE | PERU | LIMA | LIMA | VILLA EL SALVADOR | 50 | 0.05% |
| Para envío al JEE | PERU | LIMA | LIMA | VILLA MARIA DEL TRIUNFO | 30 | 0.03% |
| Para envío al JEE | PERU | LIMA | OYON | CAUJUL | 1 | 0.00% |
| Para envío al JEE | PERU | LIMA | OYON | PACHANGARA | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | LORETO | NAUTA | 5 | 0.01% |
| Para envío al JEE | PERU | LORETO | LORETO | PARINARI | 2 | 0.00% |
| Para envío al JEE | PERU | LORETO | LORETO | TIGRE | 2 | 0.00% |
| Para envío al JEE | PERU | LORETO | LORETO | TROMPETEROS | 4 | 0.00% |
| Para envío al JEE | PERU | LORETO | LORETO | URARINAS | 5 | 0.01% |
| Para envío al JEE | PERU | LORETO | MARISCAL RAMON CASTILLA | PEBAS | 8 | 0.01% |
| Para envío al JEE | PERU | LORETO | MARISCAL RAMON CASTILLA | RAMON CASTILLA | 11 | 0.01% |
| Para envío al JEE | PERU | LORETO | MARISCAL RAMON CASTILLA | SAN PABLO | 11 | 0.01% |
| Para envío al JEE | PERU | LORETO | MARISCAL RAMON CASTILLA | SIN NOMBRE (150605) | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | MARISCAL RAMON CASTILLA | YAVARI | 5 | 0.01% |
| Para envío al JEE | PERU | LORETO | MAYNAS | BELEN | 24 | 0.03% |
| Para envío al JEE | PERU | LORETO | MAYNAS | FERNANDO LORES | 4 | 0.00% |
| Para envío al JEE | PERU | LORETO | MAYNAS | INDIANA | 5 | 0.01% |
| Para envío al JEE | PERU | LORETO | MAYNAS | IQUITOS | 34 | 0.04% |
| Para envío al JEE | PERU | LORETO | MAYNAS | LAS AMAZONAS | 3 | 0.00% |
| Para envío al JEE | PERU | LORETO | MAYNAS | MAZAN | 6 | 0.01% |
| Para envío al JEE | PERU | LORETO | MAYNAS | NAPO | 4 | 0.00% |
| Para envío al JEE | PERU | LORETO | MAYNAS | PUNCHANA | 23 | 0.02% |
| Para envío al JEE | PERU | LORETO | MAYNAS | SAN JUAN BAUTISTA | 31 | 0.03% |
| Para envío al JEE | PERU | LORETO | MAYNAS | TORRES CAUSANA | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | PUTUMAYO | TENIENTE MANUEL CLAVERO | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | PUTUMAYO | YAGUAS | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | REQUENA | ALTO TAPICHE | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | REQUENA | CAPELO | 2 | 0.00% |
| Para envío al JEE | PERU | LORETO | REQUENA | EMILIO SAN MARTIN | 2 | 0.00% |
| Para envío al JEE | PERU | LORETO | REQUENA | JENARO HERRERA | 3 | 0.00% |
| Para envío al JEE | PERU | LORETO | REQUENA | MAQUIA | 5 | 0.01% |
| Para envío al JEE | PERU | LORETO | REQUENA | PUINAHUA | 7 | 0.01% |
| Para envío al JEE | PERU | LORETO | REQUENA | REQUENA | 6 | 0.01% |
| Para envío al JEE | PERU | LORETO | REQUENA | SAQUENA | 2 | 0.00% |
| Para envío al JEE | PERU | LORETO | REQUENA | TAPICHE | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | REQUENA | YAQUERANA | 5 | 0.01% |
| Para envío al JEE | PERU | LORETO | UCAYALI | CONTAMANA | 11 | 0.01% |
| Para envío al JEE | PERU | LORETO | UCAYALI | PADRE MARQUEZ | 5 | 0.01% |
| Para envío al JEE | PERU | LORETO | UCAYALI | PAMPA HERMOSA | 1 | 0.00% |
| Para envío al JEE | PERU | LORETO | UCAYALI | SARAYACU | 3 | 0.00% |
| Para envío al JEE | PERU | LORETO | UCAYALI | VARGAS GUERRA | 6 | 0.01% |
| Para envío al JEE | PERU | MADRE DE DIOS | MANU | HUEPETUHE | 2 | 0.00% |
| Para envío al JEE | PERU | MADRE DE DIOS | TAMBOPATA | INAMBARI | 1 | 0.00% |
| Para envío al JEE | PERU | MADRE DE DIOS | TAMBOPATA | LABERINTO | 1 | 0.00% |
| Para envío al JEE | PERU | MADRE DE DIOS | TAMBOPATA | LAS PIEDRAS | 2 | 0.00% |
| Para envío al JEE | PERU | MADRE DE DIOS | TAMBOPATA | TAMBOPATA | 8 | 0.01% |
| Para envío al JEE | PERU | MOQUEGUA | GENERAL SANCHEZ CERRO | PUQUINA | 1 | 0.00% |
| Para envío al JEE | PERU | MOQUEGUA | ILO | ILO | 2 | 0.00% |
| Para envío al JEE | PERU | MOQUEGUA | MARISCAL NIETO | MOQUEGUA | 1 | 0.00% |
| Para envío al JEE | PERU | MOQUEGUA | MARISCAL NIETO | SAN CRISTOBAL | 1 | 0.00% |
| Para envío al JEE | PERU | OCEANIA | AUSTRALIA | SIDNEY | 4 | 0.00% |
| Para envío al JEE | PERU | PASCO | DANIEL ALCIDES CARRION | PAUCAR | 1 | 0.00% |
| Para envío al JEE | PERU | PASCO | DANIEL ALCIDES CARRION | SANTA ANA DE TUSI | 1 | 0.00% |
| Para envío al JEE | PERU | PASCO | OXAPAMPA | CHONTABAMBA | 1 | 0.00% |
| Para envío al JEE | PERU | PASCO | OXAPAMPA | OXAPAMPA | 2 | 0.00% |
| Para envío al JEE | PERU | PASCO | OXAPAMPA | PALCAZU | 1 | 0.00% |
| Para envío al JEE | PERU | PASCO | OXAPAMPA | PUERTO BERMUDEZ | 1 | 0.00% |
| Para envío al JEE | PERU | PASCO | PASCO | HUARIACA | 1 | 0.00% |
| Para envío al JEE | PERU | PASCO | PASCO | TINYAHUARCO | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | AYABACA | AYABACA | 7 | 0.01% |
| Para envío al JEE | PERU | PIURA | AYABACA | FRIAS | 5 | 0.01% |
| Para envío al JEE | PERU | PIURA | AYABACA | LAGUNAS | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | AYABACA | MONTERO | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | AYABACA | PACAIPAMPA | 7 | 0.01% |
| Para envío al JEE | PERU | PIURA | AYABACA | PAIMAS | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | AYABACA | SUYO | 2 | 0.00% |
| Para envío al JEE | PERU | PIURA | HUANCABAMBA | EL CARMEN DE LA FRONTERA | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | HUANCABAMBA | HUANCABAMBA | 3 | 0.00% |
| Para envío al JEE | PERU | PIURA | HUANCABAMBA | HUARMACA | 4 | 0.00% |
| Para envío al JEE | PERU | PIURA | HUANCABAMBA | LALAQUIZ | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | HUANCABAMBA | SAN MIGUEL DE EL FAIQUE | 3 | 0.00% |
| Para envío al JEE | PERU | PIURA | HUANCABAMBA | SONDOR | 2 | 0.00% |
| Para envío al JEE | PERU | PIURA | MORROPON | CHULUCANAS | 3 | 0.00% |
| Para envío al JEE | PERU | PIURA | MORROPON | MORROPON | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | MORROPON | SAN JUAN DE BIGOTE | 2 | 0.00% |
| Para envío al JEE | PERU | PIURA | MORROPON | SANTO DOMINGO | 2 | 0.00% |
| Para envío al JEE | PERU | PIURA | PAITA | LA HUACA | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | PAITA | PAITA | 11 | 0.01% |
| Para envío al JEE | PERU | PIURA | PIURA | CASTILLA | 15 | 0.02% |
| Para envío al JEE | PERU | PIURA | PIURA | CATACAOS | 6 | 0.01% |
| Para envío al JEE | PERU | PIURA | PIURA | CURA MORI | 2 | 0.00% |
| Para envío al JEE | PERU | PIURA | PIURA | EL TALLAN | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | PIURA | LA ARENA | 5 | 0.01% |
| Para envío al JEE | PERU | PIURA | PIURA | LA UNION | 3 | 0.00% |
| Para envío al JEE | PERU | PIURA | PIURA | LAS LOMAS | 3 | 0.00% |
| Para envío al JEE | PERU | PIURA | PIURA | PIURA | 4 | 0.00% |
| Para envío al JEE | PERU | PIURA | PIURA | TAMBO GRANDE | 17 | 0.02% |
| Para envío al JEE | PERU | PIURA | PIURA | VEINTISEIS DE OCTUBRE | 3 | 0.00% |
| Para envío al JEE | PERU | PIURA | SECHURA | CRISTO NOS VALGA | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | SECHURA | SECHURA | 7 | 0.01% |
| Para envío al JEE | PERU | PIURA | SULLANA | BELLAVISTA | 7 | 0.01% |
| Para envío al JEE | PERU | PIURA | SULLANA | MARCAVELICA | 4 | 0.00% |
| Para envío al JEE | PERU | PIURA | SULLANA | QUERECOTILLO | 4 | 0.00% |
| Para envío al JEE | PERU | PIURA | SULLANA | SULLANA | 9 | 0.01% |
| Para envío al JEE | PERU | PIURA | TALARA | EL ALTO | 2 | 0.00% |
| Para envío al JEE | PERU | PIURA | TALARA | LA BREA | 1 | 0.00% |
| Para envío al JEE | PERU | PIURA | TALARA | MANCORA | 4 | 0.00% |
| Para envío al JEE | PERU | PIURA | TALARA | PARIÑAS | 7 | 0.01% |
| Para envío al JEE | PERU | PUNO | AZANGARO | AZANGARO | 3 | 0.00% |
| Para envío al JEE | PERU | PUNO | AZANGARO | CHUPA | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | CARABAYA | AYAPATA | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | CARABAYA | CORANI | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | CARABAYA | ITUATA | 2 | 0.00% |
| Para envío al JEE | PERU | PUNO | CARABAYA | SAN GABAN | 2 | 0.00% |
| Para envío al JEE | PERU | PUNO | CARABAYA | USICAYOS | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | HUANCANE | HUANCANE | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | HUANCANE | ROSASPATA | 2 | 0.00% |
| Para envío al JEE | PERU | PUNO | HUANCANE | TARACO | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | MELGAR | AYAVIRI | 2 | 0.00% |
| Para envío al JEE | PERU | PUNO | MOHO | HUAYRAPATA | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | MOHO | MOHO | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | SAN ANTONIO DE PUTINA | ANANEA | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | SAN ANTONIO DE PUTINA | PUTINA | 1 | 0.00% |
| Para envío al JEE | PERU | PUNO | SAN ROMAN | JULIACA | 4 | 0.00% |
| Para envío al JEE | PERU | PUNO | SANDIA | SAN PEDRO DE PUTINA PUNCO | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | BELLAVISTA | ALTO BIAVO | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | BELLAVISTA | BAJO BIAVO | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | BELLAVISTA | BELLAVISTA | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | BELLAVISTA | HUALLAGA | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | EL DORADO | SAN JOSE DE SISA | 3 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | EL DORADO | SAN MARTIN | 4 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | HUALLAGA | PISCOYACU | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | HUALLAGA | SAPOSOA | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | LAMAS | ALONSO DE ALVARADO | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | LAMAS | PINTO RECODO | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | MARISCAL CACERES | CAMPANILLA | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | MARISCAL CACERES | HUICUNGO | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | MOYOBAMBA | JEPELACIO | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | MOYOBAMBA | MOYOBAMBA | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | MOYOBAMBA | SORITOR | 4 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | PICOTA | BUENOS AIRES | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | PICOTA | PICOTA | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | PICOTA | SAN HILARION | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | PICOTA | SHAMBOYACU | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | PICOTA | TINGO DE PONASA | 6 | 0.01% |
| Para envío al JEE | PERU | SAN MARTIN | PICOTA | TRES UNIDOS | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | RIOJA | AWAJUN | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | RIOJA | ELIAS SOPLIN VARGAS | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | RIOJA | NUEVA CAJAMARCA | 4 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | RIOJA | PARDO MIGUEL | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | SAN MARTIN | CACATACHI | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | SAN MARTIN | CHAZUTA | 6 | 0.01% |
| Para envío al JEE | PERU | SAN MARTIN | SAN MARTIN | HUIMBAYOC | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | SAN MARTIN | LA BANDA DE SHILCAYO | 10 | 0.01% |
| Para envío al JEE | PERU | SAN MARTIN | SAN MARTIN | MORALES | 7 | 0.01% |
| Para envío al JEE | PERU | SAN MARTIN | SAN MARTIN | SAUCE | 3 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | SAN MARTIN | TARAPOTO | 13 | 0.01% |
| Para envío al JEE | PERU | SAN MARTIN | TOCACHE | NUEVO PROGRESO | 2 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | TOCACHE | POLVORA | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | TOCACHE | SIN NOMBRE (210806) | 1 | 0.00% |
| Para envío al JEE | PERU | SAN MARTIN | TOCACHE | TOCACHE | 2 | 0.00% |
| Para envío al JEE | PERU | TACNA | CANDARAVE | CAMILACA | 1 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | ATALAYA | RAIMONDI | 20 | 0.02% |
| Para envío al JEE | PERU | UCAYALI | ATALAYA | SEPAHUA | 4 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | ATALAYA | TAHUANIA | 4 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | CORONEL PORTILLO | CALLERIA | 28 | 0.03% |
| Para envío al JEE | PERU | UCAYALI | CORONEL PORTILLO | CAMPOVERDE | 1 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | CORONEL PORTILLO | IPARIA | 7 | 0.01% |
| Para envío al JEE | PERU | UCAYALI | CORONEL PORTILLO | MANANTAY | 10 | 0.01% |
| Para envío al JEE | PERU | UCAYALI | CORONEL PORTILLO | MASISEA | 1 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | CORONEL PORTILLO | NUEVA REQUENA | 2 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | CORONEL PORTILLO | YARINACOCHA | 14 | 0.02% |
| Para envío al JEE | PERU | UCAYALI | PADRE ABAD | ALEXANDER VON HUMBOLDT | 1 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | PADRE ABAD | CURIMANA | 2 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | PADRE ABAD | IRAZOLA | 3 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | PADRE ABAD | NESHUYA | 2 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | PADRE ABAD | PADRE ABAD | 4 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | PADRE ABAD | SIN NOMBRE (250206) | 2 | 0.00% |
| Para envío al JEE | PERU | UCAYALI | PADRE ABAD | SIN NOMBRE (250207) | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ARGENTINA | BUENOS AIRES | 17 | 0.02% |
| Para envío al JEE | EXTRANJERO | AMERICA | ARGENTINA | CORDOBA | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ARGENTINA | LA PLATA | 2 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ARGENTINA | ROSARIO DE SANTA FE | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ARGENTINA | SALTA | 3 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | BRASIL | MANAOS | 2 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | BRASIL | RIO BRANCO | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | CHILE | ARICA | 2 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | CHILE | IQUIQUE | 2 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | CHILE | SANTIAGO | 39 | 0.04% |
| Para envío al JEE | EXTRANJERO | AMERICA | COLOMBIA | LETICIA | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ECUADOR | LOJA | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | CAROLINA DEL NORTE | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | CHICAGO | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | DENVER | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | HARTFORD | 2 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | MIAMI | 5 | 0.01% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | NUEVA JERSEY | 24 | 0.03% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | NUEVA YORK | 4 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | ORLANDO | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | SAN FRANCISCO | 3 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | ESTADOS UNIDOS DE AMERICA | WASHINGTON D. C. | 12 | 0.01% |
| Para envío al JEE | EXTRANJERO | AMERICA | GUAYANA FRANCESA | CAYENA | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | MEXICO | GUADALAJARA | 1 | 0.00% |
| Para envío al JEE | EXTRANJERO | AMERICA | PANAMA | PANAMA | 1 | 0.00% |
| Pendientes | PERU | - | - | - | 0 | 0.00% |
| Pendientes | EXTRANJERO | - | - | - | 0 | 0.00% |

Votos válidos por organización política en mesas contabilizadas:

| Grupo | Votos válidos | % votos válidos |
|---|---:|---:|
| FUERZA POPULAR | 2,802,488 | 17.12% |
| JUNTOS POR EL PERÚ | 1,972,140 | 12.05% |
| RENOVACIÓN POPULAR | 1,944,558 | 11.88% |
| PARTIDO DEL BUEN GOBIERNO | 1,799,033 | 10.99% |
| PARTIDO CÍVICO OBRAS | 1,662,687 | 10.16% |
| Otros candidatos | 6,188,245 | 37.80% |

Blancos, nulos e impugnados suman **3,309,094** votos y no forman parte del denominador de votos válidos ONPE.

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
