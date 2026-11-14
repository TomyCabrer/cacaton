"""Drill library: five cases, one protocol each.

Case 1 (Urda) is the drill the tower page opens with. It is built on the 28 October 2026 Urda collision as
preliminary press reports describe it (see docs/urda.md): cab signalling (LZB) fails, the control panel loses the
trains, every train is stopped by voice and then moves on sight at 40 km/h. Its cause is not established and the
drill is a simplification, not a replay. The other four are fictional training material: the line borrows PK numbers from the Madrid–Sevilla
high-speed line, and case 5 is inspired by Adamuz, but none of them is a replay of a real event.
Trains go by simple codes (Train A is always the pilot's) with the service name kept beside them. The protocols are simplified teaching versions of
common operating rules (emergency call, cautioning after a rough-ride report, authority
to pass a signal at danger, protecting a train that fouls the adjacent line). They are
not the Adif rule book.

The protocol steps come from this file and appear the instant a report or an alarm lands. Claude never sits
between an alarm and the first protective action. Claude is Copi, the assistant: one model, Sonnet, for
everything it reads and writes.
"""

from __future__ import annotations

import re

LINE = {
    "name": "LAV training line (fictional), PK 290–340",
    "pk_range": [290.0, 340.0],
    "places": [
        {"name": "← Madrid", "pk": 300.5},
        {"name": "Adamuz", "pk": 318.8},
        {"name": "Córdoba →", "pk": 338.5},
    ],
    # Track 1 runs towards Madrid (PK falls). Track 2 runs towards Córdoba (PK rises).
    "signal_pks": [300.0, 304.0, 308.0, 312.0, 316.0, 320.0, 324.0, 328.0, 332.0, 336.0],
    "line_kmh": 300,
}

TRAIN_MODELS = {
    "S-103": {"name": "AVE S-103 · Siemens Velaro", "vmax_kmh": 300, "length_m": 200, "acc": 0.45, "brake": 1.0, "ebrake": 1.3},
    "ETR-1000": {"name": "Iryo ETR 1000 · Frecciarossa", "vmax_kmh": 300, "length_m": 202, "acc": 0.50, "brake": 1.0, "ebrake": 1.3},
    "S-120": {"name": "Alvia S-120 · CAF", "vmax_kmh": 250, "length_m": 107, "acc": 0.40, "brake": 1.0, "ebrake": 1.3},
    "S-106": {"name": "Avlo S-106 · Talgo Avril", "vmax_kmh": 300, "length_m": 202, "acc": 0.45, "brake": 1.0, "ebrake": 1.3},
}

SONNET = "claude-sonnet-5-5"
COPI_MODEL = SONNET  # Copi is one model everywhere
TRIAGE_MODEL = COPI_MODEL

