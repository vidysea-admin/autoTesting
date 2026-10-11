import sys
copy=sys.argv[1]; sys.path.insert(0, copy+"/src")
import pytest, autotester
print("parent imports", autotester.__file__)
sys.exit(pytest.main(["-p","no:xdist","-p","no:cacheprovider","-o","addopts=","--rootdir",copy,"-c",copy+"/pyproject.toml",*sys.argv[2:]]))
