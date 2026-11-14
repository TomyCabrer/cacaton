---
type: project
status: hackathon en curso
org: Imperial AI Hackathon 2026
created: 2026-11-14
tags: [project, hackathon]
aliases: []
related: ["[[Projects Index]]"]
---
# Copi

## Qué es

Supervisor de IA para los centros de control ferroviario de ADIF. Proyecto del Imperial AI Hackathon 2026, equipo de 4. Sponsor principal del hackathon: Adaption (usamos sus modelos para el fine-tuning).

Copi no toma decisiones ni actúa. Está activo en el centro de control y supervisa a las dos personas (controlador de ADIF y maquinista):

1. Identifica qué protocolo se debería estar siguiendo dada la situación.
2. Determina si se está siguiendo o no. Si no, lo marca al controlador.

Supuesto de partida: los protocolos son correctos; el fallo está en que una persona no los sigue al 100%.

## Enfoque (lo que dijo Jaime, 2026-11-14)

- **Entradas**: escucha la radio y el resto de medios de comunicación entre controlador y maquinista. Usa también la telemetría, los registros de tren y toda la información que llega al centro de control.
- **Por qué una IA**: es perfecta siguiendo "cómo se debe actuar en cada protocolo"; una persona no lo es en tareas rutinarias y además tiene fatiga. Con Copi supervisando, el controlador trabaja con menos estrés porque sabe que si se equivoca, Copi lo marcará.
- **Qué detecta**: órdenes que contradicen el protocolo, malentendidos, órdenes contradictorias, cualquier cosa que pueda generar una situación peligrosa. Ejemplo: en una zona el maquinista debe ir a 40 km/h y el controlador le dice que vaya a 50; Copi lo marca al controlador.
- **Dónde se instala**: solo en el centro de control. No en el tren, porque las comunicaciones en vía pueden fallar y no llegaría la información. El tren no necesita hardware.
- **Cliente**: ADIF y organismos públicos del estilo (Ministerio de Transportes). Sin modelo de precios previo; lo propuse yo (40.000 € por puesto y año).
- **Expansión**: fuera de España, y después aviación (supervisar que los controladores aéreos siguen los protocolos).
- **Idea de Jaime para el pitch**: comparar con lo que España se ha gastado en sistemas de seguridad ferroviaria.

## Equipo y reparto

- Jaime: financials, market considerations, feasibility (parte de negocio).
- Sobri: implementación del modelo, fine-tuning con modelos de Adaption.
- Tomy y Michel: la plataforma.

## Entregables del hackathon

- Presentación.
- Entregable con simulaciones.
- MVP.

La parte financiera no es lo que más pesa, pero conviene enseñar que el negocio está pensado.

## Análisis de mercado y financiero

Documento compartible: [Copi: análisis de mercado y financiero](https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W) (Claude Docs). **La versión buena es el doc**: ahí edita el equipo. Esta nota solo guarda el resumen y se actualiza cuando cambien las cifras clave.

Cifras clave (v2, solo centro de control):
- Caso de uso: accidente de Urda (Toledo), 2026-10-28, al menos 69 muertos (el ministro dio 64 el primer día). Cae el LZB en 63 km y el centro de Atocha autoriza al AVE a reanudar con normalidad en vez de en marcha a la vista.
- La CIAF ya avisó tras un incidente en 2024 (Cuenca-Fernando Zóbel) de que la única barrera era la comprobación visual del responsable de circulación, que "depende completamente del factor humano".
- Mercado: ~10 M€/año en España (~240 puestos en ~20 centros de ADIF), ~125 M€ en Europa.
- P&L: ingresos 0,3 / 1,7 / 4,6 / 9,1 / 12,7 M€ (2027-2031). Break-even 2029. EBITDA 2031 6,7 M€ (52%).
- Caja: mínimo -1,8 M€ en 2028. Ronda de 2,5 M€. Con licitación un año tarde: 3,6 a 5,8 M€.
- Coste de la seguridad actual: ERTMS Murcia-Almería 214 M€, Talayuela-Plasencia 126,5 M€, LZB a ERTMS Madrid-Sevilla 77,55 M€; mantenimiento ADIF 861 M€ en 2026.

## Narrativa y noticias

Recopilación de prensa con los mejores argumentos para el pitch: [[Copi narrativa y noticias]]. Lo más fuerte: el plan del Gobierno del 2026-11-03 ya pide un agente de IA que vigile las conversaciones maquinista-controlador (sin empresa ni coste aún); otro maquinista corrigió al centro ("tiene que ser marcha a la vista"); 17 minutos con los dos trenes en pantalla; confianza en el AVE del 67 % al 35 % (YouGov). Puente dimitió el 2026-11-03. Urda la investiga la AITAT (sustituyó a la CIAF en agosto de 2024).

