"""Score a results jsonl from eval.py (lines of {"gold","pred"}) against data/test.jsonl. No GPU needed.
Usage: python score_file.py results_tuned.jsonl [results_base_rules.jsonl ...]"""
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("ev", "eval.py"); ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
rows = [json.loads(l) for l in open("data/test.jsonl")]
for path in sys.argv[1:]:
    res = [json.loads(l) for l in open(path) if l.strip()]
    print(f"\n=== {path} ({len(res)} rows)")
    if len(res) != len(rows) or any(r["gold"] != x["completion"] for r, x in zip(res, rows)):
        print("WARNING: gold answers do not match data/test.jsonl in order; scoring against the file's own gold")
        rows_used = [{"completion": r["gold"]} for r in res]
    else:
        rows_used = rows
    ev.score(rows_used, [r["pred"] for r in res])
