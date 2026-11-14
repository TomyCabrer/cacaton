# Copi: análisis de mercado y financiero

Nov 14, 2026 · @Jaime

Copi es un supervisor de IA que vive en el centro de control. Escucha la radio y el resto de comunicaciones entre el controlador de ADIF y el maquinista, lee la telemetría y los registros de tren que llegan al centro, y hace dos cosas: 1) identifica qué protocolo se debería estar siguiendo en esa situación y 2) comprueba si se está siguiendo. Si no, avisa al controlador. No decide ni actúa, y no necesita nada instalado en el tren. El accidente de Urda (Toledo, 2026-10-28, al menos 69 muertos) nació de una orden del centro de control tras caer el LZB: es exactamente el fallo que Copi detecta.

- **Por qué ahora**: el plan de seguridad del Gobierno del 2026-11-03 ya incluye "un agente de IA" que vigile las conversaciones entre maquinista y controlador. Tres días después no tenía empresa, coste, plazo ni alcance. Copi es esa pieza, ya definida.
- **Mercado**: unos 10 M€ al año en España (\~240 puestos en los 19 centros de control de ADIF) y unos 125 M€ en Europa. Después, control aéreo.
- **Modelo**: licencia anual de 40.000 € por puesto de control, pagada por ADIF. Entrada con un piloto pagado en un centro.
- **Finanzas**: 12,7 M€ de ingresos y 52% de margen EBITDA en 2031. Break-even en 2029. Ronda de 2,5 M€.
- **Coste frente a lo que ya se gasta**: Copi en toda España cuesta menos al año que el 5% de un solo contrato de ERTMS (214 M€ en Murcia-Almería).
- **Riesgo principal**: acceso a los datos de ADIF, homologación y aceptación de los controladores, no la tecnología.

## El problema: 2026 ha demostrado que el eslabón débil es la decisión humana sin segunda mirada

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

## Modelo de negocio: licencia anual por puesto de control, comprada por ADIF

ADIF es el cliente y el que paga: el fallo de Urda está en su centro de control, y Copi se instala solo allí. Los operadores (Renfe, Iryo, Ouigo) se benefician sin pagar, lo que facilita que apoyen el piloto. El Ministerio de Transportes y la AESF son los aliados que empujan la compra.

| Concepto | Precio | Quién paga | Referencia |
| --- | --- | --- | --- |
| Licencia por puesto de control | 40.000 €/año | ADIF | Un operador N1 cobra 53.000 € brutos y un puesto 24/7 necesita unas 5 personas en turnos: Copi cuesta en torno al 12-15% de ese coste (estimación) |
| Implantación e integración | 30% de la licencia del primer año | ADIF | Conexión con DaVinci, la radio GSM-R y los registros de tren |
| Piloto pagado | 250.000-400.000 € | ADIF o fondos de innovación | Un centro, 6 a 12 meses, en paralelo sin interferir |

**Cómo se compra**

1. **Piloto** en un CRC por contrato menor o Compra Pública de Innovación, con cofinanciación de CDTI o Europe's Rail.
2. **Licitación** abierta (Ley de Contratos del Sector Público) para el despliegue nacional. Ciclo realista: 12 a 24 meses.
3. **Expansión** a otros gestores europeos con la referencia de ADIF y el mismo expediente de seguridad.

El valor que vendemos: un solo accidente como Urda supone al menos 69 vidas, la caída de viajeros de todo el sector y meses de limitaciones de velocidad. El despliegue nacional completo cuesta unos 10 M€ al año, el 0,2% de lo que ADIF invirtió en 2025.

## Modelo financiero: break-even en 2029 y una ronda de 2,5 M€

Con un piloto en 2027 y la licitación nacional en 2028, Copi llega a 12,7 M€ de ingresos y 6,7 M€ de EBITDA en 2031. El punto de caja más bajo es -1,8 M€ a final de 2028.

**Supuestos de despliegue**