## DaVinci y datos para las simulaciones

- DaVinci: plataforma de gestión de tráfico de ADIF en los centros de control. Diseñada por ADIF, desarrollada por Indra; la propiedad intelectual es de ADIF. Integra CTC, GSM-R, señalización, energía, ETCS y videovigilancia.
- Según infoLibre (dato aportado por Jaime): en Urda DaVinci mostraba la ocupación de la vía, pero no tiene ningún mecanismo para marcar o bloquear una orden verbal errónea.
- No hay API pública de DaVinci. El acceso real sería por contrato con ADIF (y probablemente Indra).
- Coste: no hay cifra pública de lo que costó desarrollarlo. Datos públicos: DaVinci en el centro de Albacete, 13,16 M€; extensión Pedralba-Ourense, 0,82 M€; DaVinci en Feve (2008), 13,4 M€; mantenimiento de CTC y DaVinci en 6 centros de alta velocidad, 32,7 M€ en 4 años (2026), con Indra como única oferta "por razones técnicas".
- Fuentes públicas para simular: Reglamento de Circulación Ferroviaria (RD 664/2015, en el BOE; el RD 606/2023 reforzó la marcha a la vista, art. 1.5.1.4), mapa en tiempo real de limitaciones de velocidad de ADIF, información de llegadas y salidas de ADIF, y conversaciones sintéticas generadas por protocolo.

## Protocolo de Urda (escenario para la demo)

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

## Presentación (estructura propuesta, 2026-11-14)

Plan del equipo: accidente, colaboración humano-IA, slide de negocio (Jaime), demo Tomy (controlador) y Michel (maquinista), slide legal.
Propuesta: 1 Urda; 2 el hueco (nadie comprueba la orden verbal); 3 Copi y la colaboración humano-IA; 4 demo en directo con 3 casos (Urda "con normalidad" frente a "con Marcha a la Vista", 50 frente a 40 km/h, repetición de la orden mal entendida); 5 negocio y mercado (Jaime); 6 marco legal (RCF como fuente de los protocolos, Reglamento de IA, RGPD y LOPDGDD art. 89, responsabilidad); 7 cierre y siguientes pasos. Lo regulatorio va solo en la slide legal para no repetir.

Slides de Jaime (mercado, competencia y negocio, legal) con títulos, visuales y qué decir: [[Copi slides negocio y legal]].

## Estado

- 2026-11-14: análisis v1 (puesto + cabina) y después v2 (solo centro de control).
- Repo del equipo: https://github.com/TomyCabrer/cacaton. No lo he podido abrir: parece privado y aquí no está la CLI de GitHub.

## Siguientes pasos
- [ ] Acceso al repo (que Tomy lo haga público o pasarme los archivos)
- [ ] Confirmar puestos por centro de control (memoria de ADIF)
- [ ] Elegir el modelo de Adaption y ver si puede correr en local
- [ ] Validar el precio de 40.000 € por puesto
- [ ] Pasar las cifras clave a la presentación

## Log
- 2026-11-14: estructura de las 3 slides de Jaime en [[Copi slides negocio y legal]]. Conversación exportada en `2026-11-14 Conversación exportada.txt` (esta carpeta), para Don Juan.
- 2026-11-14: un agente recopiló prensa en [[Copi narrativa y noticias]]. Doc actualizado: plan del Gobierno con IA como "por qué ahora" y como competidor probable (vía Indra), cronología de 17 minutos, HAAWAII y RSSB como precedentes, sueldo de operador N1 como referencia de precio.
- 2026-11-14: añadido el protocolo de Urda (RCF + consigna COI 01/25) como escenario de demo, a partir del artículo de infoLibre. Doc actualizado: 19 CRC, argumento "más personas no lo arreglan", fatiga.
- 2026-11-14: añadida al doc la sección de marco legal y responsabilidad (Directiva de seguridad ferroviaria, responsabilidad por productos 2024/2853, Ley de IA, LOPDGDD art. 89, Estatuto art. 64.4.d) y el factor Indra.
- 2026-11-14: creado. Precios y despliegue son hipótesis propias; el modelo está en el doc.
- 2026-11-14: decidido que el análisis vive solo en Claude Docs (editable por el equipo); en la vault, resumen y enlace, sin copia completa.
- 2026-11-14: Jaime aclara el enfoque: solo centro de control, sin hardware en el tren, cliente ADIF. Doc rehecho: fuera la licencia por cabina, precio 40.000 € por puesto, nueva sección de viabilidad y coste de la seguridad actual.

## Relacionado
- [[Projects Index]]
