#!/usr/bin/env python3
"""Validate orchestrator result records and referenced artifacts."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("plan",type=Path); ap.add_argument("dag",type=Path); ap.add_argument("results",type=Path); ap.add_argument("--out",required=True,type=Path); a=ap.parse_args()
    plan=read(a.plan); dag=read(a.dag); expected={t["id"] for t in plan["tasks"]}; issues=[]; records={}
    for tid in expected:
        p=a.results/(tid+".json")
        if not p.is_file(): issues.append(f"missing result: {tid}"); continue
        try: r=read(p)
        except Exception as e: issues.append(f"invalid JSON {tid}: {e}"); continue
        records[tid]=r
        if r.get("task_id")!=tid: issues.append(f"{tid}: task_id mismatch")
        if r.get("status")!="DONE": issues.append(f"{tid}: status is {r.get('status')}")
        for key in ("summary","evidence","artifacts","checks","issues"):
            if key not in r: issues.append(f"{tid}: missing {key}")
        if not r.get("evidence"): issues.append(f"{tid}: no evidence")
        if not r.get("checks"): issues.append(f"{tid}: no checks")
        for path in r.get("artifacts",{}).values() if isinstance(r.get("artifacts"),dict) else []:
            q=Path(path); q=q if q.is_absolute() else a.results.parent.parent/q
            if not q.is_file() or q.stat().st_size==0: issues.append(f"{tid}: missing/empty artifact {path}")
    report={"format":1,"status":"PASS" if not issues else "FAIL","tasks":len(expected),"waves":dag.get("waves",[]),"issues":issues,"records":sorted(records)}
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2)); return 0 if not issues else 1
if __name__=="__main__": raise SystemExit(main())
