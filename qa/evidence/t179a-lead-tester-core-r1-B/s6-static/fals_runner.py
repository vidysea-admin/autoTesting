"""Run one pytest node id in-process and print which autotester it imported. argv: <copy-root> <nodeid>"""
import sys
import autotester
print("autotester.__file__ =", autotester.__file__)
import pytest
root, node = sys.argv[1], sys.argv[2]
assert root.replace("\\", "/").lower() in autotester.__file__.replace("\\", "/").lower(), "imported from the wrong tree"
sys.exit(pytest.main(["--rootdir", root, "-c", root + "/pyproject.toml", "-p", "no:cacheprovider", node]))
