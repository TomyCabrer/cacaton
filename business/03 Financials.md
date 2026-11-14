# 03 Financials: modelo de negocio y modelo financiero

> Parte del análisis de negocio de Copi. Índice en [README](README.md). Doc vivo: https://claude.ai/artifact/JndrN4HG4TVKbif7ry9E4W

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

**Caja acumulada (M€, fin de año)**

| Escenario | 2027 | 2028 | 2029 | 2030 | 2031 |
| --- | --- | --- | --- | --- | --- |
| Base | -0,93 | -1,79 | -1,45 | 1,48 | 7,24 |
| Licitación un año tarde | -0,93 | -2,77 | -4,76 | -5,79 | -4,02 |

La caja toca fondo en -1,8 M€ en 2028 y la ronda de 2,5 M€ lo cubre.


**Sensibilidad**: si la licitación nacional se retrasa un año y se mantiene el plan de contratación, la necesidad sube a unos 5,8 M€. Congelando la plantilla en 16 personas hasta la adjudicación, se queda en unos 3,6 M€. Por eso cada ola de contratación se ata a un contrato firmado. Un precio de 30.000 € por puesto en vez de 40.000 € retrasa el break-even a 2030.
