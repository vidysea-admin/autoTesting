"""What SecretStore.resolve does with a declared credential for the CURRENT page host."""
import autotester
from autotester.browser.secrets import SecretStore
from autotester.schema.enums import WritePolicy
from autotester.schema.project import Project, SecretRef

print("autotester.__file__ =", autotester.__file__)
p = Project(slug="demo", name="Demo", base_url="https://app.example.test",
            allowed_domains=["app.example.test"], write_policy=WritePolicy.READ_ONLY,
            secrets=[SecretRef(key="APP_PASS", domains=["app.example.test"])])
S = SecretStore(p, {"APP_PASS": "CANARY-pw-7f3a9c"})
for page in ["https://app.example.test/login", "https://app.example.test/search?q=x",
             "https://app.example.test/settings/delete-account", "https://sub.app.example.test/x",
             "https://evil.test/", "https://app.example.test@evil.test/", "about:blank", ""]:
    try:
        got = S.resolve("{{SECRET:APP_PASS}}", page)
        print(f"{page!r:55} -> RESOLVED (len {len(got)}, is canary: {got == 'CANARY-pw-7f3a9c'})")
    except Exception as exc:  # noqa: BLE001
        print(f"{page!r:55} -> {type(exc).__name__}")
