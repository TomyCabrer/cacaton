# finetune: protocol-adherence model (Adaption)

A small model fine-tuned on **Adaption AutoScientist** that reads a railway control log and says whether the
protocol was followed, and if not, which rule was broken.

- **Case:** Urda (28 Oct 2026), LZB failure. Preliminary press reports only; the cause is not established.
- **Protocol:** RCF (RD 664/2015) annex 5ET3, arts. 5ET3.4.3.4 and 5ET3.4.3.5 (LZB failure, V Meta = 000). Verified against the
  consolidated BOE text (last consolidated 12/07/2023). Rules R1 to R6 are in [`PROTOCOL.md`](PROTOCOL.md).
- **Base model:** `Qwen/Qwen3.5-4B`, SFT with LoRA, 2 AutoScientist iterations (about 43 min).
- **Input / output:** a timestamped log in, four lines out: `VERDICT / RULES / STEP / REASON`.

## Result (honest version)

Held-out test: `data/test.jsonl`, 200 **synthetic** rows with phrasing the training set never used.

| Metric | Score |
|---|---|
| Verdict accuracy | **86%** (172/200, roughly 81 to 90%) |
| Violation recall | 95% (98/103) |
| Precision | 81% (23 false alarms on 97 compliant logs) |
| Format valid | 100% |
| Spanish / English verdict accuracy | 78% / 95% |

Per-rule recall: R1 14/14, R3 32/32, R4 19/19, R5 17/17, R6 9/9, **R2 7/12**.
All five misses are R2 rows ("driver never reports location") that the model called compliant.

**Urda demo case (`data/urda_demo.json`): verdict right, rule wrong.** The model says VIOLATION but blames R2 instead of R3
("marcha normal"). The Urda log is outside the training templates and has no location report, so R2 is arguably also true
there. The training data allows one rule per row, so the model picks one.

### What this does and does not show

- It learned the task and format, and detects violations in logs phrased differently from training.
- The data is **synthetic and templated**. The score is optimistic and says little about real transcripts.
- **No baseline yet.** We have not shown fine-tuning beats a prompted model. `eval.py --no-adapter --with-rules` does that.
- Adaption's own `best_win_rate` (0.42) is a pairwise-preference score on their evals, **not** accuracy. Ignore it.
- Do not claim it would have prevented Urda.

## Known mismatch with the drill

`copi-neat/app/protocols.py` (P-05) says "continue on sight, 40 km/h at most". The RCF text says only "Marcha a la Vista"
with no km/h figure; 40 comes from press and Renfe's proposed rule (not approved, per one outlet). R1 to R6 do not check 40.

## Files

| File | What |
|---|---|
| `PROTOCOL.md` | Rules R1 to R6 with BOE sources |
| `gen_data.py` | Synthetic generator (templated, one violation per row). Writes `data/train.jsonl`, `data/test.jsonl`, `data/urda_demo.json` |
| `upload.py` | Writes `data/adaption_train.jsonl` (prompt + completion) and uploads it to Adaption (raw mode) |
| `run.py` | Launches the AutoScientist run (Qwen3.5-4B, SFT, 2 iterations) |
| `wait_run.py` | Polls the run |
| `list_models.py` | Lists Adaption base models |
| `eval.py` | Scores the adapter; `--no-adapter [--with-rules]` for baselines; `--dry-run` self-tests the scorer |
| `data/dataset_id.txt`, `data/run_id.txt` | Adaption dataset and run IDs (tied to one account) |

## Reproduce

```bash
cd finetune
python3 -m venv .venv && .venv/bin/pip install "adaption>=0.7.0" zstandard
cp .env.example .env   # then set ADAPTION_API_KEY (never commit it)
.venv/bin/python gen_data.py
.venv/bin/python upload.py      # prints dataset_id, saves data/dataset_id.txt
.venv/bin/python run.py         # prints run_id, saves data/run_id.txt
.venv/bin/python wait_run.py    # waits; then download the checkpoint (see below)
```

Download the adapter (a zstd tar, so extract with Python, not `tar`):

```python
with client.autoscientist.with_streaming_response.download(run_id) as r:
    r.stream_to_file("checkpoint/best-checkpoint.tgz")
# then: zstandard + tarfile to extract into checkpoint/extracted
```

The adapter (170 MB, `adapter_model.safetensors`) is **not in git** (gitignored). Ask Sobri for it, or re-download from the run.

## Evaluating (needs a GPU; Colab T4 works)

Adaption does not host tuned checkpoints, and a 4B model does not fit on a 2 GB laptop GPU. On Colab:

```
!pip install -q transformers peft accelerate
%cd /content/work          # folder containing eval.py, data/test.jsonl, data/urda_demo.json, checkpoint/extracted
!python -u eval.py --out results.jsonl
```

Baselines on the same rows (the untuned model is only fair **with the rules in the prompt**):

```
!python -u eval.py --no-adapter --with-rules --out results_base_rules.jsonl
```

Gotchas found the hard way:

- The adapter's tensor names use the multimodal prefix `model.language_model.layers…`. A text-only base model names them
  `model.layers…`, and `peft` then silently loads **nothing** (it only warns "missing adapter keys"). `eval.py` renames the keys
  to match and aborts if all LoRA weights are zero (`adapter check: N/N lora_B tensors nonzero`).
- A Colab T4 has no native bfloat16; `eval.py` uses float16 there (`--dtype` overrides). Qwen3.5 may need `--dtype bfloat16`
  if fp16 gives garbage.
- Do not re-extract an old bundle over a newer `eval.py`.

## Next steps

1. Run the baselines and read the errors (23 false alarms, R2 misses, Spanish).
2. Data v2: more realistic and varied logs (more Spanish, "missing action" cases for R2, multiple violations per row),
   keeping the exact Urda log held out.
3. Longer term: a state-machine simulator as the label source, a verifier tool the model calls, and an operator-facing
   panel that shows the evidence and a confidence score. The model's role is a second pair of eyes; the operator decides.
