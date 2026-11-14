"""Prepare clean prompt/completion file and upload to Adaption (raw mode). Does NOT launch training."""
import json, os, time
for l in open(".env"):
    k, _, v = l.strip().partition("=")
    if k: os.environ[k] = v
from adaption import Adaption

with open("data/adaption_train.jsonl", "w") as out:
    for l in open("data/train.jsonl"):
        r = json.loads(l)
        out.write(json.dumps({"prompt": r["prompt"], "completion": r["completion"]}, ensure_ascii=False) + "\n")

c = Adaption()
ds = c.datasets.upload_file("data/adaption_train.jsonl", name="lzb-protocol-train",
                            processing_mode="raw", column_mapping={"prompt": "prompt", "completion": "completion"})
did = ds.dataset_id
print("dataset_id:", did)
while True:
    s = c.datasets.get_status(did)
    if s.status == "failed":
        raise SystemExit(f"ingestion failed: {s.error_data}")
    if s.row_count is not None:
        print("rows:", s.row_count, "status:", s.status); break
    time.sleep(5)
open("data/dataset_id.txt", "w").write(did)
