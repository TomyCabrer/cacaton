# 05 Regulatory: las normas que Copi comprueba y las que tiene que cumplir

> Parte del análisis de negocio de Copi. Índice en [README](README.md). Doc vivo: https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W

Aquí hay dos cosas distintas. Unas normas son **la materia prima de Copi**: los protocolos que comprueba. Otras son **las que Copi tiene que cumplir** para que lo dejen entrar en un centro de control. La responsabilidad, los datos y los trabajadores están en [06 Legal](06%20Legal.md).

## Quién manda en la seguridad ferroviaria en España

| Organismo | Papel | Qué significa para Copi |
| --- | --- | --- |
| Ministerio de Transportes | Fija la política. El 2026-11-03 anunció el plan con un agente de IA que vigile las conversaciones | Aliado que empuja la compra |
| ADIF y ADIF AV | Gestor de la infraestructura. Opera los 19 CRC y es responsable de la seguridad de su red | Cliente que paga y usuario |
| AESF (Agencia Estatal de Seguridad Ferroviaria) | Autoridad de seguridad. Supervisa el sistema de gestión de la seguridad de ADIF y le envió siete advertencias entre 2023 y 2025 | Tiene que aceptar el análisis de riesgos de Copi |
| AITAT (antes CIAF, sustituida en agosto de 2024) | Investiga los accidentes, entre ellos Urda | Sus recomendaciones son el mejor argumento de venta |

## Normas que Copi comprueba (los protocolos)

- **Reglamento de Circulación Ferroviaria** (Real Decreto 664/2015, [BOE-A-2015-8042](https://www.boe.es/buscar/act.php?id=BOE-A-2015-8042)). Es la fuente principal de los protocolos: órdenes, telefonemas, marcha a la vista y qué hacer en modo degradado.
- **Real Decreto 606/2023**. Reforzó las condiciones de la marcha a la vista (art. 1.5.1.4): máximo 40 km/h y nunca rebasar una señal en rojo.
- **Consignas internas de ADIF**. Por ejemplo la COI 01/25: un tren detenido en la misma vía es un obstáculo, y si hay cualquier duda sobre la ocupación se impone marcha a la vista.
- **Para Copi**: el reglamento es público, así que se puede convertir en reglas comprobables sin pedirle nada a ADIF. Las consignas internas sí hay que conseguirlas en el piloto.

## Normas que Copi tiene que cumplir

| Norma | Qué pide | Cómo encaja Copi |
| --- | --- | --- |
| Directiva (UE) 2016/798 de seguridad ferroviaria y Ley 38/2015 del Sector Ferroviario | Que todo cambio en el sistema de ADIF pase por su sistema de gestión de la seguridad | Copi entra como cambio en el sistema y hay que evaluarlo |
| Método común de seguridad para la evaluación de riesgos (CSM-RA) | Análisis de riesgos del cambio, revisado por un evaluador independiente | Evaluador independiente desde el piloto (presupuestado en certificación) |
| Normas CENELEC EN 50126 y EN 50129 | Ciclo de vida de seguridad y niveles de integridad (SIL) | Como solo avisa y no actúa sobre el freno ni las señales, se le exige un nivel de integridad más bajo |
| Reglamento europeo de IA (UE 2024/1689) | Probablemente sistema de alto riesgo, por ser componente de seguridad ferroviario. Obligaciones desde el 2 de agosto de 2027 | Supervisión humana de serie (decide el controlador), registro de cada aviso, documentación técnica y gestión de riesgos desde el piloto |

**La decisión clave**: si Copi entra en el expediente de seguridad de ADIF como barrera certificada o se vende como ayuda adicional. Recomendamos empezar como ayuda: se puede desplegar antes, en paralelo, y la responsabilidad del operador no cambia. Más adelante, con los datos del piloto, se puede certificar como barrera.

## Compra pública

- **Piloto**: contrato menor o Compra Pública de Innovación, con cofinanciación de CDTI o Europe's Rail.
- **Despliegue nacional**: licitación abierta según la Ley de Contratos del Sector Público. Ciclo realista de 12 a 24 meses.
- Detalle y efecto en la caja: [03 Financials](03%20Financials.md).

## Lo que viene

El plan del Gobierno del 2026-11-03 pide un agente de IA que vigile las conversaciones, pero el 2026-11-06 seguía sin empresa, coste, plazo ni definición de si recomienda o interviene. Quien llegue con una especificación propia ("recomienda, no actúa") puede marcar cómo se escribe la licitación.

---

Normas citadas de memoria. Ningún jurista las ha revisado artículo por artículo.
