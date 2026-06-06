"""W15 체인 30분 보고용 — 완료 run(jct.csv) + 진행 run(live) 합쳐 비교 그래프 생성.

출력: /raid/squad/analysis/w15_progress.png + 콘솔 백분위 표.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from kubernetes import client, config

RUNS = "/raid/squad/runs"
ORDER = [("w15_auto", "sfqa-auto", "#cc2222"), ("w15_easy", "EASY", "#22aa55"),
         ("w15_kueue", "Kueue", "#3366cc"), ("w15_sfqa", "SFQA", "#ee8833"),
         ("w15_fifo", "gate-FIFO", "#7799cc")]


def from_csv(run, kueue=False):
    sub = {}
    with open(f"{RUNS}/{run}/submit_log.csv") as f:
        for r in csv.DictReader(f):
            sub[r["job"]] = float(r["wall"])
    out = []
    with open(f"{RUNS}/{run}/jct.csv") as f:
        for r in csv.DictReader(f):
            if not r.get("jct_sec") or not r.get("queue_sec"):
                continue
            job = "-".join(r["pod"].split("-")[:-1])
            if job in sub:
                out.append((sub[job] + float(r["jct_sec"]), float(r["queue_sec"]),
                            float(r["jct_sec"])))
    return out


def from_live(kueue=False):
    config.load_kube_config()
    v1, batch = client.CoreV1Api(), client.BatchV1Api()
    jc = {}
    if kueue:
        jc = {j.metadata.name: j.metadata.creation_timestamp
              for j in batch.list_namespaced_job("squad").items}
    pods = v1.list_namespaced_pod("squad").items
    if not pods:
        return []
    t0 = min(p.metadata.creation_timestamp for p in pods)
    out = []
    for p in pods:
        jn = (p.metadata.labels or {}).get("job-name")
        c = jc.get(jn, p.metadata.creation_timestamp)
        st = p.status.start_time
        fin = None
        if p.status.container_statuses:
            t = p.status.container_statuses[0].state.terminated
            if t:
                fin = t.finished_at
        if c and st and fin:
            out.append(((fin - t0).total_seconds(), (st - c).total_seconds(),
                        (fin - c).total_seconds()))
    return out


def main():
    data = {}
    live_assigned = False
    for run, lab, c in ORDER:
        done = os.path.exists(f"{RUNS}/{run}/jct.csv")
        started = os.path.exists(f"{RUNS}/{run}/submit_log.csv")
        if done:
            data[lab] = (from_csv(run, kueue=(run == "w15_kueue")), c, "final")
        elif started and not live_assigned:
            rows = from_live(kueue=(run == "w15_kueue"))
            if rows:
                data[lab] = (rows, c, "live")
                live_assigned = True

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    print(f"{'정책':12} {'상태':>6} {'n':>5} {'p50':>6} {'p90':>6} {'p99':>6} {'max':>7} {'BSLDp50':>8} {'BSLDmax':>8}")
    for lab, (rows, c, st) in data.items():
        qs = sorted(q for _, q, _ in rows)
        bs = sorted(j / max(j - q, 10.0) for _, q, j in rows)
        n = len(qs)
        pk = lambda a, p: a[min(n - 1, int(n * p))]
        print(f"{lab:12} {st:>6} {n:>5} {pk(qs,.5):>6.0f} {pk(qs,.9):>6.0f} {pk(qs,.99):>6.0f} {qs[-1]:>7.0f} {pk(bs,.5):>8.1f} {bs[-1]:>8.1f}")
        b = {}
        for t, q, _ in rows:
            b.setdefault(int(t // 300), []).append(q)
        xs = sorted(b)
        axes[0].plot([x * 5 for x in xs], [sorted(b[x])[len(b[x]) // 2] for x in xs],
                     color=c, label=f"{lab}{'*' if st=='live' else ''}", linewidth=2)
        PCTS = [.5, .9, .99, 1.0]
        i = list(data).index(lab)
        vals = [qs[-1] if p == 1.0 else pk(qs, p) for p in PCTS]
        axes[1].bar([j + (i - len(data) / 2) * 0.16 for j in range(4)], vals,
                    width=0.16, label=lab, color=c)
        px = [80 + i2 * 0.1 for i2 in range(201)]
        axes[2].plot(px, [qs[min(n - 1, int(n * p / 100))] for p in px],
                     color=c, label=lab, linewidth=2)
    axes[0].set_xlabel("run time (min)"); axes[0].set_ylabel("queueing delay (s)")
    axes[0].set_title("trend p50 per 5min (* = in progress)"); axes[0].grid(alpha=.3); axes[0].legend(fontsize=8)
    axes[1].set_xticks(range(4), ["p50", "p90", "p99", "max"]); axes[1].grid(axis="y", alpha=.3)
    axes[1].set_title("percentiles"); axes[1].legend(fontsize=8)
    axes[2].set_xlabel("percentile"); axes[2].set_title("tail zoom (top 20%)")
    axes[2].grid(alpha=.3); axes[2].legend(fontsize=8)
    fig.suptitle("Philly-300-C48-W15 (load 1.17x, peak 3.8x, S=240) — 5 policies", fontsize=11)
    fig.tight_layout()
    fig.savefig("/raid/squad/analysis/w15_progress.png", dpi=130)
    print("→ /raid/squad/analysis/w15_progress.png")


if __name__ == "__main__":
    main()
