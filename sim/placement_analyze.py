"""placement_table.csv → 피벗 표 + Q1~Q3 정량 답 + LaTeX 스니펫.

Q1: SAFA(sfqa-auto)의 p1 이점이 4배치 전부에서 유지되는가?
Q2: 배치가 절대 성능·정책 상대 순위를 바꾸는가?
Q3: mcts 배치 비용?
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "sweep_results", "placement", "placement_table.csv")
PLACE = ["mostallocated", "compact", "round_robin", "mcts"]
POLS = ["sfqa-auto", "fifo", "sjf", "sfqa", "las"]
CFGS = ["512:single", "512:hetero", "256:hetero"]

rows = list(csv.DictReader(open(T)))
D = {}  # (cfg, place, pol) -> row
for r in rows:
    if r.get("error"):
        continue
    D[(r["config"], r["placement"], r["policy"])] = r


def g(cfg, place, pol, key):
    r = D.get((cfg, place, pol))
    return float(r[key]) if r and r.get(key) not in (None, "") else None


print("=" * 100)
print("배치 × 정책 × 구성  —  fair_p1 (worst-1% order-fairness, 높을수록 공정; FIFO=100)")
print("=" * 100)
for cfg in CFGS:
    print(f"\n## {cfg}")
    print(f"{'policy':<11} " + " ".join(f"{p:>14}" for p in PLACE))
    for pol in POLS:
        cells = []
        for pl in PLACE:
            v = g(cfg, pl, pol, "fair_p1")
            cells.append(f"{v:>14.2f}" if v is not None else f"{'--':>14}")
        print(f"{pol:<11} " + " ".join(cells))

print("\n" + "=" * 100)
print("배치 × 정책 × 구성  —  q_p50 (중앙 큐 지연 초; 낮을수록 빠름)")
print("=" * 100)
for cfg in CFGS:
    print(f"\n## {cfg}")
    print(f"{'policy':<11} " + " ".join(f"{p:>14}" for p in PLACE))
    for pol in POLS:
        cells = []
        for pl in PLACE:
            v = g(cfg, pl, pol, "q_p50")
            cells.append(f"{v:>14.0f}" if v is not None else f"{'--':>14}")
        print(f"{pol:<11} " + " ".join(cells))

# ── Q1: SAFA p1 이점 — 4배치 각각에서 sfqa-auto가 sjf/las보다 공정한가? FIFO 대비? ──
print("\n" + "=" * 100)
print("Q1: SAFA(sfqa-auto) p1 이점이 4배치 전부에서 유지되는가?")
print("    기준: sfqa-auto p1 > max(sjf,las) p1 (공정성 우위) — 구성·배치별 판정")
print("=" * 100)
q1_all = True
for cfg in CFGS:
    for pl in PLACE:
        sa = g(cfg, pl, "sfqa-auto", "fair_p1")
        sj = g(cfg, pl, "sjf", "fair_p1")
        la = g(cfg, pl, "las", "fair_p1")
        ff = g(cfg, pl, "fifo", "fair_p1")
        if None in (sa, sj, la):
            print(f"  {cfg:<11} {pl:<14}  (불완전)")
            continue
        base = max(sj, la)
        ok = sa >= base
        q1_all = q1_all and ok
        mark = "OK " if ok else "XX "
        print(f"  {mark}{cfg:<11} {pl:<14}  sfqa-auto p1={sa:6.2f}  vs sjf={sj:6.2f}/las={la:6.2f} "
              f"(base={base:6.2f}, Δ={sa-base:+6.2f})  fifo={ff if ff else 0:6.2f}")
print(f"\n  >>> Q1 종합: SAFA p1 우위가 {'모든' if q1_all else '일부(아래 XX)'} (배치,구성)에서 "
      f"{'유지됨' if q1_all else '유지되지 않음 — 정직 보고'}")

# ── Q2: 배치가 정책 상대 순위를 바꾸는가? (각 구성에서 p1 기준 정책 순위) ──
print("\n" + "=" * 100)
print("Q2: 배치가 정책 상대 순위(p1 기준)를 바꾸는가? — 바꾸지 않아야 '배치 무관' 성립")
print("=" * 100)
for cfg in CFGS:
    print(f"\n## {cfg}  (p1 내림차순 정책 순위, 배치별)")
    rank_sets = {}
    for pl in PLACE:
        ranked = sorted([p for p in POLS if g(cfg, pl, p, "fair_p1") is not None],
                        key=lambda p: -g(cfg, pl, p, "fair_p1"))
        rank_sets[pl] = ranked
        print(f"  {pl:<14}: " + " > ".join(ranked))
    # 순위 동일성
    refs = list(rank_sets.values())
    same = all(r == refs[0] for r in refs)
    print(f"  → 4배치 p1 순위 {'동일(배치 무관 성립)' if same else '상이 — 차이 확인 필요'}")
    # q_p50 절대 영향(같은 정책, 배치별 q_p50 범위)
    print(f"  q_p50 배치 영향(정책별 min~max):")
    for pol in POLS:
        vs = [g(cfg, pl, pol, "q_p50") for pl in PLACE if g(cfg, pl, pol, "q_p50") is not None]
        if vs:
            sp = (max(vs) - min(vs)) / max(1.0, min(vs)) * 100
            print(f"    {pol:<11} {min(vs):>11.0f}~{max(vs):>11.0f}  (spread {sp:5.1f}%)")

# ── Q3: mcts 비용 ──
print("\n" + "=" * 100)
print("Q3: MCTS 배치 비용 (wall-clock, 롤아웃 호출수)")
print("=" * 100)
for cfg in CFGS:
    for pol in POLS:
        r = D.get((cfg, "mcts", pol))
        rm = D.get((cfg, "mostallocated", pol))
        if r:
            w = float(r["wall_s"]); wm = float(rm["wall_s"]) if rm else 0
            print(f"  {cfg:<11} {pol:<11}  mcts={w:7.2f}s  vs most-alloc={wm:7.2f}s "
                  f"({w/max(wm,0.01):4.1f}x)  calls={r['mcts_calls']} rollouts={r['mcts_rollouts']}")
