# 06 Legal: responsabilidad, datos y trabajadores

> Parte del análisis de negocio de Copi. Índice en [README](README.md). Doc vivo: https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W

Mensaje principal: **ADIF sigue siendo el responsable. Copi se vende como una barrera adicional, no como un sustituto.** Las normas de seguridad y de IA que Copi tiene que cumplir están en [05 Regulatory](05%20Regulatory.md).

## Responsabilidad

| Tema | Qué dice el marco | Qué implica para Copi |
| --- | --- | --- |
| Quién responde de la seguridad | La Directiva (UE) 2016/798 y la Ley 38/2015 del Sector Ferroviario hacen responsable al gestor de la infraestructura | ADIF sigue respondiendo de cada orden. Copi no le quita esa responsabilidad, reduce el riesgo |
| Si Copi falla o no avisa | La nueva Directiva (UE) 2024/2853 de responsabilidad por productos defectuosos trata el software y la IA como producto. Los Estados tienen que trasponerla antes del 9 de diciembre de 2026 | Existe riesgo para el proveedor. Se limita por contrato y con un seguro de responsabilidad civil profesional |
| Exceso de confianza | Si el controlador se relaja porque "Copi lo verá", la seguridad puede empeorar | Copi refuerza y no sustituye. Medirlo en el piloto y meterlo en la formación |

**Pregunta probable del jurado: "¿Y si Copi no avisa y hay un accidente?"** El responsable es el mismo que hoy. Copi añade una barrera y no quita ninguna, y nuestra responsabilidad como proveedor está cubierta por contrato y por seguro.

## Datos personales

| Tema | Qué dice el marco | Qué implica para Copi |
| --- | --- | --- |
| Grabar audio de trabajadores | El RGPD y la LOPDGDD (art. 89) solo permiten grabar sonido en el trabajo si hay riesgos relevantes para la seguridad y la grabación es proporcionada | Encaja, porque es seguridad ferroviaria. Además ADIF ya registra las comunicaciones, así que Copi procesa algo que ya existe (pendiente de confirmar para todos los CRC) |
| Tratamiento | Minimización y evaluación de impacto (RGPD) | Procesar en local en el centro de control, guardar lo mínimo y hacer la evaluación de impacto antes del piloto |

## Trabajadores y sindicatos

| Tema | Qué dice el marco | Qué implica para Copi |
| --- | --- | --- |
| Algoritmos en el trabajo | El Estatuto de los Trabajadores (art. 64.4.d) obliga a informar al comité de empresa de los algoritmos que afectan a las condiciones de trabajo | Presentar Copi a los representantes de los controladores antes del piloto |
| Riesgo de que lo vean como vigilancia | SEMAF, CCOO y UGT pueden rechazarlo | Prohibir por contrato el uso disciplinario. Venderlo como copiloto que protege al trabajador (le sirve de prueba a su favor tras un incidente). El SCF ya pide que la seguridad no dependa de la discrecionalidad individual |

## Propiedad intelectual y acceso a DaVinci

DaVinci lo diseñó ADIF y lo desarrolló Indra. La propiedad intelectual es de ADIF y no hay API pública, así que el acceso a los datos tiene que ir por un convenio en el contrato del piloto, con una arquitectura de solo lectura.

**El factor Indra**: en septiembre de 2026 ADIF adjudicó a Indra 32,7 M€ por 4 años de mantenimiento de los centros de alta velocidad (CTC y DaVinci). Indra fue la única oferta, "por razones técnicas". Cualquier integración con DaVinci pasa por Indra, que puede ser socio o competidor. Como referencia de precio, ese mantenimiento son unos 8 M€ al año para 6 centros, y Copi a 40.000 € por puesto serían unos 0,5 M€ al año por centro.

## Contrato con ADIF: cláusulas que hay que pedir

- Limitación de responsabilidad del proveedor y seguro de responsabilidad civil profesional.
- Copi es una ayuda: la decisión y la responsabilidad operativa siguen siendo de ADIF.
- Prohibición de usar Copi con fines disciplinarios.
- Convenio de acceso a datos (DaVinci, CTC, radio, registros de tren) de solo lectura.
- Propiedad de los modelos entrenados con datos del piloto.

---

Normas citadas de memoria. Ningún jurista las ha revisado artículo por artículo.
