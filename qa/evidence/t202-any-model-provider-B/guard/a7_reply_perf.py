"""a7: model-reply content in ProviderError; over-withholding; guard performance."""
import time
from h import run, outcome, reply, where_leaked

S = "Zq7!kP2x9Lm4"
print("== model reply echoes a value as a JSON key -> pydantic loc -> ProviderError text (schema strategy) ==")
r = run(None, "Grade this: whatever", secrets=["unrelated-secret-value"],
        responses=[reply('{"verdict":"ok","' + S + '":1}')])
print("  msg:", r["exc"])
print("  value in msg:", S in str(r["exc"]))

print("== same, json strategy: repair call carries the key back (guard should refuse it) ==")
r = run(f"MY_SECRET={S}\n", "Grade this: whatever", strategy="json",
        responses=[reply('{"verdict":"ok","' + S + '":1}'), reply('{"verdict":"ok"}')])
print("  outcome:", outcome(r), "| calls:", len(r["fake"].calls), "| msg:", r["exc"])
print("  value in msg:", S in str(r["exc"]))

print("== over-withholding: assistant repair text '{' is a prefix-echo of any exception containing '{' ==")
r = run(None, "Grade this: whatever", strategy="json",
        responses=[reply("{"), RuntimeError('RateLimitError: {"error":"quota exceeded, retry in 20s"}')])
print("  msg:", r["exc"])

print("== guard latency ==")
secrets = [f"Sec{i}-" + "Xy9!qLm2" * 3 for i in range(10)]
env = "".join(f"K{i}={s}\n" for i, s in enumerate(secrets))
payloads = {
    "500KB english": ("The quick brown fox jumps over the lazy dog. " * 12000)[:500_000],
    "500KB 'a'*": "a" * 500_000,
    "200KB '%25'*": "%25" * 70_000,
    "200KB '&amp;'*": "&amp;" * 40_000,
    "300KB CJK": "密码测试" * 75_000,
    "300KB base64-ish": ("QUJDREVGR0hJSktMTU5PUA==" * 12500),
}
for name, p in payloads.items():
    t = time.perf_counter()
    r = run(env, p)
    print(f"  {name:20} {outcome(r):22} {time.perf_counter() - t:6.2f}s")
