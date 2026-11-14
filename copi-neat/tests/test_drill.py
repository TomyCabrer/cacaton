"""Play each drill headless: with the protocol followed it ends well, with nobody acting it ends badly.

The engine is deterministic and has no clock of its own, so a scripted pilot and a scripted
tower can play a whole case in milliseconds.
"""

import pytest

from app.drill import DT, Drill
from app.drill_copilot import DrillCopilot
from app.protocols import CASES, PROTOCOLS


def new(case: str) -> Drill:
    d = Drill(DrillCopilot(force_offline=True))
    d.copi_to_pilot = True  # these tests cover the pilot fallback; the default (tower only) has its own test
    d.copi_speaks = True  # and Copi's voice (COPI_SPEAK=1); by default Copi only writes, which has its own test
    d.load(case)
    d.start()
    return d


def run(d: Drill, seconds: float, until=None) -> bool:
    for _ in range(int(seconds / DT)):
        if d.state != "running":
            return False
        d.tick(DT)
        if until and until():
            return True
    return until is None


def step(d: Drill, sid: str) -> dict:
    return next(s for s in d.protocol["steps"] if s["id"] == sid)


def act(d: Drill, sid: str) -> None:
    assert d.control_step(sid, "act")["ok"], sid


def send(d: Drill, sid: str) -> None:
    assert d.control_step(sid, "send")["ok"], sid


def drive_to_stand(d: Drill, pk: float, short_m: float = 60) -> None:
    """A careful scripted pilot: brake on a curve and stop just short of a point."""
    for _ in range(1200):
        me = d.me
        dist = me.ahead_m(pk) - short_m
        if me.v == 0 and dist < 80:
            return
        want = min(d.view_driver()["me"]["limit_kmh"] / 3.6 - 1, (2 * 0.6 * max(dist, 0)) ** 0.5)
        d.driver_input(notch=-4 if me.v > want + 1.5 else (-2 if me.v > want else (2 if dist > 30 and me.v < want - 2 else 0)))
        run(d, 0.5)
    raise AssertionError("never came to a stand")


def sees(d: Drill, kind: str) -> bool:
    return any(o["kind"] == kind for o in d.view_driver()["ahead"])


# ----------------------------------------------------------------------------- library
def test_every_case_has_one_protocol_and_protocols_stay_simple():
    assert len(CASES) == 5 and list(CASES)[0] == "urda" and CASES["urda"]["n"] == 1
    assert sorted(c["protocol"] for c in CASES.values()) == sorted(PROTOCOLS)
    assert {p["model"] for p in PROTOCOLS.values()} == {"claude-sonnet-5-5"}  # Copi is one model everywhere
    assert CASES["urda"]["simple"] and len(PROTOCOLS["P-05"]["steps"]) == 3
    for p in PROTOCOLS.values():
        assert len(p["steps"]) <= 4, p["id"]
    for c in CASES.values():  # simple train codes: the pilot is always Train A
        assert [t["id"] for t in c["trains"]] == ["A", "B"] and c["trains"][0]["controller"] == "human"
        assert all(t["name"] for t in c["trains"])


@pytest.mark.parametrize("case", list(CASES))
def test_nobody_acts_and_it_ends_badly(case):
    d = new(case)
    run(d, CASES[case]["max_s"] + 5)
    assert d.state == "ended" and d.outcome["result"] == "failed"


def test_views_keep_the_seats_apart():
    d = new("obstruction")
    run(d, 30)
    pilot, tower = d.view_driver(), d.view_control()
    assert "protocol" not in pilot and "trains" not in pilot and "signals" not in pilot
    assert "hazards" not in tower and not sees(d, "debris")
    assert "debris" not in str(tower)
    run(d, 60, until=lambda: sees(d, "debris"))
    assert sees(d, "debris") and "debris" not in str(d.view_control())


