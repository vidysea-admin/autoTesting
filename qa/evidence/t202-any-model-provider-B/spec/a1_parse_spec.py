import sys, time
sys.path.insert(0, "D:/autoTesting/.worktrees/t202-any-model-provider/src")
import autotester.providers as P
from autotester.providers.base import ProviderError

cases = {
 "empty-model": "litellm:", "spaces-model": "litellm:   ", "a:b:c": "litellm:a:b:c",
 "double colon": "litellm::x", ":x": ":x", "empty": "", "bare litellm": "litellm",
 "case LiteLLM:x": "LiteLLM:x", "leading space": " litellm:x",
 "trailing nl": "litellm:gpt-4\n", "trailing tab": "litellm:gpt-4\t", "NUL": "litellm:gpt-4\x00",
 "nbsp inside": "litellm:gpt\u00a04", "nbsp trailing": "litellm:gpt-4\u00a0",
 "u2028 trailing": "litellm:gpt-4\u2028", "u2028 inside": "litellm:gp\u2028t",
 "zwsp inside": "litellm:gpt\u200b4", "zwsp trailing": "litellm:gpt-4\u200b",
 "vertex @": "litellm:vertex_ai/gemini-1.5-pro@001",
 "ollama tag": "litellm:ollama/llama3:8b",
 "comma model": "litellm:openai/gpt-4o,gemini",
 "comma list lit first": "litellm,gemini", "comma list w model": "litellm,gemini:x",
 "vision list": "gemini,anthropic", "vision list sp": "gemini, anthropic",
 "trailing comma": "gemini,", "only comma": ",",
 "traversal": "litellm:../..", "secret placeholder": "litellm:{{SECRET:KEY}}",
 "script": "litellm:<script>alert(1)</script>", "pct s": "litellm:%s", "fmt {0}": "litellm:{0}",
 "dq": 'litellm:a"b', "sq": "litellm:a'b",
 "url": "litellm:https://h/v1", "url noauth": "litellm:openai/x://y",
 "unknown id echo?": "sk-abc123", "unknown id w model": "sk-abc123:model",
 "mock:model": "mock:abc", "gemini:model": "gemini:gemini-2.5-pro",
 "langchain-fallback:x": "langchain-fallback:x",
 "id with spaces around colon": "litellm : x", "litellm: x y": "litellm: x y",
 "unicode id": "litellm\u00a0:x", "tab in model middle": "litellm:a\tb",
 "model newline middle": "litellm:a\nb", "vt/ff": "litellm:a\x0bb", "u0085": "litellm:a\u0085b",
 "u180e": "litellm:a\u180eb", "u3000": "litellm:a\u3000b", "ufeff": "litellm:a\ufeffb",
 "sk key model": "litellm:sk-live-abc123def456", "key= in model": "litellm:openai/gpt-4o?key=SECRET",
 "id trailing ws in list": "gemini ,anthropic",
}
for name, spec in cases.items():
    try:
        r = P.parse_spec(spec)
        out = f"OK {r!r}"
        pid, opt = r
        # label round-trip
        try:
            lab = P._REGISTRY[pid.split(',')[0]](**opt).label if ',' not in pid else None
        except Exception as e:
            lab = f"ctor-error {type(e).__name__}"
        out += f" | label={lab!r}"
        if lab and lab != spec.strip(): out += "  <-- label != spec.strip()"
    except ProviderError as e:
        msg = str(e)
        out = f"ProviderError: {msg!r}"
        # echo check: any >=3-char token of spec (other than registry ids) appearing in message
        s = spec.strip()
        import re
        for tok in set(re.split(r"[:,\s]+", s)):
            if len(tok) >= 3 and tok in msg and tok not in P._REGISTRY and tok not in ("provider","model","known"):
                out += f"  <-- ECHO of {tok!r}"
    except Exception as e:
        out = f"!! {type(e).__name__}: {e}"
    print(f"{name:28s} {spec[:50]!r:55s} -> {out}")

# long
for n, spec in [("100k model", "litellm:" + "a"*100_000), ("1MB model", "litellm:" + "a"*1_000_000),
                ("1MB spaces", "litellm:" + " "*1_000_000 + "x"), ("1MB colons", ":"*1_000_000),
                ("1MB commas", "," * 1_000_000), ("1MB unknown id", "z"*1_000_000),
                ("1MB 'a b' ", "litellm:" + "a "*500_000), ("1MB unicode ws", "litellm:" + "\u00a0"*1_000_000 + "x"),
                ("1MB id commas gemini", ",".join(["gemini"]*150_000))]:
    t = time.perf_counter()
    try: r = P.parse_spec(spec); o = f"OK len={len(str(r))}"
    except ProviderError as e: o = f"ProviderError len(msg)={len(str(e))}"
    print(f"{n:28s} {time.perf_counter()-t:.4f}s {o}")
