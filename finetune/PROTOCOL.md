# Protocol: LZB transmission failure, Meta 000 (occupied block)
Source: RCF (RD 664/2015) annex 5ET3, arts. 5ET3.4.3.4, .5, .1, 5.2.1.3 (verify vs current BOE consolidated text; amended by RD 606/2023).
Not public: Adif internal controller checklists. Rules below are a hackathon reconstruction.

| ID | Actor | Rule |
|----|-------|------|
| R1 | Driver | On Meta 000: press LIBERAR within 8 s, brake, stop. |
| R2 | Driver | Report location to RC (Responsable de Circulacion) once stopped. |
| R3 | RC | After checks, authorize with telefonema 5ET3.2: continue under BSL with "Marcha a la Vista" to next signal. NOT "marcha normal". |
| R4 | Driver/RC | 5ET3.2 never implies authorization to overrun signals; overrun needs separate authorization (5ET3.1 / 5.2.1.3). |
| R5 | Driver | Resume only after RC authorization. |
| R6 | Driver | Disconnect/reconnect LZB only with RC authorization (5ET3.3). |

Meta 40 = block free: driver presses LIBERAR, brakes, watches lineside signals; no stop needed (compliant distractor).
Excluded from hard labels (inference, no quoted rule): "RC did not verify preceding train position".