# ----------------------------------------------------------------------------- case 1
def test_obstruction_stop_call_holds_the_other_train_short():
    d = new("obstruction")
    assert run(d, 90, until=lambda: sees(d, "debris"))
    run(d, 6)  # the pilot needs a moment
    d.driver_report("obstruction", "other")
    assert d.protocol["id"] == "P-01" and d.protocol["model"] == "claude-sonnet-5-5"
    assert d.ctx["haz_track"] == 1 and d.ctx["threat"] == "Train B" and d.ctx["protect_signal"] == "S1-312"
    run(d, 8)  # the tower reads the first step
    act(d, "stop")
    act(d, "block")
    send(d, "details")
    run(d, 3)
    d.driver_say("Rocks across track 1 at PK 311.4. My track is clear.")
    d.driver_input(notch=-4)
    run(d, 150)
    assert d.outcome and d.outcome["result"] == "success", d.outcome
    ave = d._train("B")
    assert ave.v == 0 and ave.pk > 311.4 + 0.2
    assert not d.violations


def test_obstruction_pilot_can_make_the_emergency_call_from_the_cab():
    d = new("obstruction")
    run(d, 90, until=lambda: sees(d, "debris"))
    d.driver_act("rec")
    d.driver_report("obstruction", "other")
    assert step(d, "stop")["status"] == "done"
    run(d, 120)
    assert d._train("B").v == 0 and d.state == "running"


def test_obstruction_late_call_is_too_late():
    d = new("obstruction")
    run(d, 90, until=lambda: sees(d, "debris"))
    d.driver_report("obstruction", "other")
    run(d, 70)
    act(d, "stop")
    run(d, 60)
    assert d.outcome["result"] == "failed" and "obstruction" in d.outcome["title"]


# ----------------------------------------------------------------------------- case 2
def test_rough_ride_restriction_saves_the_following_train():
    d = new("rough_ride")
    assert run(d, 60, until=lambda: d.jolt is not None)
    assert d.me.status == "running"  # the first train gets a jolt, nothing more
    run(d, 8)
    d.driver_report("rough_ride")
    assert d.protocol["id"] == "P-02" and d.protocol["model"] == "claude-sonnet-5-5"
    assert d.reports[-1]["pk"] == 318.68 and d.reports[-1]["tagged"]
    assert any("independent sources" in a["text"] for a in d.alerts())
    send(d, "details")
    d.driver_say("Vertical, one hard bang, PK 318.7 track 1, 300 km/h.")
    act(d, "tsr")
    act(d, "warn")
    run(d, 400, until=lambda: d.outcome is not None)
    assert d.flags["examined_kmh"] <= 40
    assert d.outcome["result"] == "success" and not d.violations


def test_rough_ride_closing_the_track_at_once_also_works():
    d = new("rough_ride")
    run(d, 60, until=lambda: d.jolt is not None)
    d.driver_report("rough_ride")
    assert d.control_action("hold_signal", signal=d.ctx["protect_signal"])["ok"]
    assert run(d, 300, until=lambda: step(d, "examined")["status"] == "done")
    assert d._train("B").v == 0 and d.state == "running"


# ----------------------------------------------------------------------------- case 3
def play_dark_signal(d: Drill, authorise_early: bool = False, top_kmh: float = 28) -> None:
    assert d.signals["S2-312"].aspect == "caution" and d.signals["S2-314"].aspect == "stop"
    drive_to_stand(d, 314.0)
    assert 0 < d.me.ahead_m(314.0) < 150, d.me.pk
    assert any(o["kind"] == "signal" and o["aspect"] == "dark" for o in d.view_driver()["ahead"])
    d.driver_report("signal")
    assert d.protocol["id"] == "P-03" and d.protocol["model"] == "claude-sonnet-5-5"
    assert d.ctx["sig"] == "S2-314" and d.ctx["next_sig"] == "S2-315"
    send(d, "stand")
    d.driver_say("Stopped at S2-314. It is dark.")
    if not authorise_early:
        assert any("OCCUPIED" in a["text"] for a in d.alerts())
        assert run(d, 200, until=lambda: step(d, "section")["status"] == "done")
    send(d, "authority")
    d.driver_act("readback")
    run(d, 1)
    assert step(d, "authority")["status"] == "done"
    for _ in range(4000):
        if d.state != "running" or step(d, "on_sight")["status"] == "done":
            break
        d.driver_input(notch=2 if d.me.kmh < top_kmh - 3 else (-1 if d.me.kmh > top_kmh else 0))
        run(d, 0.5)


