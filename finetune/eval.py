"""Eval the Adaption LoRA adapter. Needs a GPU (run on Colab). Usage:
  python eval.py --adapter checkpoint/extracted --data data/test.jsonl --out results.jsonl
  python eval.py --dry-run   # scorer self-test using gold completions, no model
"""
import argparse, json, re, collections

def parse(text):
    v = re.search(r"VERDICT:\s*(VIOLATION|COMPLIANT)", text, re.I)
    r = re.search(r"RULES:\s*([^\n]*)", text, re.I)
    rules = sorted(set(re.findall(r"R\d", r.group(1)))) if r else []
    return (v.group(1).upper() if v else None), rules

def score(rows, preds):
    n = len(rows); fmt = ok_v = ok_r = tp = fn = fp = tn = 0
    per_rule = collections.defaultdict(lambda: [0, 0])  # [correct, total]
    by_lang = collections.defaultdict(lambda: [0, 0])
    for row, p in zip(rows, preds):
        gv, gr = parse(row["completion"]); pv, pr = parse(p)
        fmt += pv is not None
        ok_v += pv == gv; ok_r += (pv == gv and pr == gr)
        by_lang[row.get("lang", "?")][1] += 1; by_lang[row.get("lang", "?")][0] += pv == gv
        if gv == "VIOLATION":
            tp += pv == "VIOLATION"; fn += pv != "VIOLATION"
            for r in gr: per_rule[r][1] += 1; per_rule[r][0] += (pv == gv and r in pr)
        else:
            fp += pv == "VIOLATION"; tn += pv != "VIOLATION"
    print(f"n={n}  format_ok={fmt/n:.3f}  verdict_acc={ok_v/n:.3f}  verdict+rules_exact={ok_r/n:.3f}")
    print(f"violation recall={tp/max(tp+fn,1):.3f}  precision={tp/max(tp+fp,1):.3f}  false_alarms={fp}  misses={fn}")
    print("per-rule recall:", {k: f"{a}/{b}" for k, (a, b) in sorted(per_rule.items())})
    print("verdict acc by lang:", {k: f"{a}/{b}" for k, (a, b) in by_lang.items()})

RULES = """You are checking a railway control log against this protocol (LZB transmission failure, V Meta = 000, block ahead occupied).
R1 Driver: on Meta 000 press LIBERAR within 8 s, brake and stop.
R2 Driver: once stopped, report location to the RC (controller).
R3 RC: after checks, authorize with telefonema 5ET3.2 "Marcha a la Vista". Authorizing "marcha normal" is a violation.
R4 5ET3.2 does not authorize passing signals; passing a signal needs a separate authorization.
R5 Driver: resume only after RC authorization.
R6 Driver: disconnect/reconnect LZB only with RC authorization (5ET3.3).
If Meta is 40 (block free), no stop is needed and the log is compliant.
Answer exactly in this format:
VERDICT: VIOLATION or COMPLIANT
RULES: comma-separated rule ids, or none
STEP: short step name or none
REASON: one sentence

"""

def remap_keys(keys, model_has_language_model):
    """Adapter files from Adaption name tensors '...model.language_model.layers.N...'. A text-only base model
    names its layers 'model.layers.N'. Rename adapter keys to whatever the loaded model uses."""
    adapter_has = any("model.language_model.layers" in k for k in keys)
    if adapter_has == model_has_language_model:
        return {k: k for k in keys}
    if adapter_has:  # adapter multimodal-style, model text-only
        return {k: k.replace("model.language_model.layers", "model.layers") for k in keys}
    return {k: k.replace("model.layers", "model.language_model.layers") for k in keys}

