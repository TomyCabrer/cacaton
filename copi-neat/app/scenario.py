"""Scenario loading, sim-time helpers and train-describer interpolation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios"


def parse_t(s: str) -> datetime:
    return datetime.fromisoformat(s)


def fmt_t(d: datetime) -> str:
    return d.isoformat(timespec="seconds")


def add_s(s: str, seconds: float) -> str:
    return fmt_t(parse_t(s) + timedelta(seconds=seconds))


def seconds_between(a: str, b: str) -> float:
    return (parse_t(b) - parse_t(a)).total_seconds()


def load(name: str = "adamuz") -> dict:
    data = json.loads((SCENARIO_DIR / f"{name}.json").read_text())
    data["events"].sort(key=lambda e: e["t"])
    return data


def fed(event: dict, integrations: bool) -> bool:
    """Would Copi see this event live?

    ctc       – available in a control room today (interlocking, energy SCADA, GSM-R voice)
    proposed  – needs an integration that does not exist yet (onboard telemetry, 112 feed, sensors…)
    hindsight – only known after the investigation; never fed
    """
    feed = event.get("feed", "ctc")
    if feed == "ctc":
        return True
    if feed == "proposed":
        return integrations
    return False


def train_positions(scenario: dict, t: str) -> list[dict]:
    """Interpolate train-describer positions at sim time t (approximate, for display and proximity)."""
    out = []
    now = parse_t(t)
    for train in scenario["trains"]:
        kfs = train["keyframes"]
        first, last = parse_t(kfs[0]["t"]), parse_t(kfs[-1]["t"])
        if now < first - timedelta(minutes=5):
            continue
        if now <= first:
            pk, status, speed = kfs[0]["pk"], kfs[0]["status"], None
        elif now >= last:
            pk, status, speed = kfs[-1]["pk"], kfs[-1]["status"], 0.0
        else:
            for a, b in zip(kfs, kfs[1:]):
                ta, tb = parse_t(a["t"]), parse_t(b["t"])
                if ta <= now <= tb:
                    span = (tb - ta).total_seconds() or 1.0
                    f = (now - ta).total_seconds() / span
                    pk = a["pk"] + (b["pk"] - a["pk"]) * f
                    speed = abs(b["pk"] - a["pk"]) / span * 3600.0
                    status = a["status"]
                    break
        out.append(
            {
                "id": train["id"],
                "operator": train["operator"],
                "route": train["route"],
                "track": train["track"],
                "on_board": train.get("on_board"),
                "pk": round(pk, 3),
                "speed_kmh": None if speed is None else round(speed),
                "status": status,
            }
        )
    return out


def trains_near(scenario: dict, t: str, pk: float, km: float) -> list[dict]:
    return [tr for tr in train_positions(scenario, t) if abs(tr["pk"] - pk) <= km]
