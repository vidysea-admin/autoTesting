import os,sys,json
src=open(os.environ["DOORS"]).read().split("rows = {}")[0]
exec(compile(src,"doors","exec"))
root,store=fresh(approve=True)
routes_runs._run_queued(QueueEntry(id="run-QQ", project="demo", requested_by="alice", trigger="schedule"))
d=json.loads((root/"projects/demo/runs/run-QQ/run.json").read_text(encoding="utf-8"))
print({k:d.get(k,"<absent>") for k in ("trigger","requested_by","slot_key","via")})
