"""버스트 트레이스에서 컨트롤러 의미론 4조합 충실 리플레이 — 새 권장(blocking+counter)이
시뮬 SAFA와 수렴하는지 로컬 검증. 트레이스: philly_sample500의 원 도착 보존(클램프 없음=버스트)."""
import csv, sys
sys.path.insert(0,"sim")
from order_fairness import per_job_score

KAPPA=30.0; MIN_DUR=2.0; GPUS=8
rows=[]
with open("results/philly_sample500_jct2h_window.csv") as f:
    for r in csv.DictReader(f):
        rows.append((r["job_id"], float(r["arrival_time_s"])/KAPPA,
                     max(MIN_DUR,float(r["duration_s"])/KAPPA), min(8,int(r["gpu_count"]))))
rows.sort(key=lambda x:x[1])
JOBS=[dict(id=j,arr=a,svc=d,gpu=g,rank=i) for i,(j,a,d,g) in enumerate(rows)]
print(f"jobs={len(JOBS)}, 도착 span={JOBS[-1]['arr']:.0f}s (클램프 없음=원 버스트 보존)")

def r_table(free):
    R=[0.0]*8
    for req in range(1,9):
        s=req-free; v=1.0 if s<=0 else 1.0-0.1*s; R[req-1]=v if v>0 else 0.0
    return R

def order_auto(pend, free, now, age_mode, seen):
    fifo=sorted(pend,key=lambda p:p["arr"]); n=len(fifo)
    if n<=1: return fifo
    R=r_table(free)
    if age_mode=="counter":
        for p in fifo:
            if p["id"] not in seen: seen[p["id"]]=len(seen)
        total=len(seen)
        ages=[float(total-seen[p["id"]]) for p in fifo]
    else:
        ages=[now-p["arr"] for p in fifo]
    rq=[(R[p["gpu"]-1] if R[p["gpu"]-1]>0 else 0.5) for p in fifo]
    amin=min(ages); rel=[a-amin for a in ages]
    aref=max(1.0,sum(rel)/n); rmin=max(0.1,min(rq))
    g=min(1.0,max(rel)/aref); ae=g/(aref*rmin)
    bi,bv=0,None
    for i in range(n):
        P=1.0/(2.0**i) if i<60 else 0.0; v=P+ae*rel[i]*rq[i]
        if bv is None or v>bv: bv,bi=v,i
    return [fifo[bi]]+fifo[:bi]+fifo[bi+1:]

def replay(release, age_mode, period=5.0):
    free=GPUS; running=[]; placed={}; seen={}
    now=0.0; guard=0
    while len(placed)<len(JOBS) and guard<10**6:
        guard+=1
        nr=[]
        for (e,g,jid) in running:
            if e<=now: free+=g
            else: nr.append((e,g,jid))
        running=nr
        pend=[j for j in JOBS if j["arr"]<=now and j["id"] not in placed]
        if pend:
            ordered=order_auto(pend,free,now,age_mode,seen)
            for p in ordered:
                if p["gpu"]<=free:
                    free-=p["gpu"]; running.append((now+p["svc"],p["gpu"],p["id"])); placed[p["id"]]=now
                elif release=="blocking":
                    break
        now+=period
    jb=[(j["arr"],placed[j["id"]],0) for j in JOBS if j["id"] in placed]
    sc=sorted(per_job_score(jb)); n=len(sc)
    qd=sorted(placed[j["id"]]-j["arr"] for j in JOBS if j["id"] in placed)
    return dict(p1=round(sc[n//100],1), lt50=round(100*sum(1 for x in sc if x<50)/n,2),
                q_p50=round(qd[len(qd)//2]), placed=len(placed))

print(f"{'release':9} {'age':8} {'p1':>6} {'lt50%':>6} {'q_p50':>7} {'placed':>6}")
res={}
for rel in ("blocking","greedy"):
    for am in ("counter","wall"):
        m=replay(rel,am); res[f"{rel}_{am}"]=m
        print(f"{rel:9} {am:8} {m['p1']:6.1f} {m['lt50']:6.2f} {m['q_p50']:7} {m['placed']:6}")
import json; json.dump(res,open("/tmp/burst_replay.json","w"),indent=1)
