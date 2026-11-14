---
type: project-note
project: "[[Copi]]"
created: 2026-11-14
tags: [project, hackathon, presentación]
related: ["[[Copi]]", "[[Copi narrativa y noticias]]"]
---
# Copi slides negocio y legal

Las slides de Jaime en el pitch de [[Copi]]. Las cifras salen del doc [Copi: análisis de mercado y financiero](https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W). Si cambian allí, se cambian aquí.

Van después de la demo de Tomy y Michel: el jurado ya ha visto que funciona y ahora quiere saber si alguien lo compraría y si se puede usar legalmente.

Son tres slides. Si hay poco tiempo, la 1 y la 2 se juntan en una.

## Slide 1. Mercado y por qué ahora

**Título:** Proteger todos los centros de control de España cuesta 10 M€ al año. Un solo tramo de ERTMS cuesta 214 M€.

**Visual principal:** gráfico de barras horizontal con lo que ya se gasta en seguridad y Copi al final:
- ERTMS Murcia-Almería: 214 M€
- ERTMS Talayuela-Plasencia: 126,5 M€
- Cambio de LZB a ERTMS en Madrid-Sevilla: 77,55 M€
- Copi en toda España: ~10 M€/año

**A la derecha, tamaño del mercado (3 cifras):**
- España: ~240 puestos en 19 centros de ADIF, unos 10 M€ al año
- Europa: ~125 M€ al año
- Después: control aéreo

**Franja inferior, "por qué ahora":**
- 2026-11-03: el Gobierno anuncia un agente de IA que vigile las conversaciones entre maquinistas y controladores. Todavía no hay empresa, coste ni plazo.
- La confianza en el AVE ha bajado del 67 % al 35 % (YouGov).

**Qué decir (20 s):** "ADIF ya gasta cientos de millones en proteger el tren frente a la señal. Lo que nadie protege es la orden verbal. Cubrir todos los centros de España cuesta menos que el 0,2 % de lo que ADIF invirtió en 2025. Y el Gobierno ya ha dicho que lo quiere."

## Slide 2. Competencia y modelo de negocio

**Título:** Todo lo que hay protege el tren. Copi es el único que comprueba la orden.

**Izquierda, competencia (tabla de 3 filas o mapa 2x2):**

| Qué existe | Ejemplos | Qué no hace |
|---|---|---|
| Protección del tren | ASFA, LZB, ERTMS | Cuando falla, se pasa a procedimientos manuales sin nadie que los supervise (Urda) |
| Gestión de tráfico | DaVinci (Indra) | Enseña la vía, pero no comprueba si una orden cumple el protocolo |
| IA en el tren o en la vía | Futurail, OTIV, Mirasys, Purple Transform | Vigila al maquinista o la vía, no la decisión del centro de control |

Si se hace mapa 2x2, los ejes son "persona o máquina" y "tren o centro de control". Copi queda solo en la casilla de persona y centro de control.

**Derecha, modelo de negocio:**
- Cliente que paga: ADIF
- 40.000 € por puesto y año. Un puesto 24/7 necesita unas 5 personas en turnos, así que Copi cuesta en torno al 12-15 % de lo que cuesta cubrirlo.
- Piloto en un centro: 250.000-400.000 €
- Break-even en 2029. Ingresos de 12,7 M€ en 2031. Ronda de 2,5 M€.

**Abajo, el riesgo dicho sin rodeos:** Indra mantiene DaVinci (32,7 M€ en 4 años, como única oferta). Puede ser nuestro socio o nuestro competidor. Por eso queremos llegar antes con un piloto.

**Qué decir (25 s):** "Hay mucho dinero en proteger el tren y nada en comprobar la orden. ADIF paga una licencia por puesto que sale más barata que contratar a una persona más. El riesgo es que Indra lo meta como un módulo de DaVinci, así que nuestro plan es entrar con un piloto antes de que se licite."

## Slide 3. Marco legal y responsabilidad

**Título:** Copi cumple la ley porque avisa y no decide. La responsabilidad sigue siendo de ADIF.

**Visual:** 4 bloques. Cada uno dice qué exige la norma y qué hace Copi para cumplirla.

1. **El protocolo: Reglamento de Circulación Ferroviaria** (RD 664/2015, [BOE-A-2015-8042](https://www.boe.es/buscar/act.php?id=BOE-A-2015-8042)).
   Copi no se inventa reglas: comprueba las que ya están en el BOE. Ejemplo: la marcha a la vista, a 40 km/h como máximo, que el RD 606/2023 reforzó (art. 1.5.1.4). En Urda la orden fue "con normalidad".
2. **Reglamento europeo de IA (UE 2024/1689).**
   Copi es probablemente un sistema de alto riesgo, porque es un componente de seguridad ferroviario. Esas obligaciones empiezan el 2 de agosto de 2027. Copi ya cumple el punto central, la supervisión humana: el controlador decide siempre. Además guarda un registro de cada aviso y tiene documentación técnica desde el piloto.
3. **Datos y trabajadores: RGPD, LOPDGDD art. 89 y Estatuto de los Trabajadores art. 64.4.d.**
   La ley solo permite grabar sonido en el trabajo si hay un riesgo de seguridad relevante y la grabación es proporcionada, y aquí lo hay. ADIF ya registra estas comunicaciones, así que Copi no graba nada nuevo. Hay que informar al comité de empresa y prohibir por contrato que se use para sancionar.
4. **Responsabilidad.**
   La Directiva 2016/798 y la Ley 38/2015 hacen a ADIF responsable de la seguridad de su red, y Copi no cambia eso. Si Copi falla, la Directiva 2024/2853 trata el software como un producto, así que la responsabilidad del proveedor se limita por contrato y con un seguro. La homologación se hace con la AESF (CSM-RA, EN 50126/50129), y es más ligera porque Copi no actúa sobre el freno ni sobre las señales.

**Frase final de la slide:** Copi no sustituye a nadie. Es una barrera más.

**Qué decir (25 s):** "Las reglas ya existen y están en el BOE: Copi solo comprueba que se cumplen. Como avisa y no actúa, el controlador sigue decidiendo, que es justo lo que pide el Reglamento de IA. Y como ADIF ya graba estas comunicaciones, no hay datos nuevos."

**Pregunta probable del jurado:** "¿Y si Copi no avisa y hay un accidente?" Respuesta: el responsable sigue siendo el mismo que hoy. Copi añade una barrera y no quita ninguna, y nuestra responsabilidad como proveedor queda cubierta por contrato y por seguro.

## Slides de reserva (para las preguntas)

- P&L 2027-2031 y gráfico de caja (está en el doc)
- Sensibilidad: si la licitación llega un año tarde, hacen falta entre 3,6 y 5,8 M€
- Pasos de la compra pública: piloto por Compra Pública de Innovación, luego licitación abierta
- Precedentes: HAAWAII detectó el 82 % de los errores de colación, pero con un 67 % de falsas alarmas. RSSB S363 en el Reino Unido.

## Pendiente

- [ ] Que un abogado o alguien de derecho revise la parte legal. Está citada de memoria y no está comprobada artículo por artículo.
- [ ] Comprobar que ADIF graba todas las comunicaciones de los CRC (lo damos por hecho en la slide 3).
- [ ] Decidir la duración del pitch para saber si la slide 1 y la 2 van juntas.