def test_dark_signal_authority_after_the_section_clears():
    d = new("dark_signal")
    play_dark_signal(d)
    assert step(d, "on_sight")["status"] == "done", d.outcome
    assert d.outcome["result"] == "success" and not d.violations, d.violations


def test_dark_signal_authority_into_an_occupied_section_is_a_breach():
    d = new("dark_signal")
    play_dark_signal(d, authorise_early=True)
    assert any("occupied" in v["text"] for v in d.violations)


def test_dark_signal_passed_without_authority_trips_the_brake():
    d = new("dark_signal")
    run(d, 200, until=lambda: d.me.ahead_m(314.0) < 0)
    assert d.me.eb and any("without authority" in v["text"] for v in d.violations)


def test_copi_never_relays_an_authority():
    d = new("dark_signal")
    drive_to_stand(d, 314.0)
    d.driver_report("signal")
    send(d, "stand")
    d.driver_say("Stopped. Signal is dark.")
    assert run(d, 200, until=lambda: step(d, "section")["status"] == "done")
    run(d, 60)  # the tower stays silent: Copi goes to the pilot
    assert d.advisory["step"] == "authority" and d.advisory["stage"] == "pilot"
    assert "Only the tower" in d.instruction["text"] and d.instruction["from"] == "copi"
    assert not d.authority and step(d, "authority")["status"] == "pending"


# ----------------------------------------------------------------------------- case 4
def test_derailment_fast_protocol_stops_the_second_train():
    d = new("derailment")
    assert run(d, 90, until=lambda: d.me.status == "derailed")
    alarms = " ".join(a["text"] for a in d.view_driver()["alarms"])
    assert "CATENARY" in alarms and "derail" not in alarms.lower()  # the cab does not say what happened
    assert "derail" not in str(d.view_control()["trains"]).lower()  # nor does the tower's panel
    run(d, 10)
    d.driver_report("train_fault", text="I think it is the catenary.")
    assert d.protocol["id"] == "P-04" and d.protocol["model"] == "claude-sonnet-5-5"
    assert d.ctx["threat"] == "Train B"
    assert any("catenary" in a["text"] for a in d.alerts())
    run(d, 8)
    act(d, "stop")
    assert run(d, 60, until=lambda: d.me.v == 0)
    send(d, "question")
    assert d.driver_act("inspect")["ok"]
    run(d, 9)
    assert "off the rails" in d.view_driver()["jobs"]["inspect"]["text"]
    assert "derailed" not in str(d.llm_view()["train_describer"])  # the panel cannot know until the pilot has looked
    d.driver_act("report_finding")
    assert "derailed" in str(d.llm_view()["train_describer"])
    assert run(d, 90, until=lambda: d._train("B").v == 0)  # Train B brakes to a stand after the call
    act(d, "block")
    act(d, "emergency")
    run(d, 1)
    assert d.outcome and d.outcome["result"] == "success", (d.outcome, [s["id"] for s in d.protocol["steps"] if s["status"] != "done"])
    alvia = d._train("B")
    assert alvia.v == 0 and alvia.pk < d._foul()["lo"]


def test_derailment_clips_alone_protect_the_other_track():
    d = new("derailment")
    run(d, 90, until=lambda: d.me.status == "derailed")
    run(d, 60, until=lambda: d.me.v == 0)
    d.driver_act("clip")
    run(d, 200)
    assert d.state == "running" and d._train("B").v == 0


