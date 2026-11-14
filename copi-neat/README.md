# Copi

> Saved version "neat", 14 Nov 2026: the white, one-drill version (Urda LZB failure, Copi writes only). A copy of `memoria/` at that moment; work continues in `memoria/`.

**Working memory for rail control rooms and train drivers. It remembers, connects and proposes. The human decides.**

On 18 January 2026 two high-speed trains collided at Adamuz (Córdoba) and 46 people died. Every piece of information needed to act was somewhere: a track-circuit drift the night before, a driver's "slight vibration", three trains that hit the broken rail hours earlier, a signal that dropped, a power loss, two unanswered calls to the Alvia. It sat in different systems, people and shifts, and nobody put it together in time. Copi is a prototype of the missing piece: a shared memory that holds everything at once, so a stressed operator doesn't have to.

Read [`docs/what-happened.md`](docs/what-happened.md) for the accident research and sources.

## Demo in 3 acts (replay of the real Adamuz timeline)

| Act | Real time scale | What Copi does |
|---|---|---|
| **1 · The 22 hours** | Aug 2025 → 18 Jan 19:09 | Correlates weak signals by location across systems (union letter, inspection, track-circuit drift, driver report, wheel impacts). Escalates from *watch* to *inspect* to *close or restrict*. **Only with the proposed integrations**: today these signals live in separate silos or are never recorded. |
| **2 · The 8 seconds** | 19:43:19 → 19:43:45 | Nothing but observe. Banner: automatic protection is the only layer fast enough. Copi does not pretend otherwise. |
| **3 · The 33 minutes** | 19:43:45 → 20:35 | Fuses signal drop + power loss + train describer into "incident, two trains in zone, 478 people" at 19:43:45. Tracks unanswered calls. Flags "no train is coming" and "the Alvia didn't derail" as contradictions with the record. Proposes dispatch to the Alvia ~30 minutes before reality. |

Every recommendation waits for **Approve / Reject (with reason) / Defer**. Rejections are respected until the evidence changes. Every step lands in an audit log. **Reality check** compares Copi's timings with what really happened, with the honest caveats.

Toggle **Proposed integrations** off to see what today's control-room data alone allows: Act 1 goes silent, Act 3 still works.

## Run

```bash
cd copi-neat
./run.sh                      # creates .venv on first run, serves http://localhost:8000
```

Keys: `space` play/pause · `n` next event. Default pauses at each act and at each new critical recommendation (toggle in the top bar).

### Claude modes

| Mode | When | Behaviour |
|---|---|---|
| **live** | `ANTHROPIC_API_KEY` in `copi-neat/.env` (see `.env.example`) | Claude (`claude-opus-5-5`, effort `low`) writes the briefing, driver line, Q&A and shift handover. Every output is recorded to `demo_cache/`. |
| **recorded** | no key, `demo_cache/adamuz-2026.json` exists | Replays recorded Claude outputs: safe for a demo on bad wifi. |
| **offline** | neither | Rule engine only. Everything except the Claude briefing, Q&A and handover still works. |

**Before the demo:** do one full live run with a key so `demo_cache/` holds real Claude outputs, then commit it. A live run makes roughly 20–30 Claude calls.

Server-side refusal fallback is on (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). Remove it in `app/copilot.py` if you don't want it.

## Drill: two seats, two laptops

One drill, kept simple: **the LZB failure at Urda**. One person is the **pilot** and sees only the track. The other is
the **control tower**. They talk to each other by voice and nothing else.

```bash
cd copi-neat
./drill.sh --tunnel     # tower: http://localhost:8000/drill/control · the pilot's link is at the bottom of that page
./drill.sh --tunnel --reload   # while the code is changing: the server reloads itself, link and key stay
```

1. The tower presses **Start**. Train A (the pilot) and Train B run at 200 km/h.
2. Four seconds later **LZB fails**. A red bar appears on both screens. The tower's panel keeps only where each train
   was last seen; it never showed speed.
3. The tower tells the trains to **stop**. The pilot brakes (Space, or ↓).
4. With every train at a stand, the tower says **continue at 40**. The pilot drives on sight.
5. The drill ends when Train A has run 400 m on sight at 40 km/h or less, or stopped short of Train B.

