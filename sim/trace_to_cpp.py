"""전체 Philly 트레이스 → C++/Windows 시뮬레이터 Job CSV + 매칭 server CSV.

C++ 시뮬(gpu_scheuer/)은 분 단위 이산시간이라 wall-clock 없이 전체 트레이스를 즉시 계산한다
(=사용자 의도 "시뮬레이터니 시간축 압축". C++은 datetime을 분 인덱스로 변환해 처리).
샘플링 없이 전체 사용, JCT는 48h 클램프, 측정 오버헤드를 finish에 반영.

C++ Job CSV 컬럼(job_emulator.cpp build_job_list 순):
  pod_name,pod_type,project,namespace,user_team,start,finish,count,time_diff,
  computing_load,gpu_utilization,flavor,preemption
  - start/finish: ISO datetime → C++이 분 단위로 변환(finish-start=duration+overhead)
  - count: gpu_count, flavor: GPU 타입(get_accelerator_type 매핑), preemption: y/n

오버헤드 반영(results/overheads/params.md):
  K8s 고정 = sched_lat+startup+teardown ≈ 5s (분 단위라 올림 1min floor 적용 옵션)
  PTR 다운타임 = preemptible 잡에 D(크기 모델) 추가(이주 가정 1회분, 보수적)

매칭 server: 전체 트레이스 peak demand를 받도록 노드 수 산정(기본 capacity_factor로 조절).

사용:
  trace_to_cpp.py --clamp-hours 48 --flavor a100 --capacity-factor 1.2 \
    --out-job results/philly_full_c48_cpp.csv --out-server results/server_philly_full.csv
"""
import argparse
import csv
import json
import math
from datetime import datetime, timedelta


def ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/raid/squad/traces/philly/repo/trace-data/cluster_job_log")
    ap.add_argument("--clamp-hours", type=float, default=48.0)
    ap.add_argument("--flavor", default="a100", help="C++ enum 매핑 타입(v100/a30/a100/h100/h200/l4/l40/b200)")
    ap.add_argument("--gpus-per-node", type=int, default=8)
    ap.add_argument("--capacity-factor", type=float, default=1.2,
                    help="총 GPU = ceil(peak_demand × factor). 1.0=peak, >1 여유")
    ap.add_argument("--overhead-floor-min", type=int, default=1,
                    help="K8s 고정 오버헤드 분 단위 floor(분 해상도라 ≥1 권장, 0=무시)")
    ap.add_argument("--compress", type=float, default=1.0,
                    help="시간축 압축 C: arrival·duration을 /C (C++ 분-그리드 축소). 오버헤드는 비압축(실제 비용)")
    ap.add_argument("--ptr-downtime", action="store_true",
                    help="preemptible 잡에 PTR 다운타임 D를 finish에 추가(이주 1회 가정)")
    ap.add_argument("--out-job", default="/home/mystous/gpu_scheduler/results/philly_full_c48_cpp.csv")
    ap.add_argument("--out-server", default="/home/mystous/gpu_scheduler/results/server_philly_full.csv")
    args = ap.parse_args()

    with open(args.input) as f:
        raw = json.load(f)

    LIM = args.clamp_hours * 3600
    # K8s 고정 오버헤드(초) = sched 0.5 + startup(경합 3.5) + teardown 2.5
    k8s_ovh = 6.5
    # PTR D 모델(params.md): ckpt_gib_per_gpu*(1/0.85+1/1.75)+3 ; params 프록시 gpu_count로
    params_proxy = {1: 7.0, 2: 13.0, 4: 32.0, 8: 70.0}

    jobs = []
    for j in raw:
        sub = ts(j.get("submitted_time"))
        tot = 0.0; g = 0
        for a in j.get("attempts", []):
            s, e = ts(a.get("start_time")), ts(a.get("end_time"))
            if s and e:
                tot += (e - s).total_seconds()
                g = max(g, sum(len(d.get("gpus", [])) for d in a.get("detail", [])))
        if tot <= 0 or g <= 0:
            continue
        start = sub or ts(j["attempts"][0]["start_time"])
        if start is None:
            continue
        # 시뮬레이터에서 압축은 시간 단위 환산 → arrival·duration·오버헤드 전부 /C (비율 보존)
        dur = min(tot, LIM)
        preempt = len(j.get("attempts", [])) > 1
        ovh = 0.0
        if args.overhead_floor_min > 0:
            ovh += max(k8s_ovh, args.overhead_floor_min * 60)
        if args.ptr_downtime and preempt:
            pb = params_proxy.get(g, 7.0 * g)
            ckpt_gib = (pb * 1e9 / g) * 10 / 1024**3
            ovh += ckpt_gib * (1 / 0.85 + 1 / 1.75) + 3
        total = (dur + ovh) / args.compress       # 오버헤드 포함 전체를 /C
        jobs.append({"start": start, "dur": total, "gpu": g, "preempt": preempt,
                     "jid": j.get("jobid", str(len(jobs)))})

    jobs.sort(key=lambda x: x["start"])
    t0 = jobs[0]["start"]
    if args.compress != 1.0:   # arrival 도 /C (t0 기준 상대시각 압축 후 재구성)
        for jb in jobs:
            rel = (jb["start"] - t0).total_seconds() / args.compress
            jb["start"] = t0 + timedelta(seconds=rel)

    # peak demand(원 스케일) 이벤트 스윕
    ev = []
    for jb in jobs:
        s = (jb["start"] - t0).total_seconds()
        ev.append((s, jb["gpu"])); ev.append((s + jb["dur"], -jb["gpu"]))
    ev.sort()
    cur = peak = 0
    for _, d in ev:
        cur += d; peak = max(peak, cur)
    total_gpu = max(args.gpus_per_node, math.ceil(peak * args.capacity_factor))
    n_nodes = math.ceil(total_gpu / args.gpus_per_node)

    # Job CSV
    cols = ["pod_name", "pod_type", "project", "namespace", "user_team", "start", "finish",
            "count", "time_diff", "computing_load", "gpu_utilization", "flavor", "preemption"]
    with open(args.out_job, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, jb in enumerate(jobs):
            fin = jb["start"] + timedelta(seconds=jb["dur"])
            secs = int((fin - jb["start"]).total_seconds())
            d, rem = divmod(secs, 86400)
            h, rem = divmod(rem, 3600)
            mi, s = divmod(rem, 60)
            td = f"{d} days {h:02}:{mi:02}:{s:02}"   # 원본 포맷(쉼표 없음 — C++ 파서 호환)
            w.writerow([f"job-{i}", "task", "PROJECT", "ns", "TEAM",
                        jb["start"].strftime("%Y-%m-%d %H:%M:%S+00:00"),
                        fin.strftime("%Y-%m-%d %H:%M:%S+00:00"),
                        jb["gpu"], td, 1, 50.0, args.flavor,
                        "y" if jb["preempt"] else "n"])

    # server CSV
    with open(args.out_server, "w", newline="") as f:
        w = csv.writer(f)
        for k in range(n_nodes):
            w.writerow([f"gpu_server{k}", args.gpus_per_node, args.flavor])

    span_days = (jobs[-1]["start"] - t0).total_seconds() / 86400
    print(f"전체 잡 {len(jobs)} (무샘플), arrival span {span_days:.0f}일, clamp {args.clamp_hours}h")
    print(f"peak demand {peak} GPU → server {n_nodes}노드×{args.gpus_per_node} = {total_gpu} GPU "
          f"(factor {args.capacity_factor}, 부하 {peak/total_gpu:.2f}×)")
    print(f"오버헤드: K8s floor {args.overhead_floor_min}min" +
          (" + PTR D(preemptible)" if args.ptr_downtime else "") + " → finish에 반영")
    print(f"→ {args.out_job}\n→ {args.out_server}")
    print(f"\nC++ 실행: ./experiment_gpu '{args.out_job}' '{args.out_server}' config.set")


if __name__ == "__main__":
    main()