# ----------------------------------------------------------------------------- Copi
def test_copi_tells_the_tower_first_then_the_pilot_if_nobody_answers():
    d = new("obstruction")
    run(d, 90, until=lambda: sees(d, "debris"))
    d.driver_report("obstruction", "other")
    first = [m for m in d.radio if m["from"] == "copi"]
    assert len(first) == 1 and first[0]["to"] == "control" and "Emergency call" in first[0]["text"]
    assert d.advisory["stage"] == "tower"
    assert not any(m["from"] == "copi" for m in d.view_driver()["radio"])  # the pilot has heard nothing yet
    run(d, 25)  # no R, no action
    assert d.advisory["stage"] == "pilot"
    told = [m for m in d.view_driver()["radio"] if m["from"] == "copi"]
    assert told and "emergency call button" in told[-1]["text"]
    d.driver_act("rec")
    run(d, 1)
    assert step(d, "stop")["status"] == "done" and d.flags["escalations"] == 1


@pytest.mark.parametrize("to_pilot", [True, False])
def test_r_is_final_capi_says_nothing_more_about_that_step(to_pilot):
    d = new("obstruction")
    d.copi_to_pilot = to_pilot
    run(d, 90, until=lambda: sees(d, "debris"))
    d.driver_report("obstruction", "other")
    run(d, 4)
    assert d.copi_ack("control")["ok"] and d.advisory["stage"] == "acked"
    said = len([m for m in d.radio if m["from"] == "copi"])
    run(d, 60)  # the tower heard it and does nothing: its call
    assert d.advisory is None or d.advisory["stage"] == "acked"
    assert len([m for m in d.radio if m["from"] == "copi" and m.get("speak")]) == said  # not one more spoken line
    assert not any(m["from"] == "copi" for m in d.view_driver()["radio"])
    assert d.flags.get("reminders", 0) == 0 and d.flags.get("escalations", 0) == 0
    assert not d.copi_ack("control")["ok"]  # nothing left to acknowledge


def test_capi_lines_come_in_three_urgencies():
    d = new("obstruction")  # seconds matter: the emergency call is urgent
    run(d, 90, until=lambda: sees(d, "debris"))
    d.driver_report("obstruction", "other")
    first = [m for m in d.radio if m["from"] == "copi"][-1]
    assert first["level"] == "urgent" and first["urgent"] and first["speak"] and first["text"].startswith("Urgent. ")
    assert d.advisory["level"] == "urgent" and not d.advisory["text"].startswith("Urgent")
    act(d, "stop")
    run(d, 1)
    nxt = [m for m in d.radio if m["from"] == "copi"][-1]  # holding the signal behind the call: important
    assert nxt["level"] == "important" and not nxt["urgent"] and nxt["text"].startswith("Tower. Hold ")
    act(d, "block")
    send(d, "details")
    d.driver_say("Rocks across track 1 at PK 311.4. My track is clear.")
    run(d, 1)
    wait = [m for m in d.radio if m["from"] == "copi"][-1]  # only waiting for the other train to stop: info
    assert wait["level"] == "info" and not wait["speak"] and wait["text"].startswith("Waiting. ")
    assert d.advisory["stage"] == "quiet" and not d.copi_ack("control")["ok"]  # needs no R

    d = new("rough_ride")  # minutes, not seconds: the opening line is important, not urgent
    run(d, 120, until=lambda: d.jolt is not None)
    d.driver_report("rough_ride")
    first = [m for m in d.radio if m["from"] == "copi"][-1]
    assert first["level"] == "important" and first["text"].startswith("Tower. ")


