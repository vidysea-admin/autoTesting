"""Probe driver. `setup <world> <video> <variant>` builds a world; `run <world> -- args` runs the real CLI.
The only fake is the model provider (no model call, no network) and, for fetch-drive, the Drive seam."""
import json, os, sys
from pathlib import Path

def setup(world: Path, video: Path, variant: str) -> None:
    os.environ["AUTOTESTER_ROOT"] = str(world)
    os.environ["AUTOTESTER_APPROVAL_KEY"] = "probe-only-signing-key-not-a-secret"
    import autotester
    from autotester.schema.approval import RunApproval
    from autotester.schema.enums import ApprovalKind
    from autotester.schema.project import Project
    from autotester.stages.ingest import register_source
    from autotester.store.project_store import ProjectStore
    (world / "AT_FILE").write_text(autotester.__file__)
    if variant == "noproject":
        return
    store = ProjectStore("demo", world)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
    if variant == "emptyproject":
        return
    vid = world / "media" / "rec.mp4"
    vid.parent.mkdir(parents=True, exist_ok=True)
    if variant == "corrupt":
        vid.write_bytes(b"this is not a video at all" * 40)
    elif variant == "audioonly":
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:d=20", "-c:a", "aac", str(vid)], check=True, capture_output=True)
    else:
        vid.write_bytes(video.read_bytes())
    src = register_source(store, vid, label="rec")
    (world / "source_id.txt").write_text(src.id)
    if variant == "truncated":
        vid.write_bytes(b"")
    if variant == "missingfile":
        vid.unlink()
    prov_target = "other-provider" if variant == "wrongprov" else "fake"
    if variant not in ("noapproval",) and not os.environ.get("DRV_NOAPPR"):
        a = RunApproval(project="demo" if variant != "wrongproject" else "someone-else", run_kind=ApprovalKind.VIDEO_REVIEW,
                        target=prov_target, scope="probe", max_actions=500, max_probes=0, wall_clock_s=100000.0,
                        granted_by="probe", granted_at="2026-10-01", expires_at="2099-01-01")
        a.sign(); store.add_approval(a)
    if variant == "lowapproval":
        pass

def run(world: Path, args: list[str]) -> None:
    os.environ["AUTOTESTER_ROOT"] = str(world)
    os.environ["AUTOTESTER_APPROVAL_KEY"] = "probe-only-signing-key-not-a-secret"
    os.environ.update(COLUMNS="100", NO_COLOR="1", PYTHONIOENCODING="utf-8")
    import autotester
    (world / "AT_FILE").write_text(autotester.__file__)
    mode = os.environ.get("DRV_FAKE")
    spy = {"calls": 0, "frames": [], "paths_under_reviews": [], "orig_path_seen": False, "prompt_sha": [], "prompt_len": []}
    if mode:
        from autotester import providers
        from autotester.providers.base import Provider, ProviderError
        from autotester.schema.video_review import ReplyItem, ReviewReply
        import hashlib
        sid = (world / "source_id.txt").read_text() if (world / "source_id.txt").exists() else "src_none"
        orig = str(world / "media" / "rec.mp4")
        def items(n):
            return [ReplyItem(time_s=10 + 9 * i, screen=f"Screen{i}", seen=f"seen {i}", suggestion=f"fix {i}",
                              severity=("S1", "S2", "S3")[i % 3], source_id=sid, origin="visual") for i in range(n)]
        class Fake(Provider):
            id = "fake"
            def available(self): return mode != "unavailable"
            def judge(self, prompt, schema, images=None, *, prompt_file=None, fed_id=None):
                spy["calls"] += 1
                for p in images or []:
                    p = Path(p); spy["frames"].append(p.stem)
                    spy["paths_under_reviews"].append("reviews" in p.parts)
                    if str(p) == orig: spy["orig_path_seen"] = True
                txt = prompt.replace(str(world), "<W>")
                spy["prompt_sha"].append(hashlib.sha256(txt.encode()).hexdigest()[:12]); spy["prompt_len"].append(len(txt))
                (world / "spy.json").write_text(json.dumps(spy))
                big = mode == "costly"
                self.record("judge", 3_000_000 if big else 10, 300_000 if big else 10)
                if mode == "raise_runtime": raise RuntimeError(f"boom secret=CANARY-SECRET-123 at {orig}")
                if mode == "raise_os": raise OSError(f"disk exploded {orig}")
                if mode == "raise_provider": raise ProviderError("provider said no")
                if mode == "interrupt": raise KeyboardInterrupt()
                if mode == "badreply": return {"not": "a ReviewReply"}
                if mode == "many": return ReviewReply(summary="A user does things.", items=items(9))
                return ReviewReply(summary="A user logs in.", items=items(2))
        providers.get = lambda _id, **_kw: Fake()
        (world / "spy.json").write_text(json.dumps(spy))
    if os.environ.get("DRV_DRIVE"):
        sys.path.insert(0, os.environ["DRV_TESTS"])
        from drive_fakes import FakeDrive
        from autotester import cli_intake
        spec = json.loads(os.environ["DRV_DRIVE"]); d = FakeDrive()
        for fid, kw in spec.get("files", {}).items():
            data = Path(kw.pop("path")).read_bytes(); d.add(fid, data, **kw)
        for fid, kids in spec.get("folders", {}).items(): d.folder(fid, kids)
        for fid, lie in spec.get("lie", {}).items(): d.lie[fid] = lie
        cli_intake.default_drive = lambda _s: d
    sys.argv = ["autotester", *args]
    from autotester import main
    main()

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "setup": setup(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
    elif cmd == "both":
        w = Path(sys.argv[2]); setup(w, Path(sys.argv[3]), sys.argv[4])
        i = sys.argv.index("--"); sid = (w / "source_id.txt").read_text() if (w / "source_id.txt").exists() else "src_none"
        run(w, [a.replace("{SRC}", sid).replace("{WORLD}", str(w)) for a in sys.argv[i + 1:]])
    else:
        w = Path(sys.argv[2]); i = sys.argv.index("--"); sid = (w / "source_id.txt").read_text() if (w / "source_id.txt").exists() else "src_none"
        run(w, [a.replace("{SRC}", sid).replace("{WORLD}", str(w)) for a in sys.argv[i + 1:]])