| Año | Puestos ADIF | Europa | Hito |
| --- | --- | --- | --- |
| 2027 | 12 | 0 | Piloto pagado en 1 centro (300.000 €) |
| 2028 | 36 | 0 | Adjudicación nacional, 3 centros |
| 2029 | 90 | 1 piloto | Alta velocidad completa |
| 2030 | 180 | 2 gestores | Red convencional |
| 2031 | 240 | 3 gestores | España completa |

**Cuenta de resultados (M€)**

| Concepto | 2027 | 2028 | 2029 | 2030 | 2031 |
| --- | --- | --- | --- | --- | --- |
| Licencias España (40.000 € por puesto) | 0,00 | 1,44 | 3,60 | 7,20 | 9,60 |
| Implantación y piloto | 0,30 | 0,29 | 0,65 | 1,08 | 0,72 |
| Europa | 0,00 | 0,00 | 0,30 | 0,80 | 2,40 |
| **Ingresos** | **0,30** | **1,73** | **4,55** | **9,08** | **12,72** |
| Personal (8, 16, 28, 40, 50 personas a 65.000 €) | 0,52 | 1,04 | 1,82 | 2,60 | 3,25 |
| Certificación y seguridad | 0,25 | 0,50 | 0,40 | 0,40 | 0,40 |
| Cloud y cómputo | 0,08 | 0,15 | 0,30 | 0,50 | 0,70 |
| Servidores en cada centro (50.000 € por centro nuevo) | 0,05 | 0,10 | 0,23 | 0,38 | 0,25 |
| Ventas, licitaciones y legal | 0,15 | 0,30 | 0,50 | 0,80 | 1,00 |
| Generales | 0,10 | 0,15 | 0,25 | 0,35 | 0,45 |
| **Costes** | **1,15** | **2,24** | **3,50** | **5,02** | **6,05** |
| **EBITDA** | **-0,85** | **-0,51** | **1,05** | **4,06** | **6,67** |
| Margen EBITDA | n.s. | -30% | 23% | 45% | 52% |

Margen bruto del 86-93% desde 2028: es software, sin hardware en el tren. El coste principal es el equipo.

