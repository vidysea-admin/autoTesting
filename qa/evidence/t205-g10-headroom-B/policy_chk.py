from autotester.auth.policy import merge_route_policies, PolicyError, PUBLIC

CAT = {"run.start", "project.view"}
PUB = {"GET /login"}

def t(label, units, routes=None, public=PUB):
    try:
        out = merge_route_policies(units, catalogue=CAT, public_routes=public, routes=routes)
        print(f"{label:62s} MERGED {out}")
    except PolicyError as e:
        print(f"{label:62s} refused: {str(e)[:70]}")
    except Exception as e:
        print(f"{label:62s} {type(e).__name__}: {str(e)[:60]}")

t("dup same route two units", {"a": {"GET /x": ("run.start", "p")}, "b": {"GET /x": ("project.view", "p")}})
t("dup differing method case", {"a": {"GET /x": ("run.start", "p")}, "b": {"get /x": ("project.view", "p")}})
t("dup trailing slash", {"a": {"GET /x": ("run.start", "p")}, "b": {"GET /x/": ("project.view", "p")}})
t("dup path-param renamed", {"a": {"GET /p/{slug}": ("run.start", "p")}, "b": {"GET /p/{id}": ("project.view", "p")}})
t("dup path-param renamed WITH routes given", {"a": {"GET /p/{slug}": ("run.start", "p")}, "b": {"GET /p/{id}": ("project.view", "p")}}, routes={"GET /p/{slug}"})
t("public marker on non-public route", {"a": {"GET /x": PUBLIC}})
t("public in set, claimed by two units", {"a": {"GET /login": PUBLIC}, "b": {"GET /login": ("run.start", "p")}})
t("grant is a list (not tuple)", {"a": {"GET /x": ["run.start", "p"]}})
t("grant is empty string (omission-like)", {"a": {"GET /x": ""}})
t("grant is None", {"a": {"GET /x": None}})
t("grant is 'PUBLIC' uppercase", {"a": {"GET /x": "PUBLIC"}})
t("grant is ('public','x')", {"a": {"GET /x": ("public", "x")}})
t("empty tuple", {"a": {"GET /x": ()}})
t("3-tuple", {"a": {"GET /x": ("run.start", "p", "extra")}})
t("route w/ whitespace variants", {"a": {"GET /x": ("run.start", "p")}, "b": {"GET  /x": ("project.view", "p")}})
t("unit order independence", {"b": {"GET /y": ("run.start", "p")}, "a": {"GET /x": ("run.start", "p")}})
t("units mapping with a non-dict (None)", {"a": None})
t("empty everything", {})
t("public_routes=None-ish (empty) + public grant", {"a": {"GET /login": PUBLIC}}, public=set())
t("catalogue given as str 'run.start' (substring trap)", {"a": {"GET /x": ("run", "p")}})
