"""Poll AutoScientist run until it finishes; print status changes."""
import os, time
for l in open(".env"):
    k, _, v = l.strip().partition("=")
    if k: os.environ[k] = v
from adaption import Adaption
c = Adaption()
rid = open("data/run_id.txt").read().strip()
last = None
while True:
    r = c.autoscientist.get(rid)
    cur = (r.status, getattr(r, "best_win_rate", None))
    if cur != last:
        print(time.strftime("%H:%M:%S"), r.status, "best_win_rate:", cur[1], flush=True); last = cur
    if r.status in ("succeeded", "failed", "cancelled"):
        print("download_available:", getattr(r, "download_available", None), "error:", getattr(r, "error", None)); break
    time.sleep(60)
