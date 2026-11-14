"""Launch AutoScientist SFT run on uploaded dataset."""
import os
for l in open(".env"):
    k, _, v = l.strip().partition("=")
    if k: os.environ[k] = v
from adaption import Adaption
c = Adaption()
did = open("data/dataset_id.txt").read().strip()
run = c.autoscientist.create(dataset_id=did, model="Qwen/Qwen3.5-4B", training_method="instruction",
                             data_format="instruction", max_iterations=2)
print("run_id:", run.id, "status:", run.status, "model:", getattr(run, "model", None))
open("data/run_id.txt", "w").write(run.id)