def test_capi_repeats_an_unanswered_line_a_few_times_then_drops_it():
    def silence(case, report):
        d = Drill(DrillCopilot(force_offline=True))
        d.copi_speaks = True
        d.load(case)
        d.start()
        report(d)
        t0, step0 = d.t, d.advisory["step"]
        while d.state == "running" and d.t - t0 < 150 and d.advisory and d.advisory["step"] == step0:
            d.tick(DT)
            if d.advisory and d.advisory["stage"] == "silent":
                break
        return d, [m["t"] - t0 for m in d.radio if m["from"] == "copi" and m.get("repeat")]

    def rocks(d):
        run(d, 90, until=lambda: sees(d, "debris"))
        d.driver_report("obstruction", "other")

    def jolt(d):
        run(d, 120, until=lambda: d.jolt is not None)
        d.driver_report("rough_ride")

    d, urgent = silence("obstruction", rocks)
    assert len(urgent) == 2 and d.advisory["stage"] == "silent"  # twice, then quiet
    said = len(d.radio)
    run(d, 20)
    assert not [m for m in d.radio[said:] if m["from"] == "copi" and m.get("speak")]
    assert d.copi_ack("control")["ok"] and d.advisory["stage"] == "acked"  # R still closes it

    d, important = silence("rough_ride", jolt)
    assert len(important) == 1 and d.advisory["stage"] == "silent"  # once, then quiet
    assert urgent[0] < important[0]  # an urgent line comes back sooner


def test_acting_at_once_needs_no_r_and_copi_moves_on():
    d = new("obstruction")
    run(d, 90, until=lambda: sees(d, "debris"))
    d.driver_report("obstruction", "other")
    act(d, "stop")
    run(d, 1)
    assert d.advisory["step"] == "block" and d.advisory["stage"] == "tower"
    assert d.flags.get("escalations", 0) == 0


def test_copi_relays_a_pilot_step_and_the_pilots_answer_counts():
    d = new("rough_ride")
    run(d, 60, until=lambda: d.jolt is not None)
    d.driver_report("rough_ride")
    run(d, 40)  # tower silent: Copi asks the pilot for the facts itself
    st = step(d, "details")
    assert st["status"] == "sent" and st["sent_by"] == "copi"
    assert d.instruction["from"] == "copi" and d.instruction["step"] == "details"
    assert d.copi_ack("driver")["ok"]
    d.driver_say("PK 318.7, track 1, vertical, hard.")
    run(d, 1)
    assert st["status"] == "done"


def test_speech_from_the_pilot_opens_a_protocol_and_echoes_are_dropped():
    d = new("obstruction")
    run(d, 30)
    assert d.heard("control", "ok we are rolling")["ok"] and d.protocol is None
    assert d.heard("driver", "there are rocks on the other track")["ok"]
    assert d.protocol["id"] == "P-01" and d.ctx["haz_track"] == 1
    said = d.radio[-1]["text"]
    assert d.heard("control", said).get("dropped") == "echo"  # the microphone hearing Copi's own voice


# ----------------------------------------------------------------------------- the second laptop
def test_second_laptop_needs_the_join_key_and_can_long_poll():
    from fastapi.testclient import TestClient

    import app.main as m

    c = TestClient(m.app)
    key = m.app.state.access_key
    remote = {"host": "abc.trycloudflare.com", "cf-connecting-ip": "203.0.113.9"}
    assert c.get("/api/drill/state?role=driver", headers=remote).status_code == 403
    assert c.get("/api/state", headers=remote).status_code == 403  # the replay API spends the same Claude key
    assert c.get("/drill/driver?k=wrong", headers=remote).status_code == 403
    page = c.get(f"/drill/driver?k={key}", headers=remote)
    assert page.status_code == 200 and "memoria_key" in page.headers.get("set-cookie", "")
    assert c.get("/api/drill/state?role=driver", headers=remote).status_code == 200  # the cookie carries the key now
    fresh = TestClient(m.app)  # no cookie: claiming to be localhost does not help a request that was forwarded
    assert fresh.get("/api/drill/state?role=driver", headers={"host": "localhost", "x-forwarded-for": "203.0.113.9"}).status_code == 403
    assert fresh.get("/api/drill/state?role=driver").status_code == 200  # this laptop itself needs no key

    assert c.post("/api/drill/load", json={"case": "obstruction"}).status_code == 200
    s = c.get("/api/drill/poll?role=driver&v=-1").json()
    assert s["role"] == "driver" and s["me"]["id"] == "A" and s["me"]["name"] == "Alvia 2264" and "protocol" not in s
    assert c.get("/api/drill/state?role=control").json()["online"]["driver"] >= 1  # a polling pilot counts as seated
    c.post("/api/drill/load", json={"case": None})


