# What happened: Spain's January 2026 rail accidents

Research notes behind Copi. Compiled 14 Nov 2026 from press reports and Wikipedia timelines that cite CIAF and court documents. **The CIAF (Spain's rail accident investigation commission) had not published its final Adamuz report at the time of writing; every cause finding below is provisional.** Sources disagree on some figures; the disagreements are listed rather than resolved.

## 1. Adamuz (Córdoba), Sunday 18 January 2026: 46 dead

**What:** On the Madrid–Sevilla high-speed line, the last three coaches of **Iryo 6189** (Málaga → Madrid, 294 on board) derailed at about PK 318.7 near Adamuz and fouled the adjacent track. Seconds later **Renfe Alvia 2384** (Madrid → Huelva, 184 on board), travelling the other way at 205–210 km/h, hit them. The Alvia's first two coaches ran about 200 m further and fell down a ~4 m embankment. 46 people died, 37 of them on the Alvia, including its driver. Autopsies found 45 of the 46 died on impact. Injury counts range from 152 to 292 depending on the source.

**Second by second** (es.wikipedia timeline, from CIAF and court documents):

| Time | Event |
|---|---|
| 19:43:19 | Iryo enters the section with the broken rail |
| 19:43:34 | Coach 6, first axle, derails just past the break |
| 19:43:36 | Iryo onboard systems report infrastructure faults and loss of several systems |
| 19:43:37 | Signal S613 on the other track drops to STOP (loss of point detection). The Alvia starts emergency braking |
| 19:43:42 | Alvia event recorder stops: probable collision |
| 19:43:45 | Catenary voltage drop in the area |

About **8 seconds** from derailment to impact (other sources say 9 or 20). At ~205 km/h a high-speed train needs well over 2 km to stop. **No human or advisory system could have prevented the collision in that window.** The automatic layer (signal S613) did react.

**The next 50 minutes**, where human working memory broke down:

| Time | Event |
|---|---|
| 19:44:51 | First 112 call, from an Iryo passenger |
| 19:45:02 | Iryo driver calls the control centre: "un enganchón", thinks he snagged the catenary |
| 19:46:07 | Another train (Avlo 2181) reports it is stopped without voltage |
| 19:48:39 / 19:48:51 | Control centre calls the Alvia driver twice. No answer (he was dead) |
| 19:49:35 | Iryo driver: "es un descarrilamiento y estoy invadiendo la vía contigua… necesito que paren el tráfico". Control centre: "no hay ningún tren llegando" |
| 19:50 | Adif mobilises emergency services |
| 19:55 | First 112 call from the Alvia |
| 20:02 | First medical unit reaches the **Iryo** |
| 20:06:16 | Iryo driver tells the control centre the Alvia also derailed: the earliest control-centre mention of the Alvia in the public timeline |
| 20:09:58 | Adif tells 112 Madrid the Alvia did **not** derail, only braked hard (wrong) |
| 20:12:27 | Alvia train manager: "medio tren volcado" (half the train overturned) |
| 20:16:29 | Adif Sevilla confirms a second derailed train |
| ~20:35 | First medical team reaches the **Alvia**, about 52 minutes after the collision |

Every piece of the picture existed by 19:49 (signal drop, power loss, train-describer position, two unanswered calls, a derailment report). It was spread across phone calls, screens and people, and nobody assembled it for another 17–27 minutes.

**The 22 hours before**, where the lives were:

- **Aug 2025:** SEMAF (drivers' union) warned Adif about wear and vibration on the line, including near the site. Drivers later said this was about comfort, not safety.
- **~Nov 2025:** a track inspection recorded a small vertical acceleration near the site. No action.
- **17 Jan, 21:46:** the track circuit's voltage dropped from 2.0 V to 1.5 V. The alarm threshold was 0.78 V, so nothing fired. The Civil Guard called it "an electrical change compatible with a rail break". Adif's president disputed this.
- **17–18 Jan:** 1 of 19 drivers who ran the section felt a "ligera vibración" and gave it no importance. Not reported.
- **18 Jan, 17:21, 19:01 and 19:09:** three trains crossed the break. All later showed wheel notches like the crashed train's.
- **Cause (provisional):** a fractured weld on track 1 (PK 318+681) joining 1989 and 2023 rail sections; fatigue cracking starting at the rail foot. The Civil Guard also criticised an improper weld kit, "overly relaxed" track-circuit alarm settings, inexperienced inspectors, and handheld inspection devices that could not upload data. CIAF's lab analysis was still pending in July 2026.

Every one of those signals was below its own threshold, held in a different system or person, and never put next to the others.

**Afterwards:** line reopened 17 Feb 2026 with speed restrictions; the safety agency AESF tightened emergency communications (direct line to the traffic controller plus a backup); CIAF asked Adif for rail-break risk measures and is reviewing SNCF's approach; an independent investigation authority got its statute (RD 141/2026); the EPPO is examining possible misuse of EU maintenance funds.

## 2. Gelida (Barcelona), Tuesday 20 January 2026: 1 dead

During heavy storms, a concrete retaining wall (separating the AP-7 motorway from the tracks) collapsed onto the line. A Rodalies R4 train at about 60 km/h hit it. A trainee driver in the cab died; 37 were injured. The CIAF found from the recorder that the driver had **about 5 seconds** to brake. Open questions: who owned and inspected the wall, and whether rainfall should have triggered precautionary restrictions. Same pattern as Adamuz: seconds at the end, hours of weak signals (rain totals, the asset's condition) before.

## 3. Context: Angrois (Santiago de Compostela), 24 July 2013: 80 dead

Not part of 2026, but the reference case for driver workload. An Alvia entered an 80 km/h curve at about 179 km/h. The driver was on a work phone call with the train manager and lost track of where he was; that section had only ASFA, not continuous ERTMS supervision. A driver-side "working memory" ("braking point for the A Grandeira curve in 2 km") speaks directly to it. *(From background knowledge; check against the CIAF report before quoting.)*

## What this means for an AI assistant

| Time scale | Who can act | Role for AI |
|---|---|---|
| Seconds (Adamuz 8 s, Gelida 5 s) | Automatic protection only: interlocking, ATP/ERTMS, emergency brake | None. Say so honestly. |
| Minutes (the 50-minute response) | Control-room operator, drivers, 112 | Fuse calls and alarms into one picture, keep open loops visible, flag contradictions ("no train is coming" vs. a silent Alvia in the section), propose actions with evidence. **Human decides.** |
| Hours to months (the 22 hours) | Maintenance, traffic planning | Correlate weak signals by location across systems and shifts; escalate when independent sources agree; propose restriction or inspection. **Human decides.** |

## Sources

- [Accidente ferroviario de Adamuz (es.wikipedia)](https://es.wikipedia.org/wiki/Accidente_ferroviario_de_Adamuz): second-by-second timeline
- [2026 Adamuz rail disaster (en.wikipedia)](https://en.wikipedia.org/wiki/2026_Adamuz_rail_disaster)
- [Railway Gazette, 21 Jul 2026: CIAF investigation to continue for months](https://www.railwaygazette.com/spain/2026/07/21/ciaf-says-adamuz-crash-investigation-will-continue-for-several-months-more/)
- [Railway News: investigators identify broken rail](https://railway-news.com/spanish-investigators-identify-broken-rail-in-fatal-adamuz-derailment/)
- [Infobae: the Iryo driver's calls](https://www.infobae.com/espana/2026/01/20/los-primeros-minutos-del-iryo-accidentado-en-adamuz-segun-lo-que-revela-la-llamada-del-maquinista/)
- [El Debate: "si el centro de control no vio al Alvia, vamos a ciegas"](https://www.eldebate.com/economia/20260121/incognitas-extrano-accidente-adamuz-centro-control-no-vio-alvia-significa-vamos-ciegas_376706.html)
- [Telegraph via Yahoo: driver did not know of crash for four minutes](https://www.yahoo.com/news/articles/spanish-train-driver-did-not-200200530.html)
- [Cordópolis: earlier driver felt a "ligera vibración"](https://cordopolis.eldiario.es/cordoba-hoy/maquinista-alvia-paso-accidente-adamuz-noto-ligera-vibracion-no-dio-importancia_1_13045946.html)
- [El Debate: Gelida, 5 seconds to brake](https://www.eldebate.com/espana/cataluna/20260123/rodalies-gelida-solo-tuvo-cinco-segundos-frenar-antes-chocar-contra-muro-caido_377612.html)
- [El Debate: CIAF opens Gelida investigation](https://www.eldebate.com/espana/cataluna/20260122/ciaf-abre-expediente-investigar-causa-descarrilamiento-tren-gelida-barcelona_377180_amp.html)
