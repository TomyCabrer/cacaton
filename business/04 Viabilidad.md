# 04 Viabilidad y riesgos

> Parte del análisis de negocio de Copi. Índice en [README](README.md). Doc vivo: https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W

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

## DaVinci y datos para las simulaciones

- DaVinci: plataforma de gestión de tráfico de ADIF en los centros de control. Diseñada por ADIF, desarrollada por Indra; la propiedad intelectual es de ADIF. Integra CTC, GSM-R, señalización, energía, ETCS y videovigilancia.
- Según infoLibre (dato aportado por Jaime): en Urda DaVinci mostraba la ocupación de la vía, pero no tiene ningún mecanismo para marcar o bloquear una orden verbal errónea.
- No hay API pública de DaVinci. El acceso real sería por contrato con ADIF (y probablemente Indra).
- Coste: no hay cifra pública de lo que costó desarrollarlo. Datos públicos: DaVinci en el centro de Albacete, 13,16 M€; extensión Pedralba-Ourense, 0,82 M€; DaVinci en Feve (2008), 13,4 M€; mantenimiento de CTC y DaVinci en 6 centros de alta velocidad, 32,7 M€ en 4 años (2026), con Indra como única oferta "por razones técnicas".
- Fuentes públicas para simular: Reglamento de Circulación Ferroviaria (RD 664/2015, en el BOE; el RD 606/2023 reforzó la marcha a la vista, art. 1.5.1.4), mapa en tiempo real de limitaciones de velocidad de ADIF, información de llegadas y salidas de ADIF, y conversaciones sintéticas generadas por protocolo.

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