def test_by_default_copi_never_talks_to_the_pilot_it_reminds_the_tower():
    d = Drill(DrillCopilot(force_offline=True))
    d.load("obstruction")
    d.start()
    assert not d.copi_to_pilot and not d.copi_speaks
    run(d, 90, until=lambda: sees(d, "debris"))
    d.driver_report("obstruction", "other")
    run(d, 60)  # the tower stays silent
    assert [m for m in d.radio if m["from"] == "copi"] and not any(m.get("speak") for m in d.radio)  # Copi writes, it does not talk
    assert not any(m["from"] == "copi" for m in d.view_driver()["radio"])  # only the tower talks to the pilot
    assert d.flags.get("reminders", 0) >= 1 and d.flags.get("escalations", 0) == 0
    assert d.advisory["stage"] in ("tower", "silent")


# ----------------------------------------------------------------------------- case 1: Urda, the LZB failure
def urda(**kw) -> Drill:
    d = Drill(DrillCopilot(force_offline=True))  # the real defaults: Copi writes to the tower only
    for k, v in kw.items():
        setattr(d, k, v)
    d.load("urda")
    d.start()
    return d


def copi_lines(d: Drill) -> list[dict]:
    return [m for m in d.radio if m["from"] == "copi"]


def stop_train(d: Drill) -> None:
    d.driver_input(eb=True)
    assert run(d, 80, until=lambda: d.me.v == 0)


def drive_on_sight(d: Drill, kmh: float = 34) -> None:
    d.driver_input(eb=False)
    for _ in range(800):
        if d.state != "running":
            return
        d.driver_input(notch=4 if d.me.kmh < kmh - 2 else (-1 if d.me.kmh > kmh + 2 else 0))
        run(d, 0.25)


def test_the_server_opens_on_urda_ready_to_start():
    import app.drill_api as api

    api._drill = None
    d = api.get_drill()
    assert d.case["id"] == "urda" and d.state == "ready"
    api._drill = None


def test_urda_runs_then_lzb_fails_and_the_tower_goes_blind():
    d = urda()
    assert d.protocol is None and not d.lzb_down
    tower = d.view_control()
    assert not tower["blind"] and [t["label"] for t in tower["trains"]] == ["Train A", "Train B"]
    assert all(t["kmh"] is None for t in tower["trains"])  # the panel shows where a train is, never how fast
    assert not d.view_driver()["alarms"] and d.view_driver()["me"]["limit_known"]
    run(d, 4.2)
    assert d.lzb_down and d.clock.startswith("08:31:0") and d.protocol["id"] == "P-05"
    assert [s["id"] for s in d.protocol["steps"]] == ["stop", "stood", "on_sight"]
    seen = {t["id"]: t["pk"] for t in d.view_control()["trains"]}
    run(d, 20)
    tower = d.view_control()
    assert tower["blind"] and all(t["lost"] and t["pk"] == seen[t["id"]] and t["kmh"] is None for t in tower["trains"])
    assert d.me.pk > seen["A"] + 0.5 and "gap" not in str(tower["lzb"])  # the train has moved on; the panel has not
    pilot = d.view_driver()
    assert pilot["lzb"]["down"] and any("LZB FAILED" in a["text"] for a in pilot["alarms"]) and not pilot["me"]["limit_known"]
    assert not any(o["kind"] == "train" for o in pilot["ahead"])  # Train B is far beyond what the pilot can see