PROTOCOLS: dict[str, dict] = {
    "P-01": {
        "id": "P-01",
        "title": "Something on the line",
        "trigger": "The pilot reports something on or next to a track.",
        "tier": "seconds",
        "model": COPI_MODEL,
        "categories": ["obstruction"],
        "keywords": r"obstruct|obstacle|debris|rock|tree|landslide|fallen|something on the (track|line)|"
        r"obst[aá]culo|desprendimiento|piedra|[aá]rbol|algo en la v[ií]a|ca[ií]d",
        "steps": [
            {
                "id": "stop", "who": "control", "level": "urgent",
                "title": "Emergency call: stop track {haz_track}",
                "detail": "Before any question. A needless stop costs minutes. {threat_line}",
                "pilot": "Pilot, press your emergency call button now.",
                "action": {"kind": "emergency_call", "track": "{haz_track}", "label": "Emergency call · track {haz_track}"},
                "check": "threats_called",
            },
            {
                "id": "block", "who": "control", "level": "important",
                "title": "Hold {protect_signal} at STOP",
                "detail": "The call stops the train running now. The signal stops the next one.",
                "action": {"kind": "hold_signal", "signal": "{protect_signal}", "label": "Hold {protect_signal}"},
                "check": "signal_held", "signal": "{protect_signal}",
            },
            {
                "id": "details", "who": "driver", "level": "important",
                "title": "Get the facts from {me}",
                "detail": "Exact place, which track, what it is, is the pilot's own track clear.",
                "pilot": "Pilot, tell the tower: where, which track, what, and is your track clear.",
                "say": "{me}, control. Where is it, which track, what is it, and is your track clear?",
                "expect": "reply", "check": "driver_replied",
            },
            {
                "id": "stopped", "who": "control", "level": "info",
                "title": "{threat} stopped short",
                "detail": "Ticks itself when the panel shows the train at a stand before the site.",
                "check": "threats_stopped",
            },
        ],
    },
    "P-02": {
        "id": "P-02",
        "title": "Rough ride",
        "trigger": "The pilot reports a jolt, vibration or bang from the track.",
        "tier": "minutes",
        "model": COPI_MODEL,
        "categories": ["rough_ride"],
        "keywords": r"vibrat|rough|jolt|bump|bang|shak|hit something|golpe|vibraci|bache|sacudida|salto",
        "steps": [
            {
                "id": "details", "who": "driver", "level": "important",
                "title": "Get the facts from {me}",
                "detail": "Where, which track, how hard, what speed.",
                "pilot": "Pilot, tell the tower: where, which track, how hard, your speed.",
                "say": "{me}, control. Where, which track, how hard, and your speed?",
                "expect": "reply", "check": "driver_replied",
            },
            {
                "id": "tsr", "who": "control", "level": "important",
                "title": "30 km/h at PK {site}",
                "detail": "No train crosses the spot at line speed until someone has looked. {threat_line}",
                "pilot": "Pilot, tell the tower: no speed restriction yet, and {threat} is coming.",
                "action": {"kind": "tsr", "track": "{haz_track}", "from": "{tsr_from}", "to": "{tsr_to}", "kmh": 30,
                           "label": "Set 30 km/h"},
                "check": "tsr_set",
            },
            {
                "id": "warn", "who": "control", "level": "important",
                "title": "{threat}: look at PK {site}",
                "detail": "The next train over the spot goes slowly, looks and reports.",
                "action": {"kind": "radio_train", "train": "{threat_id}", "ask": "examine", "label": "Radio {threat}"},
                "check": "train_warned", "train": "{threat_id}",
            },
            {
                "id": "examined", "who": "control", "level": "info",
                "title": "Wait for {threat}'s report",
                "detail": "Ticks itself when the train has crossed the spot slowly and reported.",
                "check": "site_examined",
            },
        ],
    },
    "P-03": {
        "id": "P-03",
        "title": "Signal dark",
        "trigger": "The pilot reports a signal that is unlit or does not make sense.",
        "tier": "conflict",
        "model": COPI_MODEL,
        "categories": ["signal"],
        "keywords": r"signal|dark|unlit|no light|aspect|se[ñn]al|apagad",
        "steps": [
            {
                "id": "stand", "who": "driver", "level": "urgent",
                "title": "Hold {me} at {sig}",
                "detail": "A dark signal counts as a red signal.",
                "pilot": "Pilot, {sig} counts as red. Stay stopped and tell the tower its number.",
                "say": "{me}, control. Treat {sig} as red. Stay at a stand and confirm the signal number.",
                "expect": "reply", "check": "driver_stopped",
            },
            {
                "id": "section", "who": "control", "level": "info",
                "title": "Wait: section beyond {sig} clear",
                "detail": "No authority while a train is in the section. Ticks itself when it is clear.",
                "check": "section_clear",
            },
            {
                "id": "authority", "who": "driver", "level": "important",
                "title": "Authorise {me} past {sig}",
                "detail": "Only with the section clear. Exact words, and the pilot reads them back.",
                "pilot": "Pilot, do not move. Only the tower can clear you past {sig}.",
                "copi_relay": False,
                "say": "{me}, pass {sig} at danger. On sight, 30 kilometres per hour at most, to {next_sig}. Read back.",
                "action": {"kind": "authority", "signal": "{sig}", "label": "Give authority + send"},
                "expect": "readback", "check": "authority_readback", "after": ["section"],
            },
            {
                "id": "on_sight", "who": "driver", "level": "info",
                "title": "{me} on sight to {next_sig}",
                "detail": "Ticks itself when the train passes {next_sig}.",
                "check": "on_sight_done", "after": ["authority"],
            },
        ],
    },
    "P-04": {
        "id": "P-04",
        "title": "Emergency brake: other track fouled?",
        "trigger": "The pilot reports an emergency brake application, lost systems, or a train fault at speed.",
        "tier": "major",
        "model": COPI_MODEL,
        "categories": ["train_fault"],
        "keywords": r"emergency brake|derail|descarril|freno de emergencia|enganch|catenar|pantograph|pant[oó]grafo|"
        r"lost (power|systems)|train fault|aver[ií]a",
        "steps": [
            {
                "id": "stop", "who": "control", "level": "urgent",
                "title": "Emergency call: stop all trains",
                "detail": "Until someone has looked, the other track counts as blocked. {threat_line}",
                "pilot": "Pilot, press your emergency call button now.",
                "action": {"kind": "emergency_call", "track": "all", "label": "Emergency call · all trains"},
                "check": "threats_called",
            },
            {
                "id": "question", "who": "driver", "level": "important",
                "title": "Ask {me}: all coaches on the rails?",
                "detail": "Do not accept a guess about the cause. The pilot has to look.",
                "pilot": "Pilot, look back. All coaches on the rails? Other track clear? Tell the tower.",
                "say": "{me}, control. Look back along your train. Are all coaches on the rails? Is the other track clear?",
                "expect": "reply", "check": "derail_confirmed",
            },
            {
                "id": "block", "who": "control", "level": "important",
                "title": "Block both tracks",
                "detail": "Hold {protect_signal} and {protect_signal_own} at STOP. Nothing enters the site.",
                "action": {"kind": "block_zone", "signals": ["{protect_signal}", "{protect_signal_own}"], "label": "Block both tracks"},
                "check": "zone_blocked",
            },
            {
                "id": "emergency", "who": "control", "level": "important",
                "title": "Send emergency services",
                "detail": "To PK {site}, both tracks, and tell 112. Standing an ambulance down is cheap.",
                "action": {"kind": "dispatch", "what": "emergency services", "label": "Send emergency services"},
                "check": "dispatched", "what": "emergency services",
            },
        ],
    },
    "P-05": {
        "id": "P-05",
        "title": "LZB failure",
        "trigger": "Cab signalling (LZB) fails. The panel loses the trains and nothing in a cab stops one.",
        "tier": "major",
        "model": COPI_MODEL,
        "categories": ["cab_signal"],
        "keywords": r"\blzb\b|cab signal|no cab|se[ñn]alizaci[oó]n en cabina|lost (the )?signal|cannot restart|can't restart|no puedo arrancar",
        "steps": [
            {
                "id": "stop", "who": "driver", "level": "urgent",
                "title": "Stop all trains",
                "detail": "By voice, now.",
                "check": "stop_ordered",
            },
            {
                "id": "stood", "who": "driver", "level": "info",
                "title": "Every train at a stand",
                "detail": "Ticks itself when every train has stopped.",
                "check": "all_stood", "after": ["stop"],
            },
            {
                "id": "on_sight", "who": "driver", "level": "important",
                "title": "Continue on sight, 40 km/h",
                "detail": "Never normal running: nobody can see the line ahead.",
                "check": "on_sight_run", "after": ["stood"],
            },
        ],
    },
}

