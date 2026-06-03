"""squad_algo Python 포팅 검증 — Go(pkg/squad)와 동일한 6개 케이스. `python3 -m pytest` 또는 직접 실행."""
from squad_algo import (
    Server, PendingJob, RunningJob, Params, Slot,
    compute_r_table, pstar, reorder_queue, Defrag,
)


def _srv(name, gt, total, fixed=0, floating=0, job=""):
    s = Server(name=name, gpu_type=gt, total=total)
    i = 0
    for _ in range(fixed):
        s.slots[i] = Slot.FIXED; i += 1
    for _ in range(floating):
        s.slots[i] = Slot.FLOATING; s.job_ids[i] = job; i += 1
    while i < total:
        s.slots[i] = Slot.EMPTY; i += 1
    return s


def test_r_table():
    s = _srv("n0", "b200", 8, fixed=6)  # avail=2
    R = compute_r_table([s], "b200")
    assert abs(R[0] - 0.9) < 1e-9 and abs(R[1] - 1.0) < 1e-9 and abs(R[2]) < 1e-9, R


def test_r_table_flavor_aware():
    h = _srv("h", "h100", 8)            # 전부 empty
    b = _srv("b", "b200", 8, fixed=7)   # avail=1
    R = compute_r_table([h, b], "b200")
    assert abs(R[0] - 1.0) < 1e-9 and abs(R[1]) < 1e-9, R


def test_reorder_active():
    s = _srv("n0", "b200", 8, fixed=6)
    jobs = [PendingJob("J1", 1, "b200", age=0), PendingJob("J2", 1, "b200", age=100)]
    out = reorder_queue(jobs, [s], "b200", Params(), 50.0)  # AR=50 ≤ β80
    assert out[0].id == "J2", [ (j.id, j.pstar) for j in out ]


def test_reorder_inactive():
    s = _srv("n0", "b200", 8, fixed=7)
    jobs = [PendingJob("J1", 1, "b200", age=0), PendingJob("J2", 1, "b200", age=100)]
    out = reorder_queue(jobs, [s], "b200", Params(), 90.0)  # AR=90 > β80
    assert out[0].id == "J1" and out[1].id == "J2"


def test_defrag_basic():
    servers = [_srv("n0", "b200", 8, floating=4, job="A"), _srv("n1", "b200", 8, floating=4, job="B")]
    jobs = [RunningJob("A", 4, "b200", 0), RunningJob("B", 4, "b200", 1)]
    improved, plan, before, after = Defrag(servers, jobs).run()
    assert improved and before == 0 and after == 1, (improved, before, after)
    assert sum(1 for j in plan if j.target_index >= 0) == 1


def test_defrag_heterogeneous_guard():
    servers = [_srv("n0", "b200", 8, floating=4, job="A"), _srv("n1", "h100", 8, floating=4, job="B")]
    jobs = [RunningJob("A", 4, "b200", 0), RunningJob("B", 4, "h100", 1)]
    improved, _, before, after = Defrag(servers, jobs).run()
    assert not improved and before == 0 and after == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn(); print(f"PASS {fn.__name__}"); passed += 1
    print(f"\n{passed}/{len(fns)} PASS")