def prepare_adapter(model, adapter_dir):
    import os, shutil, tempfile
    from safetensors.torch import load_file, save_file
    has_lm = any("language_model.layers" in n for n, _ in model.named_parameters())
    sd = load_file(os.path.join(adapter_dir, "adapter_model.safetensors"))
    m = remap_keys(list(sd), has_lm)
    if all(k == v for k, v in m.items()):
        print("adapter keys already match the model", flush=True); return adapter_dir
    tmp = tempfile.mkdtemp(); shutil.copytree(adapter_dir, tmp, dirs_exist_ok=True)
    save_file({m[k]: v.contiguous() for k, v in sd.items()}, os.path.join(tmp, "adapter_model.safetensors"), metadata={"format": "pt"})
    print(f"remapped {sum(k != v for k, v in m.items())} adapter keys to match the loaded model", flush=True)
    return tmp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="checkpoint/extracted"); ap.add_argument("--data", default="data/test.jsonl")
    ap.add_argument("--base", default=None); ap.add_argument("--out", default="results.jsonl")
    ap.add_argument("--urda", default="data/urda_demo.json"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-adapter", action="store_true", help="evaluate the untuned base model (baseline)")
    ap.add_argument("--with-rules", action="store_true", help="prepend the protocol rules to every prompt (fair baseline for the untuned model)")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--dtype", default="auto", choices=["auto", "float16", "bfloat16"]); ap.add_argument("--max-new", type=int, default=90)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.data)]
    if a.limit: rows = rows[:a.limit]
    if a.dry_run:
        score(rows, [r["completion"] for r in rows]); return
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    base = a.base or json.load(open(f"{a.adapter}/adapter_config.json"))["base_model_name_or_path"]
    try: tok = AutoTokenizer.from_pretrained(base)
    except Exception: base = "Qwen/Qwen3.5-4B"; tok = AutoTokenizer.from_pretrained(base)
    tok.padding_side = "left"
    # Adapter keys are "...model.language_model.layers.N...": they match the multimodal class, not the text-only one.
    # Loading with AutoModelForCausalLM silently skips every adapter weight (peft only warns "missing adapter keys").
    try:
        from transformers import AutoModelForImageTextToText as Cls
    except ImportError:
        Cls = AutoModelForCausalLM
    dt = a.dtype if a.dtype != "auto" else ("bfloat16" if torch.cuda.get_device_capability()[0] >= 8 else "float16")
    print("dtype:", dt, flush=True)
    model = Cls.from_pretrained(base, dtype=getattr(torch, dt), device_map="auto")
    if not a.no_adapter:
        model = PeftModel.from_pretrained(model, prepare_adapter(model, a.adapter))
        nz = sum(1 for n, p in model.named_parameters() if "lora_B" in n and p.abs().sum().item() > 0)
        tot = sum(1 for n, p in model.named_parameters() if "lora_B" in n)
        print(f"adapter check: {nz}/{tot} lora_B tensors nonzero", flush=True)
        if nz == 0: raise SystemExit("Adapter weights NOT loaded (all lora_B are zero). Key names do not match the model class.")
    if not a.no_adapter:
        model = model.merge_and_unload()  # remove LoRA overhead at inference
    model = model.eval()
    def chat(p):
        try: return tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError: return tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True)
    def gen(prompts):
        order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
        res = [None] * len(prompts)
        for i in range(0, len(order), a.bs):
            idx = order[i:i+a.bs]
            b = tok([chat(prompts[j]) for j in idx], return_tensors="pt", padding=True).to(model.device)
            with torch.no_grad(): g = model.generate(**b, max_new_tokens=a.max_new, do_sample=False)
            for j, t in zip(idx, tok.batch_decode(g[:, b["input_ids"].shape[1]:], skip_special_tokens=True)): res[j] = t
            print(f"  {min(i + a.bs, len(order))}/{len(order)} rows", flush=True)
        return res
    pre = RULES if a.with_rules else ""
    preds = gen([pre + r["prompt"] for r in rows])
    with open(a.out, "w") as f:
        for r, p in zip(rows, preds): f.write(json.dumps({"gold": r["completion"], "pred": p}, ensure_ascii=False) + "\n")
    score(rows, preds)
    u = json.load(open(a.urda)); print("\n--- Urda demo ---\nexpected:", u["expected"]); print(gen([pre + u["prompt"]])[0])

if __name__ == "__main__":
    main()
