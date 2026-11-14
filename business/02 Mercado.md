# 02 Mercado y competencia

> Parte del análisis de negocio de Copi. Índice en [README](README.md). Doc vivo: https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W

## Mercado: unos 10 M€ al año en España y unos 125 M€ en Europa

Copi se vende por puesto de control en los centros del gestor de infraestructura. No va en el tren: la cobertura de comunicaciones en la vía no es fiable, y todo lo que necesita ya llega al centro. El mercado español completo vale unos 10 M€ de ingresos recurrentes al año, y Europa unas 13 veces más.

**Quién hay en España**

- **ADIF y ADIF AV**: gestor de la infraestructura. 19 centros de regulación de circulación (CRC) abiertos 24 horas, tres de ellos en Madrid (Atocha, Delicias y Villaverde), que reportan al centro H24. Por cada tres factores de circulación hay un controlador al lado que los supervisa, y por encima un técnico. El CRC de Barcelona tiene 14 puestos para unos 900 km y 1.200 trenes al día; el de Valencia cubre 1.761 km.
- **Operadores de viajeros**: Renfe (unos 19.900 empleados en 2024), Iryo y Ouigo. En Madrid-Barcelona Renfe tiene el 56,4% y Iryo el 24%. La alta velocidad movió 44,5 M de viajeros en 2025 (+12%).
- **Operadores de mercancías**: Renfe Mercancías, Captrain, Medway y otros. Segmento secundario.
- **Dinero disponible**: ADIF ejecutó 5.230 M€ de inversión en 2025. Tras Adamuz, el Gobierno pactó con los sindicatos 861 M€ de mantenimiento en 2026 (hasta 1.179 M€ en 2030) y 2.400 plazas extra para seguridad en ADIF.

**Tamaño (bottom-up)**

| Nivel | Qué incluye | Puestos | Ingreso recurrente/año |
| --- | --- | --- | --- |
| TAM Europa (UE + Reino Unido + Suiza + Noruega) | Mismo modelo escalado por longitud de red (España es \~7,5% de la red de la UE) | \~3.200 | \~125 M€ |
| SAM España | Todos los puestos de los centros de ADIF y el H24 | \~240 | \~10 M€ |
| SOM 2031 | España completa (9,6 M€) + 2 o 3 gestores europeos en piloto (2,4 M€) | 240 en España | 12 M€ |
| Siguiente mercado | Control aéreo: mismo problema (controlador que debe seguir protocolos), clientes como ENAIRE | Sin estimar | Sin estimar |

Supuestos: 40.000 € por puesto y año (ver precios). Los 240 puestos salen de 19 centros con una media de unos 12,5 puestos (Barcelona tiene 14). Hay que confirmarlo con ADIF.

Comprobación top-down: el TAM europeo de Copi (\~125 M€) es menos del 1% del mercado mundial de señalización (19.600 M$ en 2025, +8,9% anual) y alrededor del 4-5% del mercado de IA ferroviaria (unos 3.000 M$ en 2025, +15-18% anual). Es un nicho creíble, no un mercado inflado.

**Por qué ahora**: el 2026-11-03 el Gobierno anunció un plan con alertas automáticas, libros electrónicos de telefonemas, doble validación en modo degradado y un agente de IA que vigile las conversaciones entre maquinistas y controladores. Ese mismo día dimitió el ministro Óscar Puente. El 2026-11-06 aún no había empresa, coste ni plazo, ni se sabía si la IA solo recomendará. La demanda existe y la especificación está abierta. La confianza en la alta velocidad cayó del 67% tras Adamuz al 35% tras Urda, y solo el 18% cree que la infraestructura está bien supervisada (YouGov).

## Competencia: nadie vigila la coherencia entre controlador y maquinista

Todo lo que existe protege al tren frente a la señal o vigila a una sola persona. Copi es el único que cruza lo que ordena el controlador con lo que hace el maquinista y con el estado real de la vía.

| Alternativa | Ejemplos | Qué hace | Qué no hace |
| --- | --- | --- | --- |
| Protección automática del tren | ASFA, LZB, ERTMS/ETCS (Siemens, Alstom, Hitachi, CAF) | Frena si el tren supera la velocidad o rebasa una señal | Cuando cae (Toledo) se vuelve a procedimientos manuales sin supervisión. Retrofit ETCS: \~900.000 € por vehículo |
| Gestión de tráfico (CTC/TMS) | DaVinci (diseñado por ADIF, desarrollado por Indra), Siemens | Muestra y regula la circulación | No juzga si una orden verbal del controlador cumple el protocolo |
| Vigilancia del maquinista | Hombre muerto, detectores de fatiga (Mirasys) | Detecta somnolencia o distracción | No sabe qué orden recibió ni si es coherente |
| Conducción autónoma | Futurail (7,5 M€ de seed, 2025), OTIV | Sustituye al maquinista | Años de homologación y rechazo sindical |
| Seguridad de vía con IA | Purple Transform (4,5 M£) | Detecta intrusos y riesgos en la vía | No mira las decisiones humanas |

**Lo que viene**

- **El plan del Gobierno (2026-11-03)** pide un agente de IA que vigile las conversaciones. Es nuestro mejor aliado y nuestro competidor más probable: si ADIF lo licita como módulo de DaVinci, Indra parte con ventaja. Hay que llegar antes con un piloto y una especificación propia ("recomienda, no actúa").
- **Precedentes en aviación y en el Reino Unido**: el proyecto europeo HAAWAII (DLR, NATS, Isavia, 1,8 M€) detectó el 82% de los errores de colación (la repetición de la orden por el piloto), pero con un 67% de falsas alarmas. En el Reino Unido, RSSB estudia desde 2023 usar IA para supervisar las comunicaciones de voz en seguridad (proyecto S363). La idea es viable; el reto es la precisión.

**Ventaja de Copi**

- **No actúa, solo avisa**: no toca el freno ni la señalización. Eso abarata la homologación frente a un sistema que actúa y facilita que ADIF lo pruebe en paralelo.
- **Cubre el modo degradado**: justo cuando caen LZB o ERTMS, que es cuando hoy no hay red de seguridad.
- **Se instala sin tocar el tren**: todo ocurre en el centro de control con datos que ya llegan allí. Mucho más barato que un retrofit ETCS.
- **Los grandes no lo harán rápido**: Siemens o Alstom venden señalización con ciclos de 5 a 10 años. Un copiloto de supervisión les canibaliza argumentos de venta.

Riesgo competitivo real: que un fabricante de señalización o Indra lo añada como módulo. Respuesta: ser socio o objetivo de compra, no rival.
