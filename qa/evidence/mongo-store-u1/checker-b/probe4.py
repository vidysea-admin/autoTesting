import sys, ast
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
from test_mongo_guard_scan import _reasons

snips = {
 "concat dynamic import": "import importlib\nm = importlib.import_module('py' + 'mongo')\n",
 "variable dynamic import": "import importlib\nn = 'pymongo'\nm = importlib.import_module(n)\n",
 "getattr import_module": "import importlib\nm = getattr(importlib, 'import_module')('pymongo')\n",
 "exec import": "exec('import pymongo')\n",
 "sys.modules after dyn": "import sys\nm = sys.modules.get('pymongo')\n",
 "MongoClient via alias var": "import importlib\nm = importlib.import_module('x' and 'pymongo')\nC = m.MongoClient\nC('mongodb://h')\n",
 "subscript on client not bound by direct call": "def f(c):\n    return c['other']['x']\n",
 "client bound via attr": "class A:\n    def __init__(self):\n        self.c = MongoClient('x')\n    def g(self):\n        return self.c['other']\n",
 "from pymongo.mongo_client import MongoClient": "from pymongo.mongo_client import MongoClient as M\nM('x')\n",
 "gridfs bare": "import gridfs\n",
 "motor": "import motor.motor_asyncio\n",
 "mongoengine": "import mongoengine\n",
 "subprocess mongosh": "import subprocess\nsubprocess.run(['mongosh', 'mongodb://h/other', '--eval', 'db.x.drop()'])\n",
}
for k, v in snips.items():
    print(f"{k:50} -> {'FLAGGED ' + str(_reasons(ast.parse(v))) if _reasons(ast.parse(v)) else 'not flagged'}")
