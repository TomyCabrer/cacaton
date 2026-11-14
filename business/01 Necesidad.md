# 01 Necesidad: el problema que resuelve Copi

> Parte del análisis de negocio de Copi. Índice en [README](README.md). Doc vivo: https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W

## 2026 ha demostrado que el eslabón débil es la decisión humana sin segunda mirada

En 2026 la red española ha sufrido tres accidentes graves en diez meses. El de Toledo es exactamente el caso de uso de Copi: un sistema de seguridad cae, el humano decide mal y nadie lo comprueba.

| Fecha | Accidente | Víctimas | Qué falló | ¿Lo habría visto Copi? |
| --- | --- | --- | --- | --- |
| 2026-10-28 | Urda (Toledo): un AVE choca con un Iryo parado ante la señal de entrada | Al menos 69 muertos (el ministro dio 64 el primer día) | Cae el LZB en 63 km con unos 6 trenes. El centro de Atocha asume la circulación y autoriza al AVE a reanudar "con normalidad" en vez de en marcha a la vista. Recorre unos 25 km a hasta 200 km/h. Junto al operario había un auxiliar, un supervisor y otra persona, y el AVE avanzó un cuarto de hora a la vista de todos en los paneles | Sí: el reglamento exige una orden de texto fijo ("con Marcha a la Vista", máximo 40 km/h) y la consigna COI 01/25 de ADIF prohíbe autorizar la entrada a una vía ocupada. La orden dada contradice las dos |
| 2026-01-20 | Gelida (Rodalies R4): un muro cae sobre la vía | 1 muerto (maquinista en prácticas), 37 heridos | Infraestructura y lluvias | No: no hay decisión humana errónea |
| 2026-01-18 | Adamuz (Córdoba): descarrila un Iryo e invade la vía de un Alvia | 46 muertos | Vía (cambio de agujas en tramo renovado), causa en investigación | Parcial: no evita el descarrilamiento; sí podría exigir detener al tren que viene de frente |
| 2024 | Cuenca-Fernando Zóbel: un AVE rebasa una señal en rojo | Sin consecuencias graves | La CIAF concluyó que la única barrera era "la comprobación visual por parte del Responsable de Circulación", que "depende completamente del factor humano" | Sí: segunda comprobación automática de esa barrera humana |
| 2013-07-24 | Angrois (Santiago): Alvia a unos 190 km/h en curva limitada a 80 | 80 muertos | Maquinista distraído, sin protección ERTMS en el tramo | Parcial: solo si la telemetría llega a tiempo al centro |

El ministro Óscar Puente reconoció tras Toledo que el sistema tiene límites "especialmente los relacionados con la intervención humana". El coste no es solo humano: entre enero y abril de 2026 la alta velocidad perdió el 19,6% de viajeros (de 13,75 a 11,06 millones), con febrero en -32%.

La CIAF ya lo había avisado: tras el incidente de 2024 pidió medidas técnicas para mitigar el fallo humano, entre ellas revisar los procedimientos para reanudar la marcha y dar mejor información al responsable de circulación sobre el sistema de protección en uso. Es casi la descripción de Copi.

**Más personas no lo arreglan.** El operario que dio la orden tenía experiencia y no estaba bajo presión: los trenes estaban parados. Tenía tres personas al lado y nadie vio el error. A eso se suma la fatiga: en agosto el sindicato CSIF denunció turnos de 12 horas y hasta cinco noches seguidas, y llegan a los puestos de mando operadores sin experiencia previa en circulación. El Sindicato de Circulación Ferroviaria (SCF) pide que la seguridad no dependa de la discrecionalidad individual del responsable de circulación. Es el argumento de Copi, y un posible aliado.

**Un humano detectó el error; el centro no.** Otro maquinista corrigió por radio al centro: "No puede ser marcha normal; tiene que ser marcha a la vista". La orden al AVE se dio a las 8:36; el Iryo avisó a las 8:41 y a las 8:48 de que seguía parado; el choque fue hacia las 8:53. Fueron unos 17 minutos con los dos trenes en el mismo cantón en pantalla. Un responsable de circulación llegó a gestionar "hasta 104 telefonemas" en un turno: nadie puede revisar eso a mano.

No es un caso aislado. La CIAF contó 15 incidentes parecidos entre enero de 2023 y marzo de 2025, y la AESF envió siete advertencias a ADIF. En Alemania, el choque de Bad Aibling (2016, 11 muertos) también nació de una orden errónea del controlador. Urda la investiga la AITAT, que sustituyó a la CIAF en agosto de 2024.

Los sistemas actuales (ASFA, LZB, ERTMS) protegen al tren frente a la señal. DaVinci, la plataforma de gestión de tráfico de ADIF, muestra la ocupación de la vía, pero no comprueba ni bloquea una orden verbal errónea del puesto de mando. Nadie verifica que lo que dice el controlador cumple el protocolo. Ese hueco es el que cubre Copi, y además quita presión al controlador: sabe que si se equivoca, Copi se lo marcará.

## El caso de Urda paso a paso (escenario de la demo)

Fuente: infoLibre, 2026-10-29, "El papel del centro de control de Adif en el accidente de Urda..." (Jaime pegó el texto desde archive.today).

- ADIF gestiona la circulación desde 19 CRC abiertos 24/7; en Madrid, Atocha, Delicias y Villaverde. Herramientas: CTC (enclavamientos, señales, desvíos, itinerarios) y DaVinci (panel integrador; muestra en tiempo real la posición de los trenes y el tramo ocupado por un tren detenido).
- Plantilla: por cada tres factores de circulación, un controlador al lado que los supervisa; por encima, un técnico.
- Secuencia normativa cuando cae el LZB (sobre las 8:30 el día del accidente):
  1. El tren recibe una instrucción automática. Velocidad meta cero = hay otro tren delante antes de la siguiente estación.
  2. El maquinista debe detenerse y avisar al centro de control.
  3. Vuelven a mandar las señales de vía; la protección pasa al ASFA.
  4. Para reanudar, el centro de control da una orden con texto fijo: continuar "con 'Marcha a la Vista'", máximo 40 km/h. "En ningún caso" permite rebasar una señal en rojo.
- Consigna COI 01/25 de ADIF: un tren detenido delante en la misma vía es un obstáculo. No se autoriza rebasar una señal en parada que da acceso a vía ocupada salvo condiciones excepcionales (verificar desvíos, confirmar que no hay riesgo de colisión). Ante cualquier duda sobre la ocupación, el responsable de circulación impone condiciones restrictivas, típicamente marcha a la vista.
- Lo que pasó: el operario (con experiencia, sin presión, con un auxiliar, un supervisor y otra persona al lado) ordenó al AVE circular con normalidad. El AVE avanzó un cuarto de hora, visible en los paneles, hasta chocar con el Iryo.
- Contexto laboral: CSIF denunció (infoLibre dice agosto; la nota de CSIF que se encontró es del 2026-09-04) turnos de 12 horas y hasta 5 noches seguidas; llegan a los puestos de mando operadores sin experiencia previa en circulación. El SCF pide que la seguridad no dependa de la discrecionalidad individual.
- Para Copi: es el caso perfecto. Entrada = estado "LZB caído + vía ocupada" + transcripción de la orden. Protocolo esperado = texto fijo "con Marcha a la Vista". Orden real = "con normalidad". Copi marca la discrepancia al momento.

Más prensa y argumentos para el pitch: [prensa/Narrativa y noticias](prensa/Narrativa%20y%20noticias.md).
