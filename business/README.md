# Copi: negocio

Análisis de negocio de Copi para el Imperial AI Hackathon 2026: por qué hace falta, cuánto mercado hay, cómo gana dinero, si es viable y qué dicen las normas y la ley. Lo ha preparado Jaime.

## Resumen

Copi es un supervisor de IA que vive en el centro de control. Escucha la radio y el resto de comunicaciones entre el controlador de ADIF y el maquinista, lee la telemetría y los registros de tren que llegan al centro, y hace dos cosas: 1) identifica qué protocolo se debería estar siguiendo en esa situación y 2) comprueba si se está siguiendo. Si no, avisa al controlador. No decide ni actúa, y no necesita nada instalado en el tren. El accidente de Urda (Toledo, 2026-10-28, al menos 69 muertos) nació de una orden del centro de control tras caer el LZB: es exactamente el fallo que Copi detecta.

- **Por qué ahora**: el plan de seguridad del Gobierno del 2026-11-03 ya incluye "un agente de IA" que vigile las conversaciones entre maquinista y controlador. Tres días después no tenía empresa, coste, plazo ni alcance. Copi es esa pieza, ya definida.
- **Mercado**: unos 10 M€ al año en España (\~240 puestos en los 19 centros de control de ADIF) y unos 125 M€ en Europa. Después, control aéreo.
- **Modelo**: licencia anual de 40.000 € por puesto de control, pagada por ADIF. Entrada con un piloto pagado en un centro.
- **Finanzas**: 12,7 M€ de ingresos y 52% de margen EBITDA en 2031. Break-even en 2029. Ronda de 2,5 M€.
- **Coste frente a lo que ya se gasta**: Copi en toda España cuesta menos al año que el 5% de un solo contrato de ERTMS (214 M€ en Murcia-Almería).
- **Riesgo principal**: acceso a los datos de ADIF, homologación y aceptación de los controladores, no la tecnología.

## Índice

| # | Tema | Qué responde |
| --- | --- | --- |
| 01 | [Necesidad](01%20Necesidad.md) | Qué problema resuelve Copi. Urda, los otros accidentes de 2026 y el hueco que nadie cubre |
| 02 | [Mercado](02%20Mercado.md) | Tamaño del mercado (España, Europa, aviación), por qué ahora y la competencia |
| 03 | [Financials](03%20Financials.md) | Modelo de negocio, precio, cómo compra ADIF, P&L 2027-2031, caja, ronda y sensibilidad |
| 04 | [Viabilidad](04%20Viabilidad.md) | Cómo funciona, qué se puede hacer hoy, DaVinci y datos, lo que España ya gasta y los riesgos |
| 05 | [Regulatory](05%20Regulatory.md) | Organismos, protocolos que Copi comprueba (RCF), homologación, Reglamento de IA y compra pública |
| 06 | [Legal](06%20Legal.md) | Responsabilidad, protección de datos, trabajadores, DaVinci e Indra, y cláusulas del contrato |
| 07 | [Fuentes](07%20Fuentes.md) | Todos los enlaces |

**Otras carpetas**

- [presentacion/](presentacion/): estructura de las slides de negocio y legal, con qué decir en cada una.
- [prensa/](prensa/): recopilación de noticias y los mejores argumentos para el pitch.
- [anexos/](anexos/): resumen del proyecto, el análisis completo en un solo archivo y la conversación con Claude de la que sale todo esto.

## Antes de usar estas cifras

- Los precios, el despliegue y los costes son supuestos del equipo, no datos publicados.
- La parte legal y regulatoria está citada de memoria. Ningún jurista la ha revisado.
- La versión que se edita es el doc: https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W. Este repo es una copia y no se actualiza solo.
- Los enlaces `[[...]]` de las notas de `prensa/`, `presentacion/` y `anexos/` son de Obsidian y aquí no funcionan.