CASES: dict[str, dict] = {
    "urda": {
        "id": "urda", "n": 1, "protocol": "P-05", "simple": True,
        "title": "Urda: LZB failure",
        "summary": "Cab signalling fails and the panel loses every train. Stop the trains by voice, "
        "then move them on sight at 40 km/h.",
        "teaches": "With LZB down: stop every train, then on sight at 40 km/h. Never normal running into a line nobody can see.",
        "reconstruction": "Built on the Urda collision (28 Oct 2026) as preliminary press reports describe it. "
        "Positions, speeds and timings are the drill's, not the investigation's. Cause not yet established.",
        "reality": [
            "08:31 LZB lost over about 63 km. Trains braked to a stand.",
            "08:36 the control centre cleared the AVE for normal running. The rule was on sight, 40 km/h.",
            "08:48 the Iryo ahead said it could not restart. No action followed.",
            "08:53 the AVE hit the stopped Iryo at 160 to 200 km/h. 69 people died.",
        ],
        "driver_brief": "You drive Train A (AVE 2080), Madrid → Sevilla, at 200 km/h. Hold your speed and do what the tower tells you.",
        "clock_start": "2026-10-28T08:30:56",
        "line": {
            "name": "Madrid–Sevilla HSL, Mora–Urda (PK approximate)",
            "pk_range": [100.0, 130.0],
            "places": [{"name": "← Madrid", "pk": 108.3}, {"name": "Urda", "pk": 118.0}, {"name": "Sevilla →", "pk": 119.7}],
            "signal_pks": [],
        },
        # fail_s: seconds after Start. Until then the panel shows both trains; from then on, only where they were last seen.
        "lzb": {"from_pk": 96.0, "to_pk": 159.0, "since": "08:31", "fail_s": 4.0},
        "train_sight_m": 350,
        "pilot_acc": 1.4,  # m/s²: far more than a real train, so the pilot is not left waiting in a demo
        "view": [108.0, 120.0], "max_s": 420,
        "zones": [{"track": 2, "from": 100.0, "to": 130.0, "kmh": 200}],
        "trains": [
            {"id": "A", "name": "AVE 2080", "model": "S-103", "track": 2, "pk": 109.0, "kmh": 200, "controller": "human",
             "on_board": 397, "route": "Madrid → Sevilla"},
            {"id": "B", "name": "Iryo 6076", "model": "ETR-1000", "track": 2, "pk": 110.9, "kmh": 200, "controller": "ai",
             "on_board": 147, "route": "Madrid → Sevilla"},
        ],
        "hazards": [],
        "memory": [],
    },
    "obstruction": {
        "id": "obstruction", "n": 2, "protocol": "P-01",
        "title": "Rockfall on the other track",
        "summary": "The pilot sees rocks on the opposite track. Train B is coming the other way at 300 km/h.",
        "teaches": "The stop call goes out before the questions.",
        "driver_brief": "You drive Train A (Alvia 2264), Madrid → Sevilla, on track 2 at 200 km/h. Hold your speed. "
        "If anything on or near the line is not normal, report it to the tower and do what the tower says.",
        "view": [304.0, 326.0], "max_s": 330,
        "trains": [
            {"id": "A", "name": "Alvia 2264", "model": "S-120", "track": 2, "pk": 307.5, "kmh": 200, "controller": "human",
             "on_board": 212, "route": "Madrid → Sevilla"},
            {"id": "B", "name": "AVE 3142", "model": "S-103", "track": 1, "pk": 323.8, "kmh": 300, "controller": "ai",
             "on_board": 371, "route": "Sevilla → Madrid"},
        ],
        "hazards": [{"id": "H1", "kind": "debris", "track": 1, "pk": 311.4, "sight_m": 900}],
        "memory": [
            {"id": "M1", "when": "March 2024", "track": 1, "pk": 311.5, "source": "Slope inspection",
             "text": "Cutting at PK 311.3–311.6 rated 'watch': loose blocks above track 1."},
            {"id": "M2", "when": "Today 16:00", "track": None, "pk": 311.0, "source": "Weather service",
             "text": "Heavy rain warning for the Adamuz area until 22:00."},
        ],
    },
    "rough_ride": {
        "id": "rough_ride", "n": 3, "protocol": "P-02",
        "title": "A jolt at PK 318.7",
        "summary": "The pilot feels a jolt from the track. Train B follows on the same track, 14 km behind.",
        "teaches": "A weak signal means something once it is put next to the others from the same place.",
        "driver_brief": "You drive Train A (Iryo 6021), Sevilla → Madrid, on track 1 at 300 km/h. Hold your speed. "
        "If anything about the ride or the line is not normal, report it to the tower and do what the tower says.",
        "view": [306.0, 338.0], "max_s": 420,
        "trains": [
            {"id": "A", "name": "Iryo 6021", "model": "ETR-1000", "track": 1, "pk": 322.0, "kmh": 300, "controller": "human",
             "on_board": 289, "route": "Sevilla → Madrid"},
            {"id": "B", "name": "Avlo 2187", "model": "S-106", "track": 1, "pk": 336.0, "kmh": 300, "controller": "ai",
             "on_board": 503, "route": "Sevilla → Madrid"},
        ],
        "hazards": [{"id": "H1", "kind": "rail_break", "track": 1, "pk": 318.68, "human_effect": "jolt",
                     "ai_derail_above_kmh": 80, "ai_safe_kmh": 40,
                     "finding": "Broken rail at PK 318.68, track 1. A gap at a weld. I crossed it at walking pace."}],
        "memory": [
            {"id": "M1", "when": "Two months ago", "track": 1, "pk": 318.7, "source": "Track inspection record",
             "text": "Small vertical acceleration near PK 318.7, track 1. Below intervention limits. No action taken."},
            {"id": "M2", "when": "Last night 21:46", "track": 1, "pk": 318.7, "source": "Track-circuit monitoring",
             "text": "Track circuit TC-318-V1 fell from 2.0 V to 1.5 V. Alarm threshold is 0.78 V, so no alarm."},
        ],
    },
    "dark_signal": {
        "id": "dark_signal", "n": 4, "protocol": "P-03",
        "title": "A signal with no light",
        "summary": "The pilot finds a signal unlit. On the panel it shows STOP, and Train B is standing in the section beyond it.",
        "teaches": "No authority to pass while the section is occupied, and the words are read back.",
        "driver_brief": "You drive Train A (AVE 3142), Madrid → Sevilla, on track 2. The limit here is 160 km/h. Obey the signals: "
        "green is clear, yellow means the next signal is at STOP, red is STOP. "
        "If a signal is not normal, report it to the tower and do what the tower says.",
        "view": [306.0, 320.0], "max_s": 600,
        "zones": [{"track": 2, "from": 308.0, "to": 318.0, "kmh": 160}],
        "extra_signals": [{"track": 2, "pk": 314.0, "failed": True}, {"track": 2, "pk": 314.6}],
        "trains": [
            {"id": "A", "name": "AVE 3142", "model": "S-103", "track": 2, "pk": 309.0, "kmh": 160, "controller": "human",
             "on_board": 371, "route": "Madrid → Sevilla"},
            {"id": "B", "name": "Avlo 2187", "model": "S-106", "track": 2, "pk": 314.55, "kmh": 0, "controller": "ai",
             "on_board": 503, "route": "Madrid → Sevilla",
             "depart": {"after_report": "signal", "delay_s": 30, "latest_s": 300}},
        ],
        "hazards": [],
        "memory": [
            {"id": "M1", "when": "Three days ago", "track": 2, "pk": 314.0, "source": "Signalling maintenance log",
             "text": "Lamp unit of signal S2-314 replaced."},
            {"id": "M2", "when": "Yesterday", "track": 2, "pk": 314.0, "source": "Interlocking event log",
             "text": "Lamp-proving alarm on S2-314, twice, each cleared by itself within a minute."},
        ],
    },
    "derailment": {
        "id": "derailment", "n": 5, "protocol": "P-04",
        "title": "Emergency brake at Adamuz",
        "summary": "The pilot's train brakes by itself and loses its rear coaches' systems. "
        "Train B is coming on the other track.",
        "teaches": "Treat the other track as blocked until someone has looked. Ask a closed question.",
        "driver_brief": "You drive Train A (Iryo 6021), Sevilla → Madrid, on track 1. The limit here is 200 km/h. Hold your speed. "
        "If anything is not normal, report it to the tower and do what the tower says.",
        "view": [302.0, 326.0], "max_s": 480,
        "zones": [{"track": 1, "from": 312.0, "to": 326.0, "kmh": 200}],
        "trains": [
            {"id": "A", "name": "Iryo 6021", "model": "ETR-1000", "track": 1, "pk": 322.5, "kmh": 200, "controller": "human",
             "on_board": 289, "route": "Sevilla → Madrid"},
            {"id": "B", "name": "Alvia 2264", "model": "S-120", "track": 2, "pk": 304.0, "kmh": 250, "controller": "ai",
             "on_board": 212, "route": "Madrid → Huelva"},
        ],
        "hazards": [{"id": "H1", "kind": "rail_break", "track": 1, "pk": 318.68, "human_effect": "derail",
                     "ai_derail_above_kmh": 80, "ai_safe_kmh": 40}],
        "inspect_finding": "Coaches 6, 7 and 8 are off the rails. Coach 8 leans onto the other track.",
        "memory": [
            {"id": "M1", "when": "Two months ago", "track": 1, "pk": 318.7, "source": "Track inspection record",
             "text": "Small vertical acceleration near PK 318.7, track 1. Below intervention limits. No action taken."},
            {"id": "M2", "when": "Last night 21:46", "track": 1, "pk": 318.7, "source": "Track-circuit monitoring",
             "text": "Track circuit TC-318-V1 fell from 2.0 V to 1.5 V. Alarm threshold is 0.78 V, so no alarm."},
        ],
    },
}