The three protocol steps on the tower's screen tick themselves. Hold **T** to talk (LiveKit radio; needs
`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in `copi-neat/.env`, and `uv`). The pilot's link carries a join
key; without it the server answers 403.

**Copi** is the assistant (Claude Sonnet, `claude-sonnet-5-5`, for everything). It listens and **writes** to the tower;
it does not talk. It writes only when something is going wrong, and otherwise the panel says "Nothing to flag":

| Copi writes | When |
|---|---|
| Train A is still moving: 200 km/h. | 10 s after the failure the pilot's train is not braking |
| Train A cleared for 200 km/h. First step: stop all trains. | the tower let a train go on before it had stopped |
| Train A cleared for 160 km/h. LZB is down: on sight, 40 at most. | after the stop, the tower allowed more than 40 (any wording, any language: Sonnet reads it) |
| Train A at 66 km/h. On sight is 40. | too fast after the stop |
| Train B is stopped 460 m ahead of Train A. | Train A is running out of room to stop |

Copi does not explain the situation and ignores every other conversation. **R** means heard: the flag turns grey and
Copi does not bring it up again. Speeds and distances in the flags come from the trains' own units, which a control
room does not get today (`COPI_ONBOARD=0`: Copi goes by the radio alone). `COPI_SPEAK=1` gives Copi its voice back.

What it is built on: preliminary press reports of the Urda collision (28 Oct 2026), see `docs/urda.md`. No report
says the control centre saw train speed; whether it could follow positions after the failure is disputed. The drill
takes both away. It is a simplification, not a replay, and the steps are not the Adif rule book.

Files: `app/protocols.py` (the case and its three steps), `app/drill.py` (engine), `app/drill_copilot.py` (Copi's
Claude calls), `app/drill_api.py`, `static/drill/`, `tests/test_drill.py`.

**Earlier version.** Four more cases (rockfall, rough ride, dark signal, emergency brake) with protocol buttons, a
radio log and a talking assistant are still in the engine and the tests. Their pages are at `/drill/classic`.

## Architecture

```
scenarios/adamuz.json   events tagged real / simulated / counterfactual, and
                        ctc (today) / proposed (integration) / hindsight (never fed)
app/rules.py            deterministic layer: ms, no network, unit-tested. Location correlation,
                        incident fusion, call tracking, contradiction checks
app/memory.py           working memory: facts, hypotheses, open loops, contradictions,
                        recommendations, decisions, audit log
app/copilot.py          Claude layer: structured briefing via messages.parse + Pydantic.
                        Sees only fed events, never hindsight notes
app/main.py             FastAPI, replay clock, SSE stream, decision endpoints
static/                 operator console (vanilla JS, no build step)
tests/test_rules.py     what Copi knew, and when
```

Design rules:

1. **Seconds belong to automatic protection.** No LLM in any path that has to act in under a few seconds. Rules handle fusion instantly; Claude's briefing arrives a few seconds later and says how old it is.
2. **Advisory only.** Neither layer can touch the railway. Recommendations are a queue; a human approves, rejects with a reason, or defers.
3. **Evidence or nothing.** Every item cites event ids. Claude recommendations citing ids that don't exist are dropped and the drop is logged.
4. **Respect the "no".** A rejected recommendation comes back only when urgency rises on new evidence.
5. **Interrupt sparingly.** At most three full cards; the rest collapse. The driver tablet shows one line or nothing.
6. **Honest provenance.** Badges show which data is real, simulated or counterfactual, and which a control room actually receives today.

```bash
.venv/bin/python -m pytest -q    # the replay rules and the drill
```

## Limits

- The scenario is a reconstruction from press reports and Wikipedia timelines; train-describer data and some sensor events are simulated or counterfactual (marked in the UI). CIAF's final report is not out.
- Timing gains in the reality check are an argument for the design, not a finding. 45 of 46 victims died on impact; the lives are in Act 1, which depends on integrations that don't exist yet.
- A real deployment would need safety assessment (CENELEC EN 50126/50128/50129 style), operator training, and evaluation with real controllers. This is a hackathon prototype.
