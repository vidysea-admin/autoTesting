"""a5: floorless short .env values -- which ordinary prompts do they refuse? Numbers."""
import re
from h import run, outcome

ordinary = [
    "Grade this test run: the login page shows the dashboard after the user signs in.",
    "Step 3 clicked the Submit button on https://app.example.com/login and saw 2 errors.",
    "Does the page show 12 programs for the Computer Science course in 2026? Answer yes or no.",
    "The student profile page lists name, email, grade 10, and school city.",
    "Compare the expected result with the screenshot and report any visible defect.",
]
SCHEMA_SUFFIX_NOTE = "json strategy appends the pydantic JSON Schema text (letters, braces, quotes, digits)"
vals = ["1", "0", "a", "e", "ab", "th", "the", "on", "no", "yes", "id", "10", "dev", "true", "ok", "root", "8000", "admin", "x9"]
print(f"{'value':8} " + " ".join(f"P{i+1}" for i in range(len(ordinary))) + "   json-strategy(P1)")
tot = 0
for v in vals:
    row = []
    for p in ordinary:
        r = run(f"SOME_ENV={v}\n", p)
        row.append("REF" if not r["fake"].calls else "ok ")
        tot += 1
    r = run(f"SOME_ENV={v}\n", ordinary[0], strategy="json")
    print(f"{v!r:8} " + " ".join(f"{x:3}" for x in row) + f"   {'REF' if not r['fake'].calls else 'ok'}")

print("\n== folded check on short values: does a 2-char secret match inside ordinary words? (MIN_FOLDED_LEN=8 gate) ==")
from autotester.core.redact import assert_no_raw_secrets, fold_credential
for v in ["a-b", "Q-9", "x.y.z", "a b c d", "ab-cd-ef", "a-b-c-d-e-f-g", "the-end", "go-to-it-now"]:
    folded = fold_credential(v)
    hits = []
    for p in ordinary:
        try:
            assert_no_raw_secrets(p, [v]); hits.append("ok")
        except ValueError:
            hits.append("REF")
    print(f"  {v!r:18} folded={folded!r:14} (len {len(folded)}) {hits}")
print("\n== realistic .env keys of this repo (from .env.example) vs ordinary prompts a stage would send ==")
env = ("PATHLYNKS_COUNSELLOR_LOGIN_URL=https://pathlynks.example.com/counsellor/login\n"
       "PATHLYNKS_USER_LOGIN_URL=https://pathlynks.example.com/login\n"
       "PATHLYNKS_COUNSELLOR_EMAIL=counsellor@example.com\n"
       "PATHLYNKS_MONGO_URI=mongodb://localhost:27017/pathlynks\n")
for label, p in [("page URL = counsellor login URL", "The browser is at https://pathlynks.example.com/counsellor/login and shows a sign-in form."),
                 ("page URL = user login URL (PUBLIC key)", "The browser is at https://pathlynks.example.com/login and shows a sign-in form."),
                 ("logged-in email shown on page", "The header shows counsellor@example.com as the signed-in user."),
                 ("URL w/o scheme, folded", "Open pathlynks.example.com/counsellor/login now.")]:
    r = run(env, p); print(f"  {label:42} {outcome(r)}")