def test_urda_stop_by_voice_then_on_sight_and_copi_writes_nothing():
    d = urda()
    run(d, 10)
    assert d.heard("control", "All trains, stop now")["ok"]
    assert step(d, "stop")["status"] == "done" and step(d, "stop")["note"] == "Order heard."
    assert d.heard("driver", "what a view today")["ok"] and d.heard("control", "did you see the match last night")["ok"]
    assert d.driver_report("signal")["ok"] and d.protocol["id"] == "P-05"  # nothing the pilot says opens another protocol
    stop_train(d)
    run(d, 10)
    assert step(d, "stood")["status"] == "done" and d._train("B").v == 0
    assert d.heard("control", "Train A, continue at 40")["ok"] and d.release == "on_sight"
    drive_on_sight(d)
    assert d.outcome["result"] == "success" and d.outcome["title"] == "Stopped, then on sight at 40", d.outcome
    assert not copi_lines(d) and not d.violations and d.advisory is None  # nothing went wrong, so Copi wrote nothing
    assert "08:53" in " ".join(d.outcome["reality"])
    assert any("lost from the panel" in m["label"] for m in d.outcome["metrics"])
    assert all(t["stopped"] is not None for t in d.view_control()["trains"])  # the debrief shows where they really were


def test_urda_needs_no_microphone():
    d = urda()  # nothing is heard at all: the steps tick from what the trains do
    run(d, 10)
    stop_train(d)
    assert step(d, "stop")["note"] == "Train A is braking."
    run(d, 10)
    drive_on_sight(d)
    assert d.outcome["result"] == "success" and not copi_lines(d)


def test_urda_copi_flags_a_train_that_keeps_moving_once_and_in_writing():
    d = urda()
    run(d, 4 + 12)
    lines = copi_lines(d)
    assert len(lines) == 1 and "still moving" in lines[0]["text"] and lines[0]["level"] == "urgent" and not lines[0]["speak"]
    assert d.advisory["stage"] == "tower" and d.view_control()["copi_log"][-1]["key"] == "moving"
    assert not any(m["from"] == "copi" for m in d.view_driver()["radio"])  # Copi writes to the tower only
    d.driver_input(eb=True)
    run(d, 2)
    assert d.advisory is None and d.view_control()["copi_log"][-1]["cleared"]  # no longer true: the card goes
    run(d, 60)
    assert len(copi_lines(d)) == 1


def test_urda_r_is_final_for_a_flag():
    d = urda()
    run(d, 10)
    stop_train(d)
    run(d, 8)
    d.driver_input(eb=False)
    for _ in range(200):
        d.driver_input(notch=4 if d.me.kmh < 70 else 0)
        run(d, 0.25)
        if d.advisory:
            break
    assert "On sight is 40" in d.advisory["text"]
    assert d.copi_ack("control")["ok"] and d.advisory["stage"] == "acked" and not d.copi_ack("control")["ok"]
    said = len(copi_lines(d))
    for _ in range(120):  # 30 s at 70 km/h, still far too fast: Copi does not bring it up again
        d.driver_input(notch=4 if d.me.kmh < 70 else 0)
        run(d, 0.25)
    assert len(copi_lines(d)) == said and d.advisory["stage"] == "acked" and d.view_control()["copi_log"][-1]["heard"]


