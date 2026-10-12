import os, tempfile
from pathlib import Path
import autotester
assert os.environ["H_EXPECT"] in autotester.__file__
from autotester.delivery.inbox import DeliveryLog, delivery_key
from autotester.schema.delivery import DeliveryChannel
d = Path(tempfile.mkdtemp(dir=os.environ["H_TMP"])); log = DeliveryLog(d); log.records_dir.mkdir(parents=True)
k = delivery_key("run-1", DeliveryChannel.EMAIL, "alice")
(log.records_dir / f"{k}.01.02.json").write_text("{}", encoding="utf-8")
print("for_key:", len(log.records_for_key(k)))
try: print("for_run:", len(log.records_for_run("run-1")))
except Exception as e: print("for_run raised", type(e).__name__)