**Financiación**: ronda de 2,5 M€ en 2027, de la que unos 0,5 M€ pueden ser no dilutivos (CDTI, ENISA, convocatorias de Europe's Rail). Cubre el mínimo de -1,8 M€ con un 40% de margen. La caja incluye 90 días de cobro, normal en el sector público.

&#91;embedded content: modelo del equipo · caja acumulada 2027-2031, dos escenarios\]

**Sensibilidad**: si la licitación nacional se retrasa un año y se mantiene el plan de contratación, la necesidad sube a unos 5,8 M€. Congelando la plantilla en 16 personas hasta la adjudicación, se queda en unos 3,6 M€. Por eso cada ola de contratación se ata a un contrato firmado. Un precio de 30.000 € por puesto en vez de 40.000 € retrasa el break-even a 2030.

## Viabilidad: la tecnología existe hoy; el cuello de botella es el acceso a los datos de ADIF

**Cómo funciona Copi**

1. **Entrada**: radio GSM-R y resto de comunicaciones entre controlador y maquinista, más todo lo que ya llega al centro (DaVinci, CTC, telemetría y registros de tren, limitaciones temporales de velocidad).
2. **Transcripción**: voz a texto en español con ruido de radio y vocabulario ferroviario.
3. **Situación**: clasifica qué está pasando (por ejemplo, LZB caído en un tramo con trenes detenidos).
4. **Protocolo**: decide qué protocolo aplica. La base es el Reglamento de Circulación Ferroviaria (Real Decreto 664/2015), que en 2023 reforzó justo las condiciones de marcha a la vista, más las consignas internas de ADIF (por ejemplo la COI 01/25, que trata un tren detenido como obstáculo y obliga a imponer marcha a la vista ante cualquier duda sobre la ocupación de la vía).
5. **Comprobación**: compara cada orden y cada acción con ese protocolo. Ejemplos: zona limitada a 40 km/h y el controlador autoriza 50; o, como en Urda, el controlador ordena reanudar "con normalidad" cuando el reglamento exige el texto fijo "con Marcha a la Vista".
6. **Aviso**: marca la discrepancia al controlador en segundos. No bloquea nada; la decisión sigue siendo humana.

**Qué es factible y qué no**

| Pieza | Estado | Comentario |
| --- | --- | --- |
| Modelo de lenguaje para razonar sobre protocolos | Factible hoy | Fine-tuning con los modelos de Adaption sobre el reglamento y casos simulados |
| Voz a texto de radio ferroviaria | Factible, requiere ajuste | Ruido y jerga; se entrena con grabaciones del piloto |
| Datos de DaVinci | Bloqueante sin ADIF | DaVinci integra CTC, GSM-R, señalización, energía y ETCS, y su propiedad intelectual es de ADIF. No hay API pública: el acceso llega por contrato con ADIF (e Indra) |
| Datos para el hackathon | Factible | Reglamento en el BOE, mapa público de limitaciones de velocidad de ADIF y conversaciones sintéticas generadas por protocolo |
| Latencia | Factible | Un aviso en menos de unos segundos basta: en Urda el AVE avanzó un cuarto de hora después de la orden |

**Lo que España ya gasta en seguridad ferroviaria**

| Inversión | Importe | Alcance |
| --- | --- | --- |
| Mantenimiento de ADIF, 2026 a 2030 | 861 M€ en 2026, subiendo a 1.179 M€ en 2030 | Acuerdo con sindicatos tras Adamuz |
| ERTMS nivel 2 Murcia-Almería | 214 M€ | Unos 200 km |
| ERTMS nivel 2 Talayuela-Plasencia | 126,5 M€ | 70 km |
| Sustitución del LZB por ERTMS en Madrid-Sevilla | 77,55 M€ | La línea de Urda; retrasada a 2027 |
| ETCS embarcado (retrofit) | \~900.000 € por vehículo | Media europea 2022 |
| **Copi en toda España** | **\~10 M€ al año** | **240 puestos, todos los centros** |

Copi no sustituye nada de esto: cubre el hueco que estos sistemas dejan cuando caen y refuerza la decisión humana sin sustituirla.

## Marco legal y responsabilidad: ADIF sigue siendo el responsable; Copi debe venderse como barrera adicional

La decisión clave es si Copi entra en el expediente de seguridad de ADIF como barrera certificada o se vende como ayuda adicional. Recomendamos empezar como ayuda: se puede desplegar antes y la responsabilidad del operador no cambia.

| Tema | Qué dice el marco | Qué implica para Copi |
| --- | --- | --- |
| Responsable de la seguridad | La Directiva de seguridad ferroviaria (UE) 2016/798 y la Ley 38/2015 del Sector Ferroviario hacen responsable al gestor de infraestructura de la seguridad de su red | ADIF sigue respondiendo de cada orden. Copi no traslada esa responsabilidad, la reduce |
| Si Copi falla o no avisa | Nueva Directiva de responsabilidad por productos defectuosos (UE) 2024/2853: el software y la IA cuentan como producto. Los Estados la trasponen antes del 9 de diciembre de 2026 | Riesgo de responsabilidad del proveedor. Limitarlo por contrato y con un seguro de responsabilidad civil profesional |
| Ley europea de IA | Componente de seguridad de un producto ferroviario: probable alto riesgo. Las obligaciones para este tipo de sistemas empiezan el 2 de agosto de 2027 | Registro de cada aviso, supervisión humana, documentación técnica y gestión de riesgos desde el piloto |
| Grabación de audio de trabajadores | La ley española de protección de datos (LOPDGDD, art. 89) solo admite grabar sonido en el trabajo si hay riesgos relevantes para la seguridad y es proporcionado | Encaja: es seguridad ferroviaria. Mejor aún: ADIF ya registra las comunicaciones; Copi procesa lo que ya existe |
| Algoritmos y trabajadores | El Estatuto de los Trabajadores (art. 64.4.d) obliga a informar al comité de empresa de los algoritmos que afectan a las condiciones de trabajo | Presentar Copi a los representantes de los controladores antes del piloto. Prohibir por contrato su uso disciplinario |
| Exceso de confianza | Si el controlador se relaja porque "Copi lo verá", el sistema puede empeorar la seguridad | Copi refuerza, no sustituye. Medirlo en el piloto y formarlo como parte del procedimiento |

**El factor Indra**: en septiembre de 2026 ADIF adjudicó a Indra 32,7 M€ por 4 años de mantenimiento de los centros de alta velocidad (CTC y DaVinci). Indra fue la única oferta "por razones técnicas". Cualquier integración con DaVinci pasa por Indra, que puede ser socio o competidor. Referencia de precio: ese mantenimiento son unos 8 M€ al año para 6 centros; Copi a 40.000 € por puesto sería unos 0,5 M€ al año por centro.

## Riesgos: el mayor no es técnico, es la homologación y los sindicatos

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Homologación de seguridad (AESF, análisis de riesgos CSM-RA, normas CENELEC EN 50126 y EN 50129) | Alto: sin ella no hay despliegue | Diseño "solo avisa": no actúa sobre freno ni señales, lo que baja el nivel de integridad exigido. Evaluador independiente desde el piloto (presupuestado en certificación) |
| Ley europea de IA | Medio: probable sistema de alto riesgo por ser componente de seguridad ferroviario | Tratarlo como alto riesgo desde el día 1: registro de decisiones, supervisión humana, documentación técnica |
| Rechazo de maquinistas y controladores (SEMAF, CCOO, UGT) | Alto: pueden verlo como vigilancia laboral | Posicionarlo como copiloto que protege al trabajador (prueba a su favor tras un incidente). Sin uso disciplinario por contrato. Sindicatos en el piloto |
| Ciclo de compra pública lento | Alto en caja (ver sensibilidad) | Compra Pública de Innovación y fondos europeos para el piloto. Contratación atada a contratos |
| Falsas alarmas | Medio: si molesta, lo apagan | Piloto en paralelo sin avisos en tiempo real los primeros meses, solo para medir precisión. Referencia: HAAWAII, en aviación, tuvo un 67% de falsas alarmas. Copi gana precisión porque cruza la voz con la telemetría |
| Acceso a datos de ADIF (DaVinci, CTC, radio, registros de tren) | Alto: sin datos no hay producto | Convenio de datos en el contrato del piloto. Arquitectura de solo lectura |
| Protección de datos (grabaciones de radio y del puesto) | Medio | Procesamiento en local, retención mínima, evaluación de impacto RGPD |
| Un fabricante lo copia | Medio a largo plazo | Velocidad, datos propios del piloto y alianza con un integrador |

Preguntas abiertas para el equipo:

- [ ] Confirmar el número real de puestos por centro de control (memoria de ADIF)
- [ ] Elegir el modelo de Adaption y ver si puede correr en local en el centro de control
- [ ] Validar el precio de 40.000 € por puesto con alguien de ADIF o un exjefe de CRC

## Fuentes

Cifras propias (precios, despliegue, costes) son supuestos del equipo, no datos publicados. Angrois (2013) se cita de memoria.

- [Euronews, accidente de Toledo (2026-10-28)](https://es.euronews.com/2026/10/28/oscar-puente-considera-inexplicable-que-el-centro-de-control-autorizara-al-ave-a-reanudar-)
- [Xataka, caída de viajeros de alta velocidad tras Adamuz](https://www.xataka.com/movilidad/adamuz-alta-velocidad-espana-no-remonta-ha-perdido-casi-20-viajeros-cuatro-meses)
- [Ara, accidente de Adamuz](https://es.ara.cat/sociedad/39-muertos-150-heridos-choque-trenes-alta-velocidad-cordoba_1_5622100.html)
- [El Observador, accidente de Gelida](https://www.elobservador.com.uy/espana/sucede/al-menos-15-heridos-al-descarrilar-un-tren-gelida-barcelona-la-caida-un-muro-contencion-n6031702)
- [Ara, CRC de Barcelona: 14 controladores, 1.200 trenes](https://es.ara.cat/sociedad/movilidad/14-controladores-1-200-trenes-funciona-sala-dirige-circulacion-cercanias_130_5710964.html)
- [Artículo14, centro H24 y 20 CRC](https://www.articulo14.es/politica/oscar-puente-ministro-de-transportes-desde-el-centro-de-control-h24-estoy-tratando-de-obtener-la-informacion-sobre-lo-ocurrido-20261028.html)
- [El Periódic, CRC de Valencia (1.761 km)](https://www.elperiodic.com/valencia/adif-licita-redaccion-proyecto-obras-renovacion-tecnologica-centro-regulacion-circulacion-situado-valencia-fuente-luis_694058)
- [La Moncloa, acuerdo con sindicatos ferroviarios (2026-02-09)](https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/transportes-movilidad-sostenible/Paginas/2026/090226-transportes-acuerdo-sindicatos-ferroviarios.aspx)
- [Deia, claves del acuerdo: 861 M€ de mantenimiento](https://www.deia.eus/economia/2026/02/09/claves-acuerdo-transportes-maquinistas-desconvocar-renfe-10680263.html)
- [CNMC, inversión ejecutada por ADIF en 2025](https://www.cnmc.es/sites/default/files/6703004.pdf)
- [CNMC, informe anual ferroviario 2025](https://cnmc.es/prensa/inf-anual-ferro-25-20260717)
- [El Español, cuotas de Renfe, Iryo y Ouigo](https://www.elespanol.com/invertia/observatorios/movilidad/20260326/ouigo-roba-cuota-renfe-iryo-mayoria-corredores-alta-velocidad/1003744183489_0.html)
- [Voz Pópuli, plantilla de Renfe 2024](https://www.vozpopuli.com/economia/telecomunicaciones/la-igualdad-en-los-talleres-de-renfe-solo-el-5-de-los-mecanicos-son-mujeres.html)
- [Global Market Insights, mercado de señalización](https://www.gminsights.com/industry-analysis/railway-signaling-system-market)
- [The Business Research Company, IA ferroviaria](https://www.thebusinessresearchcompany.com/report/railway-artificial-intelligence-ai-global-market-report)
- [Rail Engineer, coste de ETCS](https://www.railengineer.co.uk/is-etcs-affordable/)
- [Tech.eu, ronda de Futurail](https://tech.eu/2025/09/23/the-next-autonomy-revolution-futurail-secures-eur75m-to-tackle-rail-inefficiences/)
- [Kurrant, ronda de Purple Transform](https://kurrant.com/kurrantly-news/purple-transform-secures-4-5m-to-boost-rail-safety-with-ai-technology/)
- [Eurostat, accidentes ferroviarios en la UE](https://ec.europa.eu/eurostat/statistics-explained/index.php/Railway_safety_statistics_in_the_EU)

Añadidas tras definir el enfoque (solo centro de control):

- [Voz Pópuli, la CIAF pidió medidas contra el fallo humano tras el incidente de 2024](https://www.vozpopuli.com/economia/transporte/la-ciaf-pidio-medidas-tecnicas-para-mitigar-el-fallo-humano-tras-un-incidente-similar-al-de-urda-en-2024.html)
- [Qué!, tres errores del accidente de Urda](https://www.que.es/2026/10/29/errores-accidente-urda-lzb-adif/)
- [infoLibre, el papel del centro de control de ADIF en Urda](https://www.infolibre.es/politica/papel-centro-control-adif-accidente-urda-pone-duda-gestion-alta-velocidad_1_2239187.html) (leída en una copia de archive.today del 29 de octubre de 2026)
- [Indra, ficha de DaVinci](https://www.indracompany.com/sites/default/files/davinci_control_y_gestion.pdf)
- [BOE, Reglamento de Circulación Ferroviaria (Real Decreto 664/2015)](https://www.boe.es/eli/es/rd/2015/07/17/664)
- [BOE, Real Decreto 606/2023 que refuerza la marcha a la vista](https://www.boe.es/boe/dias/2023/07/12/pdfs/BOE-A-2023-16156.pdf)
- [Railmarket, ERTMS Murcia-Almería (214 M€)](https://railmarket.com/news/technology-innovation/20355-sbb-lifts-speed-limit-near-gotthard-tunnel)
- [Railwaynews, ERTMS Madrid-Extremadura (126,5 M€)](https://railwaynews.net/madrid-extremadura-high-speed-ertms-level-2-rail-tech-advancements.html)
- [Demócrata, sustitución del LZB en Madrid-Sevilla (77,55 M€)](https://www.democrata.es/en/economy/94-million-to-renew-the-security-of-madrid-sevilla-award-thales-low-bid-and-pending-points/)
- [Railwaynews, coste del ETCS embarcado](https://railwaynews.net/?p=284789)

* [Indra, contrato de mantenimiento de los centros de alta velocidad (32,7 M€, 2026)](https://www.indragroup.com/en/news/indra-set-to-consolidate-its-role-as-adifs-technological-partner-by-maintaining-its-advanced-high-speed-rail-traffic-management-technology-for-a-further-four-years)
* [Railway News, Indra mantendrá la tecnología de tráfico de ADIF](https://railway-news.com/spain-indra-to-maintain-adif-high-speed-rail-traffic-management-technology/)
* [Indra, DaVinci en el centro de Albacete (13,16 M€)](https://www.indragroup.com/en/news/46215-2)

- [Infobae, plan de seguridad del Gobierno con IA (2026-11-03)](https://www.infobae.com/espana/2026/11/03/oscar-puente-anuncia-un-plan-de-seguridad-ferroviaria-con-inteligencia-artificial-doble-validacion-de-ordenes-y-mejora-de-condiciones-laborales-tras-el-accidente-de-urda/)
- [Voz Pópuli, el plan sigue sin empresa ni coste (2026-11-06)](https://www.vozpopuli.com/espana/politica/un-informe-europeo-desmonta-el-plan-de-ferroviario-del-gobierno-los-gemelos-digitales-no-predicen-fallos-en-tiempo-real.html)
- [Aquí Madrid, Urda minuto a minuto](https://aqui.madrid/urda-minuto-a-minuto-lo-que-dijo-puente-y-lo-que-quedo-sin-respuesta)
- [Demócrata, 104 telefonemas y reacción de los sindicatos](https://www.democrata.es/actualidad/indignacion-filtracion-audios-urda-sindicatos-denuncian-senalamiento-controladores-atocha/amp/)
- [HerQles, la CIAF y 15 incidentes de 2023 a 2025](https://herqles.com/2026/10/29/informe-ciaf-factor-humano-urda/)
- [Voz Pópuli, sueldo del operador y doble verificación (2026-11-04)](https://www.vozpopuli.com/economia/transporte/puente-pone-a-los-operarios-de-adif-la-diana-de-las-culpas-antes-de-marcharse-de-transportes.html)
- [YouGov, confianza en la alta velocidad tras Urda (2026-11-12)](https://yougov.com/es-es/articulos/55957-adamuz-y-urda-lo-que-opinan-los-espanoles-tras-dos-accidentes-ferroviarios)
- [CORDIS, proyecto HAAWAII](https://cordis.europa.eu/project/id/884287/reporting)
- [RSSB, proyecto S363 sobre IA en comunicaciones de seguridad](https://www.rssb.co.uk/research-catalogue/CatalogueItem/S363)
- [Irish Times, Bad Aibling (2016)](https://www.irishtimes.com/news/world/europe/human-error-blamed-for-german-train-crash-1.2536854)

Marco legal: las normas citadas (Directivas 2016/798 y 2024/2853, Ley de IA, LOPDGDD art. 89, Estatuto de los Trabajadores art. 64.4.d) se citan de memoria y no se han revisado con un jurista.
