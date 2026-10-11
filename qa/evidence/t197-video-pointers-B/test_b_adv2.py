import json, subprocess, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from test_b_adv import *  # noqa


def _mk(tmp_path_factory, fps, dur=130):
    out = tmp_path_factory.mktemp("bv2") / f"rec{fps}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=s=160x120:r={fps}:d={dur}",
                    "-c:v", "libx264", "-preset", "veryfast", str(out)],
                   check=True, capture_output=True, timeout=120)
    return out


def test_determinism_diff(tmp_path, video_file, monkeypatch):
    outs = []
    for i in range(2):
        root = tmp_path / f"r{i}"; root.mkdir()
        store, source, provider = make_world(root, video_file, monkeypatch)
        grant(store)
        r = review(source, "--redact", "0:55-1:15", "--pointers", ptr(root, "0:10-2:00 | n\n1:00\n"))
        rid = json.loads(r.stdout)["id"]
        outs.append(json.loads((store.paths.dir / "reviews" / f"{rid}.json").read_text("utf-8")))
        time.sleep(1.1)
    keys = [k for k in outs[0] if outs[0][k] != outs[1][k]]
    print("DIFFERING KEYS:", keys, [(outs[0][k], outs[1][k]) for k in keys][:4])
    for d in outs:
        d.pop("created_at", None)
    assert outs[0] == outs[1]


def test_edge_windows_25fps(tmp_path_factory, tmp_path, monkeypatch):
    v = _mk(tmp_path_factory, 25)
    store, source, provider = make_world(tmp_path, v, monkeypatch)
    grant(store)
    for spec in ["2:00-2:10", "0:00-2:10", "0:00-0:05"]:
        provider.calls = 0
        r = review(source, "--redact", spec, "--refresh", json_out=False)
        print("25fps window", spec, "exit", r.exit_code, "calls", provider.calls,
              (r.stderr or r.output).strip().splitlines()[-1][:160])


def test_edge_windows_1fps_msg(tmp_path, video_file, monkeypatch):
    store, source, provider = make_world(tmp_path, video_file, monkeypatch)
    grant(store)
    r = review(source, "--redact", "2:00-2:10", json_out=False)
    print("1fps tail window:", r.exit_code, (r.stderr or r.output).strip().splitlines()[-1][:200])


def test_unicode_digits(world):
    store, source, provider, tmp = world
    grant(store)
    for t in ["\u0663:\u0660\u0660\n", "\uff11:\uff10\uff10\n"]:
        r = review(source, "--pointers", ptr(tmp, t))
        print(ascii(t), "->", r.exit_code, "calls", provider.calls)
