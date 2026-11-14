# Copi

**A second pair of eyes for rail control rooms. Copi listens to the controller and the driver, checks what is said against the protocol that applies, and flags the controller when the two diverge. The human decides.**

Built at the Imperial AI Hackathon 2026 (14–15 November, Imperial College London).

## Why

On 28 October 2026 the LZB cab signalling dropped over about 63 km of the Madrid–Sevilla high-speed line. An Iryo stopped near Urda (Toledo) and could not restart. According to preliminary press reports, the control centre then released the AVE following it on the same track to normal running, when the rule after an LZB loss is to continue on sight. About 17 minutes later the AVE hit the stationary train. Reports give 68 to 69 dead.

Press reports describe no mechanism in the control room that checks a spoken order against the rule. Copi is a prototype of that check. It runs in the control centre only, needs nothing installed on the train, and cannot touch the railway: it writes a flag, and the controller acts on it or dismisses it.

The investigation is not finished and the cause is not established. Everything here is built from press reports. The timeline and sources are in [`copi-neat/docs/urda.md`](copi-neat/docs/urda.md).

## What is in the repo

| Folder | What it is | Start with |
|---|---|---|
| [`copi-neat/`](copi-neat/) | The prototype. A two-laptop drill of the Urda LZB failure (pilot, control tower, Copi), and a replay console for the Adamuz collision of 18 January 2026. FastAPI, plain JavaScript, Claude. | [`copi-neat/README.md`](copi-neat/README.md) |
| [`finetune/`](finetune/) | A small model (Qwen3.5-4B, fine-tuned on Adaption) that reads a control log and says whether the LZB-failure protocol was followed, and which rule was broken. | [`finetune/REPORT.md`](finetune/REPORT.md) |
| [`business/`](business/) | Need, market, financials, feasibility, regulation and legal. In Spanish. | [`business/README.md`](business/README.md) |

## Run the demo

Needs Python 3.10 or later. Nothing else is required for a first look.

```bash
git clone https://github.com/TomyCabrer/cacaton.git
cd cacaton/copi-neat
./run.sh                 # first run creates .venv, then serves http://localhost:8000
```

| Page | Address |
|---|---|
| Adamuz replay console | http://localhost:8000 |
| Drill, control tower | http://localhost:8000/drill/control |
| Drill, pilot | the link shown on the tower's page |

For the drill on two laptops, start it with `drill.sh` instead:

```bash
./drill.sh --tunnel      # tower on this laptop, plus an https link for the pilot's laptop
```

What each extra gives you:

| To get | You need |
|---|---|
| Live Claude (briefings, questions, reading the tower's orders) | `ANTHROPIC_API_KEY` in `copi-neat/.env` (copy `.env.example`) |
| Voice radio between pilot and tower | `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` in `copi-neat/.env`, and [`uv`](https://docs.astral.sh/uv/) |
| A pilot on a different network | `cloudflared` (`brew install cloudflared`) and the `--tunnel` flag |

Without an Anthropic key, Copi replays the Claude outputs recorded in `copi-neat/demo_cache/`, and falls back to the rule engine where nothing is recorded. That makes the demo safe on bad wifi.

Tests:

```bash
.venv/bin/python -m pytest -q    # the replay rules and the drill
```

## The drill

One person is the pilot and sees only the track. The other is the control tower and sees the line, not the track. They talk by voice.

1. Two trains run at 200 km/h. Four seconds after the start, LZB fails.
2. The tower tells the trains to stop.
3. With every train at a stand, the tower clears them to continue on sight at 40 km/h.

Copi listens and writes to the tower. It stays silent unless something is going wrong:

| Copi writes | When |
|---|---|
| Train A is still moving: 200 km/h. | 10 s after the failure the train is not braking |
| Train A cleared for 200 km/h. First step: stop all trains. | the tower let a train go on before it had stopped |
| Train A cleared for 160 km/h. LZB is down: on sight, 40 at most. | after the stop, the tower allowed more than 40, in any wording or language |
| Train A at 66 km/h. On sight is 40. | too fast after the stop |
| Train B is stopped 460 m ahead of Train A. | Train A is running out of room to stop |

The drill is a simplification, not a replay of the accident. Full rules, keys and options are in [`copi-neat/README.md`](copi-neat/README.md).

## How Copi is designed

- **Advisory only.** Copi cannot act on the railway. It proposes, and a person approves, rejects or defers.
- **No language model where seconds count.** Deterministic rules do the fast work with no network. Claude's output arrives a few seconds later and says how old it is.
- **Evidence or nothing.** Every flag cites the events behind it. A recommendation that cites an event that does not exist is dropped, and the drop is logged.
- **Quiet by default.** One line when something is wrong, "Nothing to flag" otherwise.
- **A "no" is respected.** A rejected recommendation comes back only if new evidence raises the urgency.
- **Honest about its data.** The interface marks which data is real, simulated or counterfactual, and which a control room receives today.

## The fine-tuned model

The task: read a timestamped control log from an LZB failure and answer with a verdict, the rule broken, the step and a reason. The protocol is six rules (R1 to R6) taken from the Spanish rail traffic regulation, RCF annex 5ET3; see [`finetune/PROTOCOL.md`](finetune/PROTOCOL.md).

Results on 200 held-out synthetic logs:

| Metric | Untuned Qwen3.5-4B, rules in prompt | Fine-tuned |
|---|---|---|
| Verdict accuracy | 60% | **86%** |
| Verdict and rule both right | 11% | **86%** |
| False alarms on 97 compliant logs | 80 | **23** |
| Violation recall | 100% | 95% |

Read these with three caveats:

- The data is synthetic and templated, so 86% is optimistic and says little about real radio transcripts.
- On the one realistic case, the Urda reconstruction, the fine-tuned model gets the verdict right and names the wrong rule.
- The baseline is the untuned 4B model. A frontier model given the same rules has not been run.

The drill does not use this model yet. Copi in the drill runs on Claude.

Full results are in [`finetune/REPORT.md`](finetune/REPORT.md), what we learned about the platform in [`finetune/ADAPTION.md`](finetune/ADAPTION.md), and the steps to reproduce in [`finetune/README.md`](finetune/README.md).

## The business case

- **Customer:** ADIF. An annual licence of 40,000 € per control position, starting with a paid pilot in one centre.
- **Market:** about 10 M€ a year in Spain (roughly 240 positions in 19 control centres) and about 125 M€ in Europe. Air traffic control comes after.
- **Why now:** the Spanish government's safety plan of 3 November 2026 includes "an AI agent" to watch conversations between driver and controller, so far with no supplier, cost or date.
- **Main risk:** access to ADIF's data, certification, and acceptance by controllers. The technology is the smaller problem.

The prices, rollout and costs are the team's assumptions, not published figures, and no lawyer has reviewed the legal part. The detail is in [`business/`](business/).

## Limits

- The scenarios are reconstructions from press reports. Neither investigation has published a final report.
- The 40 km/h cap in the drill comes from press reports. The regulation says only "Marcha a la Vista" and gives no figure.
- The model evaluation uses synthetic data.
- This is a hackathon prototype. A real deployment would need a safety assessment (CENELEC EN 50126, 50128 and 50129), operator training, and evaluation with real controllers.
- We do not claim Copi would have prevented Urda.

## Team

| Name | Worked on | GitHub |
|---|---|---|
| Tomy | Platform: drill and replay console | @TomyCabrer |
| Michel | Platform | |
| Sobri | Fine-tuned model and its evaluation | @j-sobrino |
| Jaime | Business, market, regulation and legal | @jaimeramaa |
| Juan | Design and specification | @juaninjr |

## Working in this repo

- `main` always runs. Work on a short branch (`feat/<thing>`), open a pull request, merge fast.
- Never commit API keys. They go in `.env`, which is git-ignored.
- Whatever we show on Sunday must run from a clean clone with the steps above.

## Hackathon links

- Website (schedule, tracks, submission): https://imperialaihack.com/login
- Discord: https://discord.gg/28XrgECKY
- Event page: https://luma.com/c6zebxau
- Adaption: https://adaptionlabs.ai
- Figma for Education: https://www.figma.com/education
