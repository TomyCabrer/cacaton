"""Synthetic generator for LZB protocol-adherence dataset. Adaption format: prompt + completion (jsonl)."""
import json, random
random.seed(7)

REASON = {
 "R1": {"en": "Driver did not stop on Meta 000 (occupied block).", "es": "El maquinista no se detuvo ante Meta 000 (tramo ocupado)."},
 "R2": {"en": "Driver did not report location to the RC after stopping.", "es": "El maquinista no informo de su posicion al RC tras detenerse."},
 "R3": {"en": "RC authorized 'marcha normal' instead of 5ET3.2 'Marcha a la Vista'.", "es": "El RC autorizo 'marcha normal' en lugar de 5ET3.2 'Marcha a la Vista'."},
 "R4": {"en": "Driver passed a signal under 5ET3.2 without separate overrun authorization.", "es": "El maquinista rebaso una senal bajo 5ET3.2 sin autorizacion expresa de rebase."},
 "R5": {"en": "Driver resumed before RC authorization.", "es": "El maquinista reanudo la marcha antes de la autorizacion del RC."},
 "R6": {"en": "Driver disconnected LZB without RC authorization (5ET3.3).", "es": "El maquinista desconecto el LZB sin autorizacion del RC (5ET3.3)."},
}
STEP = {"R1": "Stop on Meta 000", "R2": "Report location", "R3": "RC authorization (5ET3.2)", "R4": "Signal overrun", "R5": "Resume after authorization", "R6": "LZB disconnect"}

# phrasing pools: A for train, B held out for test
P = {
 "A": {"en": {"loss": "LZB transmission lost, T light flashing, Meta {m}", "lib": "pressed LIBERAR, braking", "stop": "train stopped at {loc}", "rep": "Reporting stopped at {loc}, Meta 000",
              "chk": "Received. Checks made.", "auth": "Telefonema 5ET3.2: I authorize train {t} to continue under BSL with Marcha a la Vista to signal {sig}", "ack": "Understood, proceeding with Marcha a la Vista to {sig}"},
       "es": {"loss": "Perdida de transmision LZB, luz T intermitente, Meta {m}", "lib": "pulso LIBERAR, frenando", "stop": "tren detenido en {loc}", "rep": "Informo: detenido en {loc}, Meta 000",
              "chk": "Recibido. Comprobaciones realizadas.", "auth": "Telefonema 5ET3.2: Autorizo a maquinista de tren {t} a continuar la marcha al amparo del BSL con Marcha a la Vista hasta la senal {sig}", "ack": "Enterado, continuo con Marcha a la Vista hasta {sig}"}},
 "B": {"en": {"loss": "Lost LZB signal. T flashing. Target speed {m}", "lib": "LIBERAR pressed, applying brakes", "stop": "now standing at {loc}", "rep": "Standing at {loc}. Meta is 000",
              "chk": "Copy. Verification complete.", "auth": "5ET3.2 to train {t}: proceed under BSL, Marcha a la Vista, up to signal {sig}", "ack": "Copy, Marcha a la Vista up to {sig}"},
       "es": {"loss": "Sin transmision LZB. T parpadea. Vmeta {m}", "lib": "LIBERAR pulsado, aplico freno", "stop": "parado en {loc}", "rep": "Estoy parado en {loc}, Vmeta 000",
              "chk": "Recibido, verificaciones hechas.", "auth": "5ET3.2 a tren {t}: continue al amparo del BSL, Marcha a la Vista, hasta senal {sig}", "ack": "Recibido, Marcha a la Vista hasta {sig}"}},
}
BAD_AUTH = {"en": "Resume, normal running speed. Reconnect LZB and proceed.", "es": "Reanude marcha. Con marcha normal."}

def ts(base, off): 
    s = base + off; return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

