"""Deterministic rules: the fast, testable layer of Copi.

These run on every event in milliseconds, with no network and no model. They do
the things a stressed human forgets and that must never wait for an LLM:
correlate weak signals by location, track unanswered calls, notice that a train
went quiet in an incident zone, and flag statements that contradict the record.

The Claude layer (copilot.py) sits on top and writes the briefing; it never
replaces these rules.
"""

from __future__ import annotations

from .memory import CONFIDENCE_RANK, WorkingMemory
from .scenario import parse_t, seconds_between, trains_near

INCIDENT_RADIUS_KM = 1.5


class RuleEngine:
    def __init__(self, scenario: dict, mem: WorkingMemory):
        self.sc = scenario
        self.mem = mem
        self.trains = {t["id"]: t for t in scenario["trains"]}
        self.anomalies: list[dict] = []
        self.incident: dict | None = None
        self.no_answer: dict[str, list[str]] = {}
        self.dispatched: set[str] = set()
        self.status_confirmed: set[str] = set()
        self.banner: dict | None = None
        self.driver: dict | None = None
        self.firsts: dict[str, str] = {}

    # ------------------------------------------------------------------
    def on_event(self, ev: dict, t: str) -> bool:
        """Apply one fed event. Returns True if memory changed in a way worth re-briefing."""
        before = len(self.mem.log)
        if "anomaly" in ev:
            self._anomaly(ev, t)
        if "occupancy" in ev:
            self._occupancy(ev, t)
        if "derailment" in ev:
            self._derailment(ev, t)
        if ev.get("driver_view"):
            self._driver_advisory(ev, t)
        if "signal" in ev:
            self._signal(ev, t)
        if "heartbeat_lost" in ev:
            self._heartbeat_lost(ev, t)
        if "power" in ev:
            self._power(ev, t)
        if ev["kind"] == "external_112":
            self._call_112(ev, t)
        if "call" in ev:
            self._call(ev, t)
        for claim in ev.get("claims", []):
            self._claim(claim, ev, t)
        if "emergency" in ev:
            self._emergency(ev, t)
        return len(self.mem.log) > before

    # ------------------------------------------------------------------
    # Act 1: weak signals that only mean something together
    def _anomaly(self, ev: dict, t: str) -> None:
        self.anomalies.append(ev)
        specific = [a for a in self.anomalies if a["location"].get("radius_km", 1.0) <= 1.0]
        if not specific:
            loc = ev["location"]
            self.mem.upsert(
                "watch",
                f"area:{loc['pk']:.0f}",
                f"Area-level warning around PK {loc['pk']:.1f} (±{loc.get('radius_km', 0):.0f} km). "
                "On its own: low specificity.",
                [ev["id"]],
                t,
                detail=ev["text"],
            )
            return

        anchor = min(specific, key=lambda a: a["location"]["radius_km"])
        pk, track = anchor["location"]["pk"], anchor["location"]["track"]
        cluster = [a for a in self.anomalies if self._near(a, pk, track)]
        ids = [a["id"] for a in cluster]
        score = sum(a["anomaly"]["weight"] for a in cluster)
        families = sorted({a["anomaly"]["family"] for a in cluster})
        impacts = [a for a in cluster if a["anomaly"]["family"] == "dynamic"]
        zone = self._zone(pk, track)
        key = f"defect:T{track}:{int(pk * 2) / 2:.1f}"

        if len(families) < 2:
            self.mem.upsert("watch", key, f"Single weak signal at {zone}.", ids, t, detail=ev["text"])
            return
        self.mem.resolve(key.replace("defect:", "area:"), t, "merged into location hypothesis")

        summary = "; ".join(f"{a['id']} {a['channel'].lower()}" for a in cluster)
        detail = (
            f"{len(cluster)} signals from {len(families)} independent families ({', '.join(families)}), "
            f"score {score:.1f}. Each is below its own alarm threshold. Sources: {summary}."
        )

        if score >= 5 and impacts:
            level = "critical"
            text = (
                f"Rail discontinuity likely at {zone}: {len(impacts)} train(s) registered wheel impacts at the same point."
            )
            conf = "high"
        elif score >= 4 and len(families) >= 3:
            level, conf = "high", "medium"
            text = f"Probable track defect at {zone}."
        elif score >= 3:
            level, conf = "medium", "medium"
            text = f"Possible track defect at {zone}."
        else:
            level, conf = "low", "low"
            text = f"Possible track defect at {zone} (two unrelated sources agree on location)."

        self.mem.upsert("hypothesis", key, text, ids, t, confidence=conf, detail=detail)
        if CONFIDENCE_RANK[conf] >= 2:
            self.firsts.setdefault("defect:flagged", t)

        if level == "medium":
            self.mem.recommend(
                "INSPECT_TRACK", zone,
                f"Inspect {zone} (ultrasonic + visual) in the next maintenance window",
                "Three independent weak signals point at the same few hundred metres. None crosses its own "
                "threshold, which is exactly why no single system raised it.",
                ids, "medium", "One inspection crew for about two hours at night. No service impact.", t,
            )
        elif level == "high":
            self.mem.recommend(
                "INSPECT_TRACK", zone, f"Inspect {zone} today, before the evening peak",
                "Four independent weak signals now agree on one location, including a fresh human report.",
                ids, "high", "One crew diverted from planned work.", t,
            )
            self.mem.recommend(
                "SPEED_RESTRICTION", zone, f"Precautionary speed restriction on {zone} until inspected",
                "Evidence keeps accumulating at one spot. A restriction limits the energy of any failure "
                "while the inspection is pending.",
                ids, "high", "A few minutes of delay per train on one track.", t,
            )
        elif level == "critical":
            self.firsts.setdefault("defect:critical", t)
            self.mem.recommend(
                "SPEED_RESTRICTION", zone,
                f"Close {zone}, or restrict to walking pace, until inspected",
                f"{len(impacts)} train(s) hit something at PK {pk:.2f} on track {track}. Wheel impacts at a fixed "
                "point are the signature of a rail discontinuity. The next train on this track will cross it at line speed.",
                ids, "critical", "Corridor delays of 1–2 h with single-track working on the other track.", t,
            )
            self.mem.recommend(
                "INSPECT_TRACK", zone, f"Send track inspection to {zone} now",
                "Physical confirmation is the fastest way to either clear the line or keep it closed.",
                ids, "critical", "One crew, immediately.", t,
            )
            self.mem.upsert(
                "open_loop", f"{key}:exposure",
                f"{len(impacts)} train(s) have crossed the suspect point since the first impact; "
                "track still open at line speed.",
                [a["id"] for a in impacts], t,
            )

    def _near(self, a: dict, pk: float, track: int | None) -> bool:
        loc = a["location"]
        if loc.get("track") not in (None, track):
            return False
        return abs(loc["pk"] - pk) <= max(loc.get("radius_km", 0.3), 0.3)

    def _zone(self, pk: float, track: int | None) -> str:
        for tc in self.sc["infrastructure"].get("track_circuits", []):
            if tc["track"] == track and tc["pk_from"] <= pk <= tc["pk_to"]:
                return f"track {track}, PK {tc['pk_from']:.1f}–{tc['pk_to']:.1f}"
        return f"track {track}, PK {pk - 0.3:.1f}–{pk + 0.3:.1f}"

    # ------------------------------------------------------------------
    # Act 2: seconds. Observe, do not advise.
    def _automatic_window(self, t: str, ev_id: str) -> None:
        if self.banner is None:
            self.banner = {
                "kind": "automatic",
                "since": t,
                "text": "AUTOMATIC PROTECTION WINDOW — seconds to impact. No human, and no AI advisor, can "
                "decide this fast. Signalling and the train's emergency brake are the safety layer here. "
                "Copi records; it does not advise.",
                "evidence": [ev_id],
            }
            self.mem.note(t, "banner", "Automatic protection window: Copi observes only", evidence=[ev_id])

    def _set_incident(self, pk: float, t: str, ev_id: str, why: str) -> None:
        if self.incident is None:
            self.incident = {"pk": pk, "t": t, "evidence": [ev_id], "why": [why]}
        else:
            self.incident["evidence"].append(ev_id)
            self.incident["why"].append(why)

    def _occupancy(self, ev: dict, t: str) -> None:
        occ = ev["occupancy"]
        train = occ["train"]
        if occ["state"] == "entered":
            self.mem.upsert(
                "fact", f"occ:{train}",
                f"{train} on track {occ['track']}, PK {occ['pk_from']:.1f}–{occ['pk_to']:.1f}.",
                [ev["id"]], t,
            )
        elif occ["state"] == "static":
            self.mem.upsert(
                "fact", f"occ:{train}",
                f"{train} stationary on track {occ['track']}, PK {occ['pk_from']:.1f}–{occ['pk_to']:.1f}. "
                "Not a scheduled stop.",
                [ev["id"]], t,
            )
            if self.incident is not None:
                self._involve(train, "high", [ev["id"]], t, "stopped inside the incident zone and has not moved")

    def _derailment(self, ev: dict, t: str) -> None:
        d = ev["derailment"]
        pk, track = ev["location"]["pk"], ev["location"]["track"]
        self._set_incident(pk, t, ev["id"], "onboard derailment alarm")
        self._automatic_window(t, ev["id"])
        self.mem.upsert(
            "fact", f"derailed:{d['train']}",
            f"{d['train']}: derailment detected, coaches {d['coaches']}, track {track} PK {pk:.2f}.",
            [ev["id"]], t,
        )
        self.mem.upsert(
            "hypothesis", "fouled:adjacent",
            f"Track {3 - track} may be fouled by derailed coaches of {d['train']}.",
            [ev["id"]], t, confidence="high",
        )
        for tr in trains_near(self.sc, t, pk, 3.0):
            if tr["track"] != track:
                self._involve(
                    tr["id"], "medium", [ev["id"]], t,
                    f"on track {tr['track']} {abs(tr['pk'] - pk):.2f} km away at ~{tr['speed_kmh'] or '?'} km/h when "
                    f"{d['train']} derailed",
                )

    def _driver_advisory(self, ev: dict, t: str) -> None:
        self.driver = {
            "train": ev["driver_view"],
            "t": t,
            "headline": "Probable DERAILMENT, not a catenary snag",
            "text": "Emergency brake and loss of systems in the rear coaches. Assume the adjacent track is fouled. "
            "Tell the CTC now:",
            "say": "«Descarrilamiento en PK 318,6. Posible invasión de vía contigua. Paren el tráfico.»",
            "evidence": [ev["id"]],
        }
        self.mem.note(t, "driver.advisory", f"Advisory pushed to {ev['driver_view']} cab", evidence=[ev["id"]])

    def _signal(self, ev: dict, t: str) -> None:
        sig = ev["signal"]
        if sig["to"] != "stop":
            return
        pk, track = ev["location"]["pk"], ev["location"]["track"]
        self._set_incident(pk, t, ev["id"], f"{sig['id']} dropped: {sig['cause']}")
        self._automatic_window(t, ev["id"])
        self.mem.upsert(
            "fact", f"signal:{sig['id']}",
            f"{sig['id']} (track {track}, PK {pk:.2f}) dropped to STOP: {sig['cause']}.",
            [ev["id"]], t,
        )
        for tr in trains_near(self.sc, t, pk, 3.0):
            if tr["track"] == track:
                self._involve(
                    tr["id"], "medium", [ev["id"]], t,
                    f"{abs(tr['pk'] - pk):.2f} km from {sig['id']} at ~{tr['speed_kmh'] or '?'} km/h when it dropped; "
                    "stopping distance at that speed is over 2 km",
                )

    def _heartbeat_lost(self, ev: dict, t: str) -> None:
        train = ev["heartbeat_lost"]
        self.mem.upsert(
            "fact", f"telemetry:{train}",
            f"{train}: telemetry lost at track {ev['location']['track']} PK {ev['location']['pk']:.2f} while braking.",
            [ev["id"]], t,
        )
        if self.incident is not None:
            self._involve(train, "high", [ev["id"]], t, "telemetry lost inside the incident zone")

    # ------------------------------------------------------------------
    # Act 3: minutes. Fuse, track loops, catch contradictions.
    def _power(self, ev: dict, t: str) -> None:
        p = ev["power"]
        self.mem.upsert("fact", f"power:{p['section']}", f"Catenary voltage drop, {p['section']} section.", [ev["id"]], t)
        if self.banner and self.banner["kind"] == "automatic":
            self.banner = None
        if self.incident is None:
            return
        if seconds_between(self.incident["t"], t) > 180:
            return
        pk = self.incident["pk"]
        evidence = self.incident["evidence"] + [ev["id"]]
        nearby = trains_near(self.sc, t, pk, INCIDENT_RADIUS_KM)
        people = sum(tr["on_board"] or 0 for tr in nearby)
        names = ", ".join(f"{tr['id']} (track {tr['track']})" for tr in nearby)
        self.firsts.setdefault("incident", t)
        for key in [k for k, i in self.mem.items.items() if k.startswith("defect:") and k.endswith(":exposure") and i.status == "open"]:
            self.mem.resolve(key, t, "overtaken by the incident at this location", [ev["id"]])
        self.mem.supersede(
            lambda r: r.action in ("SPEED_RESTRICTION", "INSPECT_TRACK"),
            t, "Overtaken by the incident at the same location: stopping all traffic covers it.",
        )
        self.banner = {
            "kind": "incident",
            "since": t,
            "text": f"INCIDENT · Adamuz PK ~{pk:.1f}. Trains in zone: {names}. Up to {people} people on board.",
            "evidence": evidence,
        }
        self.mem.upsert(
            "hypothesis", "incident:adamuz",
            f"Major incident at Adamuz, PK ~{pk:.1f}, both tracks: "
            + " + ".join(self.incident["why"])
            + " + power loss, within seconds of each other.",
            evidence, t, confidence="high",
        )
        for tr in nearby:
            self.mem.upsert(
                "open_loop", f"status:{tr['id']}",
                f"Status unconfirmed: {tr['id']} — track {tr['track']}, last PK {tr['pk']:.2f}, "
                f"{tr['on_board'] or '?'} on board.",
                evidence, t,
            )
            if tr["id"] not in self._involved_ids():
                self._involve(tr["id"], "medium", evidence, t, "inside the incident zone at the moment of the alarms")
        self.mem.recommend(
            "STOP_TRAFFIC", "both tracks PK 300–340",
            "Stop all traffic on both tracks, PK 300–340 (Adamuz)",
            "Loss of point detection and loss of power at the same place within seconds. Until the scene is "
            "confirmed, any train entering the zone is at risk.",
            evidence, "critical", "Corridor delays until the scene is confirmed (minutes).", t,
        )
        for tr in nearby:
            self.mem.recommend(
                "CALL_TRAIN", tr["id"],
                f"Call {tr['id']}: driver, then train manager on the backup number",
                f"{tr['id']} was in the zone at the moment of the alarms. Get a first-hand status.",
                evidence, "critical", "One radio call.", t,
            )
        self.mem.recommend(
            "DISPATCH_EMERGENCY", "Adamuz PK 318.2–318.9",
            f"Send emergency services to Adamuz PK 318.2–318.9, both tracks: {len(nearby)} trains, up to {people} people",
            "Dispatching to the zone, not to a single caller, covers every train that may be involved. "
            "Recalling an ambulance costs little; a late one does not.",
            evidence, "critical", "Emergency resources committed before confirmation; can be stood down.", t,
            key="dispatch_emergency:incident",
        )
        for tr in nearby:
            self.firsts.setdefault(f"dispatch:{tr['id']}", t)

    def _call_112(self, ev: dict, t: str) -> None:
        train = ev.get("train")
        self.mem.upsert(
            "fact", f"112:{train}", f"112 emergency call from a passenger on {train}.", [ev["id"]], t,
        )
        if train and self.incident is not None:
            self._involve(train, "high", [ev["id"]], t, "passengers are calling 112")

    def _call(self, ev: dict, t: str) -> None:
        call = ev["call"]
        if call["status"] == "no_answer":
            train = ev["train"]
            attempts = self.no_answer.setdefault(train, [])
            attempts.append(ev["id"])
            self.mem.upsert(
                "open_loop", f"nocontact:{train}",
                f"No answer from {train} driver: {len(attempts)} attempt(s).",
                list(attempts), t,
            )
            if len(attempts) >= 2:
                loc = ev["location"]
                self._involve(train, "high", list(attempts), t, f"{len(attempts)} unanswered calls after the alarms")
                self.mem.recommend(
                    "CALL_TRAIN", f"{train}:backup",
                    f"Stop calling the {train} driver. Call the train manager / any crew phone",
                    "Two unanswered calls from a train inside the incident zone. The driver may be incapacitated.",
                    list(attempts), "critical", "One call.", t,
                )
                self.mem.recommend(
                    "DISPATCH_EMERGENCY", train,
                    f"Send emergency services directly to {train}: track {loc['track']}, PK ~{loc['pk']:.2f}",
                    f"Silence from {train} inside the zone is itself evidence. Give responders its exact position.",
                    list(attempts), "critical", "Resources committed before confirmation; can be stood down.", t,
                )
                self.firsts.setdefault(f"dispatch:{train}", t)
        elif call["status"] == "answered" and ev.get("train"):
            train = ev["train"]
            if self.mem.is_open(f"nocontact:{train}"):
                self.mem.resolve(f"nocontact:{train}", t, f"contact via {call['from']}", [ev["id"]])

    def _claim(self, claim: dict, ev: dict, t: str) -> None:
        subject, assertion, by = claim["subject"], claim["assertion"], claim["by"]
        eid = ev["id"]

        if assertion == "catenary_snag":
            why = []
            if self.incident is not None:
                why = [w for w in self.incident["why"] if "derail" in w or "point" in w]
            if why:
                self.mem.upsert(
                    "contradiction", f"claim:{subject}:snag",
                    f"{by} reports a catenary snag, but that does not explain: {'; '.join(why)}.",
                    self.incident["evidence"] + [eid], t,
                )
                self.mem.recommend(
                    "CONFIRM_STATUS", subject,
                    f"Ask {subject}: are all coaches on the rails? Is the adjacent track clear?",
                    "The driver's mental model (snag) and the interlocking (points lost on the other track) disagree. "
                    "One closed question resolves it.",
                    self.incident["evidence"] + [eid], "critical", "Ten seconds of radio time.", t,
                )

        elif assertion == "derailed_fouling_adjacent":
            self.mem.resolve(f"claim:{subject}:snag", t, "driver confirms derailment", [eid])
            self.mem.upsert("fact", f"derailed:{subject}", f"{subject} derailed and fouling the adjacent track ({by}).", [eid], t)
            self.mem.upsert(
                "hypothesis", "fouled:adjacent", f"Adjacent track fouled by {subject} — confirmed by its driver.",
                [eid], t, confidence="high",
            )
            self.mem.resolve(f"status:{subject}", t, "derailed; fire and injuries reported", [eid])
            self.status_confirmed.add(subject)

        elif assertion == "no_train_approaching":
            exposed = [
                tid for tid in self._involved_ids()
                if tid != subject and tid not in self.status_confirmed and self.mem.is_open(f"status:{tid}")
            ]
            for tid in exposed:
                calls = self.no_answer.get(tid, [])
                ev_ids = self.mem.get(f"involved:{tid}").evidence + [eid]
                self.mem.upsert(
                    "contradiction", f"claim:no_train:{tid}",
                    f"{by}: 'no train is coming'. True now, but {tid} was already in this section when the alarms "
                    f"fired and its status is unconfirmed ({len(calls)} unanswered call(s)). It may already be involved.",
                    ev_ids, t,
                )
                self.mem.recommend(
                    "CONFIRM_STATUS", tid,
                    f"Confirm {tid} position and condition: crew phone, passengers via 112, or responders on site",
                    "The working assumption 'no other train' is not supported by the record.",
                    ev_ids, "critical", "A few minutes of one person's attention.", t,
                )

        elif assertion == "derailed":
            first_hand = subject.split()[0] in by or by.startswith("Adif")
            self._involve(subject, "high", [eid], t, f"reported derailed by {by}")
            if first_hand:
                self.mem.upsert("fact", f"derailed:{subject}", f"{subject} derailed (confirmed by {by}).", [eid], t)
                self.mem.resolve(f"status:{subject}", t, f"derailed — {by}", [eid])
                self.status_confirmed.add(subject)
                for key in [k for k in self.mem.items if k.startswith("claim:") and subject in k]:
                    self.mem.resolve(key, t, f"settled: {subject} derailed ({by})", [eid])
            else:
                self.mem.upsert(
                    "fact", f"derailed:{subject}:report", f"{subject} reported derailed by {by} (second-hand).", [eid], t,
                )

        elif assertion == "not_derailed":
            inv = self.mem.get(f"involved:{subject}")
            if inv is not None and inv.confidence == "high":
                self.mem.upsert(
                    "contradiction", f"claim:{subject}:not_derailed",
                    f"{by} says {subject} did not derail. This conflicts with {len(inv.evidence)} items in the record. "
                    "Do not close the loop on a single report.",
                    inv.evidence + [eid], t,
                )
                self.mem.recommend(
                    "CONFIRM_STATUS", f"{subject}:first-hand",
                    f"Get first-hand confirmation of {subject} before telling 112 it is safe",
                    f"A reassuring message to 112 would stand down help for {subject}. The record says otherwise.",
                    inv.evidence + [eid], "critical", "A few minutes before the message goes out.", t,
                )

    def _emergency(self, ev: dict, t: str) -> None:
        e = ev["emergency"]
        target = e["target"]
        if e["state"] == "mobilised":
            self.dispatched.add(target)
            self.mem.upsert("fact", f"emergency:{target}", f"Emergency services mobilised for {target}.", [ev["id"]], t)
            gaps = [tid for tid in self._involved_ids() if tid not in self.dispatched and tid != target]
            for tid in gaps:
                tr = self.trains.get(tid, {})
                self.mem.upsert(
                    "open_loop", f"dispatch_gap:{tid}",
                    f"Emergency services mobilised for {target} only. {tid} "
                    f"(track {tr.get('track', '?')}, {tr.get('on_board') or '?'} on board) has no confirmed dispatch.",
                    self.mem.get(f"involved:{tid}").evidence + [ev["id"]], t,
                )
        elif e["state"] == "on_scene":
            self.dispatched.add(target)
            self.mem.upsert("fact", f"onscene:{target}", f"First medical unit on scene at {target}.", [ev["id"]], t)
            self.mem.resolve(f"dispatch_gap:{target}", t, "responders on scene", [ev["id"]])

    # ------------------------------------------------------------------
    def _involved_ids(self) -> list[str]:
        return [k.split(":", 1)[1] for k in self.mem.items if k.startswith("involved:")]

    def _involve(self, train: str, conf: str, evidence: list[str], t: str, why: str) -> None:
        key = f"involved:{train}"
        item = self.mem.get(key)
        if item is not None and CONFIDENCE_RANK[item.confidence] > CONFIDENCE_RANK[conf]:
            conf = item.confidence
        reasons = (item.detail + "; " if item and item.detail else "") + why
        if item and why in (item.detail or ""):
            reasons = item.detail
        self.mem.upsert(
            "hypothesis", key, f"{train} possibly involved." if conf != "high" else f"{train} involved (high confidence).",
            evidence, t, confidence=conf, detail=reasons,
        )
        self.firsts.setdefault(f"involved:{train}", t)
        if conf == "high":
            self.firsts.setdefault(f"involved_high:{train}", t)


def is_before(a: str, b: str) -> bool:
    return parse_t(a) < parse_t(b)
