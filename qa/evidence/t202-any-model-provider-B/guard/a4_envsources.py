"""a4: where do the secret values come from, and which are missed / over-included?"""
import os, tempfile
from pathlib import Path
from h import run, outcome, where_leaked

PRE = "Grade this run: "
print("== exported (process-env) secrets NOT in the vendor-key list, not in .env ==")
AWS = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
for name, val in [("AWS_SECRET_ACCESS_KEY", AWS), ("AZURE_API_KEY", "az-9f8e7d6c5b4a39281706"),
                  ("MISTRAL_API_KEY", "mi-1a2b3c4d5e6f7a8b9c0d"), ("GROQ_API_KEY", "gsk_Abc123Def456Ghi789"),
                  ("HF_TOKEN", "hf_AbCdEfGhIjKlMnOpQrSt"), ("OPENROUTER_API_KEY", "sk-or-v1-abcdef1234567890"),
                  ("DEEPSEEK_API_KEY", "ds-abcdef1234567890xx"), ("COHERE_API_KEY", "co-abcdef1234567890xx"),
                  ("AZURE_API_BASE", "https://x.openai.azure.com")]:
    r = run(None, PRE + val, exports={name: val})
    print(f"  {name:22} {outcome(r):22} leak={where_leaked(r, val)}")
print("  control: listed names")
for name in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "LITELLM_API_KEY"]:
    r = run(None, PRE + "secretvalue-123456", exports={name: "secretvalue-123456"})
    print(f"  {name:22} {outcome(r):22}")

print("== same names but ALSO in the repo-root .env (load_repo_env path) ==")
r = run("AZURE_API_KEY=az-9f8e7d6c5b4a39281706\n", PRE + "az-9f8e7d6c5b4a39281706"); print("  AZURE in .env:", outcome(r))

print("== .env parse shapes: does the value the provider guards equal what a human thinks is the secret? ==")
cases = {
    "export prefix": ("export K=Ab3dE9xYz1\n", "Ab3dE9xYz1"),
    "double-quoted": ('K="Ab3dE9 xYz1"\n', "Ab3dE9 xYz1"),
    "single-quoted": ("K='Ab3dE9xYz1'\n", "Ab3dE9xYz1"),
    "hash no space": ("K=Ab3dE9#xYz1\n", "Ab3dE9#xYz1"),
    "hash w/ space comment": ("K=Ab3dE9xYz1 # comment\n", "Ab3dE9xYz1"),
    "interpolation ${A}": ("A=Base99xYz\nK=${A}suffix1\n", "Base99xYzsuffix1"),
    "interpolation literal ${A} (raw text a user may type)": ("A=Base99xYz\nK=${A}suffix1\n", "${A}suffix1"),
    "CRLF line ends": ("K=Ab3dE9xYz1\r\n", "Ab3dE9xYz1"),
    "BOM first line": ("\ufeffK=Ab3dE9xYz1\n", "Ab3dE9xYz1"),
    "empty value": ("K=\n", ""),
}
for name, (envtxt, secret_in_prompt) in cases.items():
    if not secret_in_prompt:
        continue
    r = run(envtxt, PRE + secret_in_prompt)
    print(f"  {name:55} {outcome(r)}")

print("== multi-line secret (PEM-like) in quoted .env value; prompt carries ONE line ==")
pem = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7\nVJTUt9Us8cKjMzEfYyjiWA4R4/M2bS1GB4t7NXp98C3SC6dVMvDu\n-----END PRIVATE KEY-----"
line = "VJTUt9Us8cKjMzEfYyjiWA4R4/M2bS1GB4t7NXp98C3SC6dVMvDu"
r = run(f'K="{pem}"\n', PRE + line); print("  one 52-char line of the key:", outcome(r), "leak=", where_leaked(r, line))
r = run(f'K="{pem}"\n', PRE + pem); print("  whole PEM:", outcome(r))
r = run(f'K="{pem}"\n', PRE + pem.replace("\n", " ")); print("  whole PEM, newlines->space:", outcome(r))

print("== whitespace-only / junk values (DoS?) ==")
for label, envtxt in [("K=' ' (single space)", "K=' '\n"), ('K="\\n"', 'K="\\n"\n'), ("K='x'", "K='x'\n")]:
    r = run(envtxt, "An ordinary prompt with spaces and an x"); print(f"  {label:26} {outcome(r)}")

print("== unreadable / odd .env files ==")
r = run(None, PRE + "hello", env_bytes=b"K=\xff\xfe\xfdbad\n"); print("  invalid UTF-8 .env:", outcome(r), "exc=", repr(r["exc"])[:120])
tmp = Path(tempfile.mkdtemp(prefix="t202b-")); (tmp / ".env").mkdir()
os.environ["AUTOTESTER_ROOT"] = str(tmp)
from h import Fake, reply  # noqa
import sys
sys.modules["litellm"] = Fake([reply('{"verdict":"ok"}')])
from autotester.providers.litellm_provider import LiteLLMProvider
from h import Ans
try:
    LiteLLMProvider(model="openai/gpt-4o").judge("hi", Ans); print("  .env is a directory: CALLED")
except BaseException as e:
    print("  .env is a directory:", type(e).__mro__[:3], str(e)[:100], "| is ProviderError:", type(e).__name__ == "ProviderError")
