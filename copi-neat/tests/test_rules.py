"""Replay the Adamuz scenario through the rule engine and check what Copi knew, and when."""

import pytest

from app import scenario as S
from app.memory import WorkingMemory
from app.rules import RuleEngine


def replay(integrations: bool, until: str | None = None):
    sc = S.load("adamuz")
    mem = WorkingMemory()
    rules = RuleEngine(sc, mem)
    for ev in sc["events"]:
        if until and ev["t"] > until:
            break
        if S.fed(ev, integrations):
            rules.on_event(ev, ev["t"])
    return sc, mem, rules


def pending(mem, action=None, urgency=None):
    return [
        r for r in mem.recs
        if r.status == "pending" and (action is None or r.action == action) and (urgency is None or r.urgency == urgency)
    ]


def test_hindsight_events_never_fed():
    sc = S.load("adamuz")
    for ev in sc["events"]:
        if ev["feed"] == "hindsight":
            assert not S.fed(ev, True) and not S.fed(ev, False)


def test_precursors_flag_defect_before_crash_with_integrations():
    _, mem, rules = replay(True, until="2026-01-18T19:10:00")
    hyp = mem.get("defect:T1:318.5")
    assert hyp is not None and hyp.confidence == "high"
    assert rules.firsts["defect:flagged"] == "2026-01-17T21:46:00"  # track-circuit drift tips it to medium
    assert rules.firsts["defect:critical"] == "2026-01-18T17:21:00"  # first wheel impact
    crit = pending(mem, "SPEED_RESTRICTION", "critical")
    assert crit and set(["P2", "P3", "P5"]) <= set(crit[0].evidence)


def test_precursors_invisible_without_integrations():
    _, mem, rules = replay(False, until="2026-01-18T19:10:00")
    assert "defect:flagged" not in rules.firsts
    assert not mem.recs


def test_no_advice_during_the_eight_seconds():
    _, mem, rules = replay(True, until="2026-01-18T19:43:42")
    assert rules.banner and rules.banner["kind"] == "automatic"
    in_window = [r for r in mem.recs if "2026-01-18T19:43:00" <= r.created <= "2026-01-18T19:43:42"]
    assert in_window == []


@pytest.mark.parametrize("integrations,expected", [(True, "2026-01-18T19:43:34"), (False, "2026-01-18T19:43:37")])
def test_alvia_flagged_within_seconds(integrations, expected):
    _, _, rules = replay(integrations)
    assert rules.firsts["involved:ALVIA 2384"] == expected


def test_incident_fusion_dispatches_to_both_trains_with_ctc_data_only():
    _, mem, rules = replay(False, until="2026-01-18T19:43:45")
    assert rules.banner["kind"] == "incident"
    dispatch = pending(mem, "DISPATCH_EMERGENCY", "critical")
    assert dispatch and "2 trains" in dispatch[0].title
    assert mem.is_open("status:ALVIA 2384") and mem.is_open("status:IRYO 6189")


def test_operator_no_train_claim_is_challenged():
    _, mem, _ = replay(False, until="2026-01-18T19:49:35")
    c = mem.get("claim:no_train:ALVIA 2384")
    assert c is not None and c.status == "open"
    assert {"R5", "R6"} <= set(c.evidence)


def test_false_all_clear_does_not_close_the_loop():
    _, mem, _ = replay(True, until="2026-01-18T20:09:58")
    c = mem.get("claim:ALVIA 2384:not_derailed")
    assert c is not None and c.status == "open"
    assert mem.is_open("status:ALVIA 2384")


def test_first_hand_report_settles_alvia_status():
    _, mem, _ = replay(True)
    assert not mem.is_open("status:ALVIA 2384")
    assert not mem.is_open("claim:ALVIA 2384:not_derailed")
    assert not mem.is_open("dispatch_gap:ALVIA 2384")


def test_rejected_recommendation_is_only_reraised_on_escalation():
    mem = WorkingMemory()
    r = mem.recommend("INSPECT_TRACK", "z", "inspect", "why", ["P2"], "medium", "cheap", "t1")
    mem.decide(r.id, "rejected", "crew busy", "t2")
    assert mem.recommend("INSPECT_TRACK", "z", "inspect", "why", ["P3"], "medium", "cheap", "t3") is None
    again = mem.recommend("INSPECT_TRACK", "z", "inspect now", "why", ["P5"], "critical", "cheap", "t4")
    assert again is not None and again.escalated_from == "medium" and again.id != r.id


def test_incident_supersedes_precursor_recommendations():
    _, mem, _ = replay(True, until="2026-01-18T19:43:45")
    precursor = [r for r in mem.recs if r.action in ("SPEED_RESTRICTION", "INSPECT_TRACK")]
    assert precursor and all(r.status == "superseded" for r in precursor)
    assert not mem.is_open("defect:T1:318.5:exposure")