REPORT_CATEGORIES = [
    {"id": "obstruction", "label": "Something on the line", "options": [
        {"id": "other", "label": "On the other track"}, {"id": "mine", "label": "On my track"}]},
    {"id": "rough_ride", "label": "Jolt / rough ride"},
    {"id": "signal", "label": "Signal not normal"},
    {"id": "train_fault", "label": "Train fault / emergency brake"},
    {"id": "cab_signal", "label": "Cab signal (LZB) lost"},
]
CATEGORY_TEXT = {
    "obstruction": "Obstruction on the line",
    "rough_ride": "Rough ride: I felt a jolt from the track",
    "signal": "Signal not normal",
    "train_fault": "Train fault: emergency brake applied",
    "cab_signal": "Cab signalling lost: no LZB",
}


def protocol_for_category(category: str) -> str | None:
    for p in PROTOCOLS.values():
        if category in p["categories"]:
            return p["id"]
    return None


def match_keywords(text: str) -> str | None:
    """Deterministic fallback for free-text reports. First protocol whose keywords hit, most specific first."""
    for pid in ("P-05", "P-04", "P-03", "P-02", "P-01"):
        if re.search(PROTOCOLS[pid]["keywords"], text, re.IGNORECASE):
            return pid
    return None


def routing() -> list[dict]:
    return [
        {"protocol": p["id"], "title": p["title"], "tier": p["tier"], "model": p["model"], "why": "One model for everything."}
        for p in PROTOCOLS.values()
    ]
