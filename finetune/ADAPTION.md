# How We Used Adaption

14 Nov 2026

## Summary

We used Adaption AutoScientist to fine-tune Qwen3.5-4B into a protocol-adherence checker for railway control logs, end to end through the Python SDK: upload a 1,200-row dataset, launch one AutoScientist run, poll it, and download the LoRA checkpoint. The run finished in about 43 minutes and the checkpoint reaches 86% verdict accuracy on 200 held-out synthetic logs, against 60% for the untuned model given the same rules in its prompt.

Adaption handled training and the search over settings well. The friction was around the edges: no hosting for the tuned model, a checkpoint whose tensor names did not match a text-only base model, and a win-rate metric that does not measure label accuracy. Details and suggestions below.

## What we did

All calls used the `adaption` Python SDK (version 0.19.0 installed; the docs require 0.7.0 or later), with the API key in `ADAPTION_API_KEY`.

1. **List models.** `autoscientist.list_models()` returned 16 base models; we picked `Qwen/Qwen3.5-4B` (SFT or DPO, LoRA or full).
2. **Build the dataset locally.** A generator wrote 1,200 synthetic training logs with `prompt` and `completion` columns (the completion is `VERDICT / RULES / STEP / REASON`).
3. **Upload.** `datasets.upload_file(..., processing_mode="raw", column_mapping={"prompt": "prompt", "completion": "completion"})`, then `datasets.get_status()` polled every 5 seconds until the row count (1,200) appeared. Raw mode skipped Adaptive Data processing.
4. **Launch.** `autoscientist.create(dataset_id, model="Qwen/Qwen3.5-4B", training_method="instruction", data_format="instruction", max_iterations=2)`. No augmentation: 1,200 rows clears the 1,000-row SFT minimum.
5. **Poll.** `autoscientist.get(run_id)` once a minute until `succeeded`.
6. **Download.** `autoscientist.with_streaming_response.download(run_id)` streamed a 160 MB archive of the best iteration's checkpoint.
7. **Evaluate on our own GPU.** Adaption does not host tuned checkpoints, so we loaded the adapter on a Colab T4 and scored 200 held-out rows ourselves.

## Run details

| Item | Value |
| --- | --- |
| Base model | `Qwen/Qwen3.5-4B` |
| Method | SFT (`training_method="instruction"`), LoRA |
| Dataset | 1,200 rows, raw processing, no augmentation |
| Iterations | 2 of a maximum 2 (default target win rate 0.70, not reached) |
| Duration | about 43 minutes (created 18:10:45, completed 18:53:16 UTC, 14 Nov 2026) |
| Adaption win rate | 0.35 after iteration 1, 0.42 final |
| Iteration 1 settings | LoRA r=16, alpha 32, 1 epoch, learning rate 5e-5 |
| Final checkpoint | LoRA r=32, alpha 64, 4 epochs (84 steps); training loss about 1.7 to 0.0002 |
| Checkpoint size | 170 MB adapter (160 MB compressed archive) |
| Our own accuracy | 86% on 200 held-out rows (untuned baseline 60%) |

The win rate is Adaption's pairwise-preference score on its own evals. It is not our accuracy, and we did not use it to judge the model.

## What worked well

- **A short path from CSV or JSONL to a trained model.** Upload, one `create` call, poll, download: a few short scripts, with no training code and no GPU of our own for the 43-minute run.
- **The settings search.** We passed only the model and an iteration cap; AutoScientist chose LoRA rank, epochs and learning rate, and its second iteration used different settings from the first.
- **Clear data rules.** The minimum row counts (1,000 for SFT) are documented per method, so we knew 1,200 rows was enough and that augmentation was optional.
- **The result is real.** A 4B model fine-tuned on 1,200 synthetic rows beat the untuned model by 26 points of verdict accuracy and by 75 points of exact rule match on our held-out set.
- **Open weights.** The download is a standard LoRA adapter, so we could evaluate it ourselves with `transformers` and `peft` and keep it.

## Friction we hit

- **No hosting for the tuned model.** The Responses API serves 7 hosted models (for example `qwen3.5-397b`); we found no way to call our checkpoint there. Evaluation needed our own GPU, and a 4B model does not fit on a 2 GB laptop GPU, so we used a free Colab T4.
- **Adapter tensor names did not match a text-only base model.** The adapter's keys are named `model.language_model.layers.N...`, but the base model in the adapter config (`togethercomputer/Qwen3.5-4B`) loaded as text-only with `model.layers.N...`. `peft` then loaded none of the 256 tensors and only printed a warning, so our first evaluations silently ran the untuned model. We fixed it by renaming the keys and by adding a check that the LoRA weights are nonzero.
- **The win rate does not measure accuracy.** It is a pairwise-preference score on Adaption's own evals (0.35, then 0.42 against a 0.70 target). Our task has exact labels, so we scored it ourselves. The docs do not say what it compares against, and nothing in them mentions classification.
- **Column mapping.** We set `column_mapping` at upload, but the dataset reported `configured_column_mapping=None`. Passing the same mapping to `autoscientist.create` failed with a 400 ("columns not in this dataset"); omitting it worked, so we are not certain which columns were used, though they were literally named `prompt` and `completion`.
- **The checkpoint archive is zstd-compressed.** The docs show `tar xf`, which failed on our machine without `zstd`; we extracted it with Python's `zstandard` package.
- **Cost and time were not visible.** We found no price or credit figure for the run, and the docs give no time per iteration. The 30-day free trial that began at launch (13 May) has probably ended; we did not check billing.
- **The run object shows little progress.** Beyond `iterations_completed` and `best_win_rate`, we saw no loss curves or logs until the checkpoint was downloaded.

## What we did not use yet

- **Adaptive Data.** We used raw mode, so no adapt, expand, translate or quality-evaluation steps. Adapting or expanding the dataset may help with our Spanish weakness and with variety.
- **Augmentation.** Optional, adds general-purpose rows to reduce forgetting; skipped because 1,200 rows cleared the minimum.
- **Custom Evals.** The API lists a custom-rubric eval; we did not try it, and did not confirm it can score label accuracy on a held-out set.
- **DPO.** It needs 12,000 preference pairs, far more than we have.
- **Larger models.** We trained one 4B model; the 9B and larger models were not compared.
- **Hugging Face export and the Responses API.** We downloaded the checkpoint by hand and did not use the hosted models.

## Suggestions for Adaption

1. **Host tuned checkpoints** behind the Responses API, or document a one-call way to serve them. This is the biggest gap for a hackathon team without a GPU.
2. **Fix or document the checkpoint tensor names**, or ship an adapter that loads on the base model it names. A load that silently skips every LoRA weight is easy to miss.
3. **Support label-accuracy evaluation.** A held-out eval that reports accuracy or F1 for structured outputs, next to the win rate, and a plain explanation of what the win rate compares against.
4. **Document classification and structured-output tasks.** Our task is prompt to a fixed-format label, and the docs only describe generative SFT.
5. **Clarify column mapping** for raw uploads: when it is applied, and why `create` rejects a mapping that matches the dataset.
6. **Show cost and progress.** A cost estimate for AutoScientist runs (the Adaptive Data `adapt` call already has one), time per iteration, and loss curves in the run object.
7. **Use a more common archive format**, or say in the docs that it needs `zstd`.
