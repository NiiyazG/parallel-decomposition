#!/usr/bin/env python3
"""Validate a plan and emit a deterministic DAG with topological waves."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

EDGE_TYPES = {"DATA", "RESOURCE", "ORDER", "DECISION"}
MODES = {"read", "write"}

def load(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e: raise SystemExit(f"INVALID_JSON: {path}: {e}")

def fail(msg): raise SystemExit("FAIL: " + msg)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("plan",type=Path); ap.add_argument("--dag",required=True,type=Path); ap.add_argument("--check-snapshot",action="store_true"); a=ap.parse_args()
    plan=load(a.plan); tasks=plan.get("tasks");
    if not isinstance(tasks,list) or not tasks: fail("tasks must be a non-empty array")
    limit=plan.get("max_parallel", 5)
    if not isinstance(limit,int) or not 1 <= limit <= 5: fail("max_parallel must be an integer from 1 to 5")
    ids=[t.get("id") for t in tasks]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)): fail("task IDs must be unique non-empty strings")
    byid={t["id"]:t for t in tasks}; edges=[]; edge_keys=set(); outputs=set()
    def add(u,v,k,reason=""):
        if u==v: fail(f"self dependency: {u}")
        key=(u,v,k)
        if key not in edge_keys: edge_keys.add(key); edges.append({"from":u,"to":v,"type":k,"reason":reason})
    for t in tasks:
        for key in ("goal","inputs","outputs","depends_on","resources","done_criteria"):
            if key not in t: fail(f"{t['id']}: missing {key}")
        for o in t["outputs"]:
            path=o.get("path")
            if not isinstance(path,str) or not path or Path(path).is_absolute() or ".." in Path(path).parts: fail(f"{t['id']}: output path must be relative and confined")
            if path in outputs: fail(f"duplicate output path: {path}")
            outputs.add(path)
        if t.get("max_retries",0) not in (0,1): fail(f"{t['id']}: max_retries must be 0 or 1")
        if not isinstance(t.get("idempotent"),bool): fail(f"{t['id']}: idempotent must be boolean")
        for d in t["depends_on"]:
            if d.get("id") not in byid: fail(f"{t['id']}: unknown dependency {d.get('id')}")
            if d.get("type") not in EDGE_TYPES: fail(f"{t['id']}: invalid edge type")
            add(d["id"],t["id"],d["type"],d.get("reason",""))
        for r in t["resources"]:
            if r.get("mode") not in MODES or not r.get("id"): fail(f"{t['id']}: invalid resource")
    for i,x in enumerate(tasks):
        for y in tasks[i+1:]:
            for rx in x["resources"]:
                for ry in y["resources"]:
                    if rx["id"]==ry["id"] and (rx["mode"]=="write" or ry["mode"]=="write"):
                        add(x["id"],y["id"],"RESOURCE",f"deterministic resource order for {rx['id']}")
    if a.check_snapshot:
        for t in tasks:
            for inp in t["inputs"]:
                src=inp.get("source","")
                if src.startswith("snapshot:"):
                    name=src.split(":",1)[1]; snap=a.plan.parent/"snapshot"; manifest=snap/"manifest.json"
                    if not manifest.is_file(): fail(f"snapshot manifest missing: {manifest}")
                    data=load(manifest); item=next((x for x in data.get("files",[]) if x.get("name")==name),None)
                    if not item or not (snap/name).is_file(): fail(f"snapshot input missing: {name}")
                    h=hashlib.sha256((snap/name).read_bytes()).hexdigest()
                    if h!=item.get("sha256"): fail(f"snapshot hash mismatch: {name}")
    adj={i:[] for i in ids}; indeg={i:0 for i in ids}
    for e in edges: adj[e["from"]].append(e["to"]); indeg[e["to"]]+=1
    waves=[]; remaining=set(ids)
    while remaining:
        wave=sorted(i for i in remaining if indeg[i]==0)
        if not wave: fail("cycle detected")
        if len(wave)>limit: fail(f"wave has {len(wave)} tasks, max_parallel is {limit}")
        waves.append(wave)
        for u in wave:
            remaining.remove(u)
            for v in adj[u]: indeg[v]-=1
    dag={"format":1,"nodes":ids,"edges":edges,"waves":waves,"max_parallel":limit}
    a.dag.parent.mkdir(parents=True,exist_ok=True); a.dag.write_text(json.dumps(dag,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","tasks":len(ids),"edges":len(edges),"waves":waves},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
