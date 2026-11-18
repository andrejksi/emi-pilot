"""Turn an `strace -f -ttt -e trace=execve,exit_group` log into a timeline of
the processes EMI started: what each was, when it ran, how long, and how
much of the wall time had at least one test process running.

    python3 timeline.py TRACE [--list]
"""
import re
import sys
from collections import defaultdict

LINE = re.compile(r"^(\d+)\s+(\d+\.\d+)\s+(.*)$")
EXEC = re.compile(r'execve\("([^"]+)", \[(.*?)\](?:, 0x[0-9a-f]+ /\* \d+ vars \*/)?\) = (-?\d+)')
EXIT = re.compile(r"exit_group\((-?\d+)\)")
RESUMED = re.compile(r"<\.\.\. execve resumed>.*= (-?\d+)")


def kind(path, argv):
    a = " ".join(argv)
    base = path.rsplit("/", 1)[-1]
    if base == "git":
        return "git " + (argv[1] if len(argv) > 1 else "")
    if base.startswith("python"):
        if "coverage" in a:
            return "python coverage run"
        if "--collect-only" in a:
            return "python pytest listing"
        if "-m pytest" in a or " pytest" in a:
            return "python pytest run"
        return "python other"
    return base


def parse(path):
    procs = {}
    pending = {}
    first = last = None
    for raw in open(path, errors="replace"):
        m = LINE.match(raw)
        if not m:
            continue
        pid, t, rest = int(m.group(1)), float(m.group(2)), m.group(3)
        first = t if first is None else first
        last = t
        e = EXEC.search(rest)
        if e and e.group(3) == "0":
            argv = re.findall(r'"((?:[^"\\]|\\.)*)"', e.group(2))
            procs[pid] = {"start": t, "path": e.group(1), "argv": argv, "end": None}
            continue
        if "execve(" in rest and "unfinished" in rest:
            e2 = re.search(r'execve\("([^"]+)", \[(.*?)\]', rest)
            if e2:
                pending[pid] = (t, e2.group(1), re.findall(r'"((?:[^"\\]|\\.)*)"', e2.group(2)))
            continue
        r = RESUMED.search(rest)
        if r and r.group(1) == "0" and pid in pending:
            t0, p, argv = pending.pop(pid)
            procs[pid] = {"start": t0, "path": p, "argv": argv, "end": None}
            continue
        x = EXIT.search(rest)
        if x and pid in procs and procs[pid]["end"] is None:
            procs[pid]["end"] = t
            procs[pid]["code"] = int(x.group(1))
    return procs, first, last


def busy(intervals):
    """Seconds covered by at least one interval."""
    total, end = 0.0, None
    for s, e in sorted(intervals):
        if end is None or s > end:
            total += e - s
            end = e
        elif e > end:
            total += e - end
            end = e
    return total


def main():
    procs, first, last = parse(sys.argv[1])
    wall = last - first
    by = defaultdict(list)
    for pid, p in procs.items():
        if p["end"] is None:
            continue
        by[kind(p["path"], p["argv"])].append(p)
    print(f"wall {wall:.1f} s, {len(procs)} processes")
    print(f"{'what':28} {'n':>5} {'total s':>9} {'median s':>9} {'max s':>8}")
    rows = []
    for k, ps in by.items():
        d = sorted(p["end"] - p["start"] for p in ps)
        rows.append((sum(d), k, len(d), d[len(d) // 2], d[-1]))
    for total, k, n, med, mx in sorted(rows, reverse=True)[:15]:
        print(f"{k:28} {n:5} {total:9.1f} {med:9.2f} {mx:8.2f}")
    tests = [(p["start"], p["end"]) for k, ps in by.items() if k.startswith("python") for p in ps]
    gits = [(p["start"], p["end"]) for k, ps in by.items() if k.startswith("git") for p in ps]
    b = busy(tests)
    print(f"\nsome python process running: {b:.1f} s of {wall:.1f} s ({100 * b / wall:.0f}%)")
    print(f"some git process running:    {busy(gits):.1f} s")
    # average number of python processes at once, while any runs
    total = sum(e - s for s, e in tests)
    print(f"python process-seconds {total:.1f}: {total / b:.2f} at once on average while any runs" if b else "")
    if "--list" in sys.argv:
        for pid, p in sorted(procs.items(), key=lambda kv: kv[1]["start"]):
            if p["end"] and kind(p["path"], p["argv"]).startswith("python"):
                print(f"{p['start'] - first:8.1f} {p['end'] - p['start']:6.2f}  {' '.join(p['argv'])[:150]}")


if __name__ == "__main__":
    main()
