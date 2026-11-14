# LZB Protocol-Adherence Model: Results

14 Nov 2026

## Summary

A Qwen3.5-4B model fine-tuned on Adaption reaches 86% verdict accuracy on 200 held-out synthetic logs, against 60% for the untuned model given the same rules in its prompt. It names exactly the right rule in 86% of answers, against 11% for the untuned model. The test data is synthetic and templated, so this shows the model learned the task, not that it works on real control-room audio. On the one realistic case, the Urda reconstruction, the fine-tuned model gets the verdict right but names the wrong rule.

Task: read a timestamped control log from an LZB transmission failure (V Meta = 000) and answer `VERDICT / RULES / STEP / REASON`. The protocol is RCF annex 5ET3 (arts. 5ET3.4.3.4 and .5), split into six rules, R1 to R6. Training used 1,200 synthetic rows (Adaption AutoScientist, SFT with LoRA, 2 iterations, about 43 minutes).

## Results

Both models ran on the same 200 held-out synthetic rows, written with phrasing the training set never used. The untuned model got the protocol rules in its prompt; the fine-tuned model did not need them.

| Metric | Untuned + rules in prompt | Fine-tuned |
| --- | --- | --- |
| Verdict accuracy | 60% (120/200) | 86% (172/200) |
| Verdict and rules exactly right | 11% | 86% |
| Violation recall | 100% (103/103) | 95% (98/103) |
| Precision | 56% | 81% |
| False alarms on 97 compliant logs | 80 | 23 |
| Spanish / English verdict accuracy | 65% / 54% | 78% / 95% |
| R2 recall (driver reports location) | 0/12 | 7/12 |
| Urda demo case | VIOLATION, R3 + R6 | VIOLATION, R2 (wrong rule) |

- **Fine-tuning helps on this test.** The 26-point accuracy gap is much larger than the roughly 5-point noise at n=200.
- **The untuned model is close to "always say VIOLATION".** Its 100% recall comes from flagging 80 of 97 compliant logs; its 56% precision is barely above the 51.5% of an always-violation answer.
- **The fine-tuned model is strong on rules where a wrong action appears in the log.** Recall was perfect on R1, R3, R4, R5 and R6 (14/14, 32/32, 19/19, 17/17, 9/9).
- **R2 is the hardest rule.** It depends on something missing: all five of the fine-tuned model's missed violations were R2 rows called compliant.

## Weaknesses

- **Synthetic, templated data.** Train and test come from the same generator, differing only in phrasing. The 86% is optimistic and says little about real radio or phone transcripts.
- **The Urda case fails on the rule.** The fine-tuned model says VIOLATION but blames R2 instead of R3, with a garbled reason. The untuned model got R3 here. It is one example, but it is the case the demo rests on.
- **Over-flagging.** 23 false alarms on 97 compliant logs (precision 81%). For an operator-facing check, alert fatigue matters as much as recall.
- **Spanish is weaker** (78% against 95% for English), and real logs would be in Spanish.
- **One rule per row.** Training allows a single violated rule, so the model cannot report two (the Urda log arguably breaks R2 and R3 and R6).
- **Weak baseline only.** The comparison model is the untuned 4B with one prompt. A frontier model given the same rules has not been run and may score high on templated data.
- **Protocol gaps.** The 40 km/h cap in the drill's protocol is not in the RCF text, which says only "Marcha a la Vista". Adif's internal controller checklists and the itemized checks before 5ET3.2 are not public. R1 to R6 are our reconstruction.
- **Cause not established.** The Urda investigation is preliminary, so "controller error" is an apparent deviation per press reports, not a finding. We do not claim the model would have prevented the accident.
- **No hosted inference.** Adaption does not serve the tuned model; running it needs a GPU (Colab T4 so far), and a 200-row evaluation takes about 10 minutes.

## Next steps

1. **Frontier-model baseline.** Run Claude with the same rules prompt on the same 200 rows. It tells us whether fine-tuning is the story, or whether the story is a small, cheap model that needs no protocol text in its prompt.
2. **Read the errors.** Score the saved per-row files (`finetune/score_file.py`) to see which compliant logs cause the 23 false alarms and whether they cluster in Spanish or in Meta-40 cases.
3. **Data v2, then retrain.** More Spanish rows; "missing action" cases for R2; varied compliant logs; multiple rules per row; Urda-style phrasing, with the exact Urda log held out so any Urda result stays honest. LLM-rewritten logs would make the test more realistic.
4. **Fix the Urda label.** Accept R2 and R3 (and R6) for the Urda log, or reword it so only R3 applies.
5. **Align the protocol with the drill.** Agree one definition with the team: the drill's "40 km/h on sight" versus the RCF's "Marcha a la Vista".
6. **Longer term.** A state-machine simulator as the label source, a verifier tool the model calls, and an operator panel showing the evidence and a confidence score. The operator decides; the model is a second pair of eyes.
