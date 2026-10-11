"""Watchdog race hunt. usage: race.py fast N out | near VARIANT N out"""
from __future__ import annotations

import collections
import json
import os
import random
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl  # noqa: E402
from hl import PATH, Listener, good_json, http_head  # noqa: E402

launch = hl.launch
mode = sys.argv[1]
fetched = []
orig_fetch = launch._fetch_version


def rec(p):
    try:
        r = orig_fetch(p); fetched.append(len(r)); return r
    except BaseException as e:
        fetched.append(type(e).__name__); raise


launch._fetch_version = rec
base = set(threading.enumerate())

if mode == "fast":
    n, out = int(sys.argv[2]), sys.argv[3]

    def good(c):
        c.request(); j = good_json(c.port); c.send(http_head(len(j)) + j); c.wait(0.05)
    lst = Listener(good, backlog=128)
    res = collections.Counter(); exc = []; left = 0; worst = 0
    t_all = time.monotonic()
    for i in range(n):
        t0 = time.monotonic()
        try:
            r = launch._answers_as(lst.port, PATH)
        except BaseException as e:
            r = "EXC"; exc.append(repr(e))
        worst = max(worst, time.monotonic() - t0)
        res[str(r)] += 1
        if foreign := hl.foreign_threads(base):
            left += 1
            time.sleep(0.05)
    time.sleep(0.2)
    summary = dict(mode="fast", n=n, results=dict(res), exceptions=exc[:5], iters_with_extra_thread_immediately=left,
                   threads_at_end=hl.foreign_threads(base), max_wall=round(worst, 3),
                   total_s=round(time.monotonic() - t_all, 1), accepts=lst.accepts,
                   open_client_socks=sum(s.fileno() != -1 for s in hl.SOCKS))
    lst.stop()
else:
    variant, n, out = sys.argv[2], int(sys.argv[3]), sys.argv[4]
    # a: whole valid reply sent at t~2.0 | b: headers + first half of body immediately, 2nd half at t~2.0
    # c: complete valid JSON immediately, CL declares +40 spaces that arrive at t~2.0 (truncation-still-valid)
    declared_of = {}

    def beh(c):
        c.request(); j = good_json(c.port)
        s = random.uniform(1.99, 2.01)
        if variant == "a":
            c.wait(s); c.send(http_head(len(j)) + j)
        elif variant == "b":
            c.send(http_head(len(j)) + j[:len(j) // 2]); c.wait(s); c.send(j[len(j) // 2:])
        else:
            c.send(http_head(len(j) + 40) + j); c.wait(s); c.send(b" " * 40)
        c.wait(0.3)
        declared_of[c.lst.accepts] = len(j) + (40 if variant == "c" else 0)
    lst = Listener(beh, backlog=128)
    rows = []; res = collections.Counter(); walls = []
    for i in range(n):
        fetched.clear(); t0 = time.monotonic()
        try:
            r = launch._answers_as(lst.port, PATH)
        except BaseException as e:
            r = "EXC:" + repr(e)
        wall = time.monotonic() - t0
        walls.append(wall)
        declared = None
        j = good_json(lst.port)
        declared = len(j) + (40 if variant == "c" else 0)
        got = fetched[0] if fetched else None
        kind = ("True-full" if r is True and got == declared else
                "True-TRUNCATED" if r is True else "False" if r is False else str(r))
        if r is False:
            kind += f"({got if isinstance(got, str) else 'short:' + str(got)})"
        res[kind] += 1
        rows.append((round(wall, 4), kind))
    walls.sort()
    summary = dict(mode="near", variant=variant, n=n, results=dict(res),
                   wall_min=round(walls[0], 3), wall_median=round(walls[len(walls) // 2], 3),
                   wall_max=round(walls[-1], 3), threads_at_end=hl.foreign_threads(base),
                   open_client_socks=sum(s.fileno() != -1 for s in hl.SOCKS))
    summary["rows_sample"] = rows[:10]
    time.sleep(0.2); lst.stop()
print(json.dumps(summary, indent=1))
json.dump(summary, open(out, "w"), indent=1)
