import random, string, sys
sys.path.insert(0, r"D:\autoTesting\.worktrees\t209-leak-severity\src")
from autotester.stages.leak_evidence import templatise_url
random.seed(7)
b62 = string.ascii_letters + string.digits
b64u = b62 + "-_"
crock = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
fmts = {
 "nanoid21 (base64url)": lambda: "".join(random.choices(b64u, k=21)),
 "base62-22": lambda: "".join(random.choices(b62, k=22)),
 "cuid2-24 (a-z0-9)": lambda: random.choice(string.ascii_lowercase) + "".join(random.choices(string.ascii_lowercase+string.digits, k=23)),
 "ULID-26": lambda: "".join(random.choices(crock, k=26)),
 "stripe-like cus_+14": lambda: "cus_" + "".join(random.choices(b62, k=14)),
 "objectid-24 hex": lambda: "".join(random.choices("0123456789abcdef", k=24)),
 "uuid4": lambda: __import__("uuid").uuid4().hex[:8]+"-"+__import__("uuid").uuid4().hex[:4]+"-"+"4abc"+"-"+"89ab"+"-"+"0"*12,
}
N = 2000
for name, g in fmts.items():
    kept = sum(1 for _ in range(N) if (lambda i: templatise_url(f"https://a.test/students/{i}") .endswith("/"+i))(g()))
    print(f"{name:24s} raw id kept in url_template: {kept}/{N} = {100*kept/N:.1f}%")