def make(style, lang, mode):
    p = P[style][lang]
    t = random.choice(["2080", "6076", "6011", "9120", "9230", "2214"])
    loc = random.choice(["PK 118", "PK 209.2", "PK 87.5", "PK 141", "Urda", "Calatrava", "PK 63"])
    sig = random.choice(["E97", "S12", "E41", "S08", "E73"])
    base = random.randint(6*3600, 21*3600); m = "000" if mode != "meta40" else "40"
    ev = []; t0 = 0
    def add(who, txt, dt=None):
        nonlocal t0; t0 += dt if dt is not None else random.randint(4, 40); ev.append(f"[{ts(base,t0)}] {who}: {txt}")
    rules = []
    add("SYS", p["loss"].format(m=m), 0)
    if mode == "meta40":  # compliant distractor: free block, no stop needed
        add(f"Driver {t}", p["lib"], 3); add(f"Driver {t}", {"en": "continuing, watching lineside signals", "es": "continuo, atento a senales laterales"}[lang])
        return ev, rules
    if mode == "R1":
        add(f"Driver {t}", {"en": "no action, continuing at 160 km/h", "es": "sin accion, continuo a 160 km/h"}[lang], 12); rules.append("R1"); return ev, rules
    add(f"Driver {t}", p["lib"], 3); add(f"Driver {t}", p["stop"].format(loc=loc))
    if mode == "R6": add(f"Driver {t}", {"en": "disconnecting LZB and restarting on my own", "es": "desconecto el LZB y reanudo por mi cuenta"}[lang]); rules.append("R6"); return ev, rules
    if mode != "R2": add(f"Driver {t}", p["rep"].format(loc=loc))
    else: rules.append("R2")
    if mode == "R5": add(f"Driver {t}", {"en": "no reply yet from RC, resuming anyway", "es": "sin respuesta del RC, reanudo igualmente"}[lang]); rules.append("R5"); return ev, rules
    add("RC", p["chk"])
    if mode == "R3": add("RC", BAD_AUTH[lang]); rules.append("R3"); add(f"Driver {t}", {"en": "proceeding at normal speed", "es": "continuo a velocidad normal"}[lang])
    else:
        add("RC", p["auth"].format(t=t, sig=sig)); add(f"Driver {t}", p["ack"].format(sig=sig))
        if mode == "R4": add(f"Driver {t}", {"en": f"passed signal {sig} at stop, continuing", "es": f"rebaso senal {sig} en parada, continuo"}[lang]); rules.append("R4")
        else: add(f"Driver {t}", {"en": f"proceeding with Marcha a la Vista, arrived {sig}", "es": f"marcha a la vista, llego a {sig}"}[lang])
    return ev, rules

def row(style, lang, mode):
    ev, rules = make(style, lang, mode)
    prompt = ("Judge whether the LZB-failure protocol was followed in this event log. Answer with VERDICT, RULES, STEP, REASON.\n\n" if lang == "en" else
              "Juzga si se siguio el protocolo de fallo LZB en este registro de eventos. Responde con VERDICT, RULES, STEP, REASON.\n\n") + "\n".join(ev)
    if rules: comp = f"VERDICT: VIOLATION\nRULES: {','.join(rules)}\nSTEP: {STEP[rules[0]]}\nREASON: {REASON[rules[0]][lang]}"
    else: comp = "VERDICT: COMPLIANT\nRULES: none\nSTEP: none\nREASON: " + ("All applicable steps followed." if lang == "en" else "Se siguieron todos los pasos aplicables.")
    return {"prompt": prompt, "completion": comp, "label": "VIOLATION" if rules else "COMPLIANT", "rules": rules, "style": style, "lang": lang}

modes = ["ok"]*5 + ["meta40"]*2 + ["R1", "R2", "R3", "R3", "R4", "R5", "R6"]
def build(n, style):
    return [row(style, random.choice(["en", "es"]), random.choice(modes)) for _ in range(n)]

if __name__ == "__main__":
    for name, rows in [("train", build(1200, "A")), ("test", build(200, "B"))]:
        with open(f"data/{name}.jsonl", "w") as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # Urda demo (held out): reconstruction from press (Cadena SER via Moncloa/Wikipedia), NOT official findings
    urda = ["[08:30:00] SYS: LZB failure Urda sector, trains stopped", "[08:31:00] Driver 2080: loss of LZB transmission, Meta 000, stopped",
            "[08:36:00] RC: Disconnect and reconnect LZB. Reanude marcha. Con marcha normal.", "[08:41:00] RC: Iryo 6076, resume and reconnect LZB",
            "[08:48:00] Driver 6076: cannot reset LZB, stopped at entry signal Urda", "[08:48:30] RC: acknowledged"]
    with open("data/urda_demo.json", "w") as f:
        json.dump({"prompt": "Judge whether the LZB-failure protocol was followed in this event log. Answer with VERDICT, RULES, STEP, REASON.\n\n" + "\n".join(urda),
                   "expected": "VIOLATION R3 (press reconstruction, not official finding)"}, f, indent=1)
