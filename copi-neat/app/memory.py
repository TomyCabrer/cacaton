"""Working memory for a rail control room.

Holds what the operator would otherwise have to keep in their head under stress:
facts, hypotheses, open loops (things started and not finished), contradictions,
and recommendations waiting for a human decision. Every change is logged so the
timeline can be audited afterwards.

Copi never acts on the railway. A recommendation only becomes an action when
a human approves it, and the approval is recorded with who, when and why.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

ACTIONS = (
    "STOP_TRAFFIC",
    "SPEED_RESTRICTION",
    "INSPECT_TRACK",
    "CALL_TRAIN",
    "DISPATCH_EMERGENCY",
    "NOTIFY_112",
    "CONFIRM_STATUS",
)
URGENCY_RANK = {"medium": 1, "high": 2, "critical": 3}
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
KINDS = ("fact", "hypothesis", "open_loop", "contradiction", "watch")


def wall_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Item:
    key: str
    kind: str
    text: str
    evidence: list[str]
    created: str
    updated: str
    confidence: str | None = None
    detail: str | None = None
    status: str = "open"
    resolved_at: str | None = None
    resolution: str | None = None
    source: str = "rules"


@dataclass
class Recommendation:
    id: str
    key: str
    action: str
    target: str
    title: str
    rationale: str
    evidence: list[str]
    urgency: str
    cost_if_wrong: str
    created: str
    source: str = "rules"
    status: str = "pending"
    escalated_from: str | None = None
    decided_at: str | None = None
    decided_wall: str | None = None
    reason: str | None = None


@dataclass
class WorkingMemory:
    items: dict[str, Item] = field(default_factory=dict)
    recs: list[Recommendation] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)
    _rec_seq: int = 0

    # ----- items -------------------------------------------------------
    def upsert(
        self,
        kind: str,
        key: str,
        text: str,
        evidence: list[str],
        t: str,
        confidence: str | None = None,
        detail: str | None = None,
        source: str = "rules",
    ) -> Item:
        assert kind in KINDS, kind
        item = self.items.get(key)
        if item is None:
            item = Item(key, kind, text, list(dict.fromkeys(evidence)), t, t, confidence, detail, source=source)
            self.items[key] = item
            self._log(t, "memory.add", f"{kind}: {text}", key=key, evidence=item.evidence)
            return item
        changed = item.text != text or item.confidence != confidence or item.detail != detail
        merged = list(dict.fromkeys(item.evidence + evidence))
        if merged != item.evidence:
            changed = True
        item.text, item.confidence, item.detail, item.evidence = text, confidence, detail, merged
        if item.status == "resolved":
            item.status, item.resolved_at, item.resolution = "open", None, None
            changed = True
        if changed:
            item.updated = t
            self._log(t, "memory.update", f"{kind}: {text}", key=key, evidence=merged)
        return item

    def resolve(self, key: str, t: str, resolution: str, evidence: list[str] | None = None) -> None:
        item = self.items.get(key)
        if item is None or item.status == "resolved":
            return
        item.status, item.resolved_at, item.resolution = "resolved", t, resolution
        if evidence:
            item.evidence = list(dict.fromkeys(item.evidence + evidence))
        item.updated = t
        self._log(t, "memory.resolve", f"{item.kind}: {item.text} → {resolution}", key=key)

    def get(self, key: str) -> Item | None:
        return self.items.get(key)

    def is_open(self, key: str) -> bool:
        item = self.items.get(key)
        return item is not None and item.status == "open"

    # ----- recommendations ---------------------------------------------
    def recommend(
        self,
        action: str,
        target: str,
        title: str,
        rationale: str,
        evidence: list[str],
        urgency: str,
        cost_if_wrong: str,
        t: str,
        source: str = "rules",
        key: str | None = None,
    ) -> Recommendation | None:
        """Add a recommendation, or escalate an existing one.

        Same key + still pending: update in place if urgency rises.
        Same key + already decided: only re-raise if urgency rises, so a human
        "no" is respected until the evidence changes.
        """
        assert action in ACTIONS, action
        key = key or f"{action}:{target}".lower()
        latest = next((r for r in reversed(self.recs) if r.key == key), None)
        if latest is not None:
            higher = URGENCY_RANK[urgency] > URGENCY_RANK[latest.urgency]
            if latest.status == "pending":
                if higher:
                    old = latest.urgency
                    latest.urgency, latest.title, latest.rationale = urgency, title, rationale
                    latest.cost_if_wrong = cost_if_wrong
                    latest.evidence = list(dict.fromkeys(latest.evidence + evidence))
                    latest.escalated_from = old
                    self._log(t, "rec.escalate", f"{title} ({old} → {urgency})", rec=latest.id)
                    return latest
                latest.evidence = list(dict.fromkeys(latest.evidence + evidence))
                return None
            if not higher:
                return None
        self._rec_seq += 1
        rec = Recommendation(
            id=f"REC-{self._rec_seq:03d}",
            key=key,
            action=action,
            target=target,
            title=title,
            rationale=rationale,
            evidence=list(dict.fromkeys(evidence)),
            urgency=urgency,
            cost_if_wrong=cost_if_wrong,
            created=t,
            source=source,
            escalated_from=latest.urgency if latest is not None else None,
        )
        self.recs.append(rec)
        verb = "rec.reraise" if latest is not None else "rec.add"
        self._log(t, verb, f"[{urgency}] {title}", rec=rec.id, source=source, evidence=rec.evidence)
        return rec

    def decide(self, rec_id: str, decision: str, reason: str | None, t: str) -> Recommendation:
        rec = next((r for r in self.recs if r.id == rec_id), None)
        if rec is None:
            raise KeyError(rec_id)
        if rec.status != "pending":
            raise ValueError(f"{rec_id} already {rec.status}")
        if decision not in ("approved", "rejected", "deferred"):
            raise ValueError(decision)
        rec.status, rec.decided_at, rec.decided_wall, rec.reason = decision, t, wall_now(), reason
        self._log(t, f"human.{decision}", f"{rec.title}" + (f" — reason: {reason}" if reason else ""), rec=rec.id)
        return rec

    def supersede(self, match, t: str, reason: str) -> None:
        """Close pending recommendations that events have overtaken. Logged, never silent."""
        for r in self.recs:
            if r.status == "pending" and match(r):
                r.status, r.decided_at, r.reason = "superseded", t, reason
                self._log(t, "rec.superseded", f"{r.title} — {reason}", rec=r.id)

    def pending(self) -> list[Recommendation]:
        return [r for r in self.recs if r.status == "pending"]

    # ----- audit -------------------------------------------------------
    def _log(self, t: str, what: str, text: str, **extra) -> None:
        self.log.append({"sim": t, "wall": wall_now(), "what": what, "text": text, **extra})

    def note(self, t: str, what: str, text: str, **extra) -> None:
        self._log(t, what, text, **extra)

    def snapshot(self) -> dict:
        by_kind: dict[str, list[dict]] = {k: [] for k in KINDS}
        for item in self.items.values():
            by_kind[item.kind].append(asdict(item))
        return {
            "items": by_kind,
            "recommendations": [asdict(r) for r in self.recs],
            "log": self.log[-200:],
        }