def play_wrong_release(d: Drill, heed_copi: bool) -> None:
    run(d, 10)
    d.heard("control", "all trains stop")
    stop_train(d)
    run(d, 8)
    d.heard("control", "Train A, you can resume normal running")
    run(d, 0.2)
    assert "cleared for normal running" in d.advisory["text"] and any("normal running" in v["text"] for v in d.violations)
    d.driver_input(eb=False)
    warned = None
    for _ in range(2400):  # a pilot who trusts the release
        if d.state != "running":
            break
        if warned is None and any(e["key"] == "closing" for e in d.flag_log):
            warned = d.t
        if heed_copi and warned is not None and d.t - warned > 6:  # the tower reads the flag and stops the train
            d.driver_input(eb=True)
        elif d.me.kmh < 195:
            d.driver_input(notch=4)
        run(d, 0.25)
    assert warned is not None


def test_urda_normal_running_ends_in_the_collision():
    d = urda()
    play_wrong_release(d, heed_copi=False)
    assert d.outcome["result"] == "failed" and d.outcome["title"] == "Train A ran into Train B", d.outcome


def test_urda_heeding_copi_avoids_the_collision_but_is_no_success():
    d = urda()
    play_wrong_release(d, heed_copi=True)
    assert d.outcome["result"] == "near_miss" and d._gap_m() > 0, d.outcome
    assert any("after the stop" in v["text"] for v in d.violations)


def test_urda_a_clearance_before_the_stop_is_answered_with_stop_first():
    d = urda()
    run(d, 8)
    d.heard("control", "Train A, go at 200")  # the tower clears a speed while nothing has stopped
    run(d, 0.2)
    assert d.advisory["text"] == "Train A cleared for 200 km/h. First step: stop all trains."
    assert any("before the trains had stopped" in v["text"] for v in d.violations)
    run(d, 12)
    assert len(copi_lines(d)) == 1  # one flag for it: "still moving" would say the same thing twice
    d.heard("control", "stop the train, then we continue at 40")  # a stop word before the stand is the stop order
    assert d.release == "hold"
    stop_train(d)
    run(d, 8)
    assert d.advisory is None and len(copi_lines(d)) == 1
    d.heard("control", "Train A, go at 200")  # the same words after the stop: now the rule is on sight
    run(d, 0.2)
    assert d.advisory["text"] == "Train A cleared for 200 km/h. LZB is down: on sight, 40 at most."

    d = urda()
    run(d, 8)
    d.heard("control", "continue at 40")  # right order, wrong moment
    run(d, 0.2)
    assert d.advisory["text"] == "Train A cleared to continue. First step: stop all trains."
    stop_train(d)
    run(d, 1)
    assert d.advisory is None and d.release == "on_sight"  # once it has stopped, on sight is the right order


def test_urda_the_pilots_train_picks_up_speed_quickly():
    d = urda()
    run(d, 10)
    stop_train(d)
    run(d, 8)
    d.driver_input(eb=False)
    d.driver_input(notch=4)
    t0 = d.t
    assert run(d, 30, until=lambda: d.me.kmh >= 40) and d.t - t0 < 10  # 0 to 40 km/h in under ten seconds


def test_urda_copi_can_go_by_the_radio_alone():
    d = urda(onboard=False)
    run(d, 20)
    assert [m["text"] for m in copi_lines(d)] == ["No stop order yet."]
    d.heard("control", "stop")
    run(d, 1)
    assert d.advisory is None and len(copi_lines(d)) == 1


@pytest.mark.parametrize("words,want", [
    ("all trains stop immediately", ("stop", 0)),
    ("para el tren", ("stop", 0)),
    ("continue at 40", ("on_sight", 40)),
    ("proceed on sight and stop short of train b", ("on_sight", 40)),
    ("do not go faster than 40 kilometers per hour", ("on_sight", 40)),
    ("continúa a 40", ("on_sight", 40)),
    ("continue at 80", ("faster", 80)),
    ("resume normal running", ("faster", 0)),
    ("how are you", None),
    ("move ahead slowly and be ready to stop", None),  # not a stop order: Copi's model reads it
    ("stop, do not continue", ("stop", 0)),
])
def test_urda_orders_are_read_from_plain_words(words, want):
    assert Drill._read_order(words) == want
