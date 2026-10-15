"""One explicitly authorized existing-model Gemini fallback readiness challenge."""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from autotester.core.env import load_repo_env
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.gemini import DEFAULT_MODEL
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.vision_probe import probe_vision

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent/'gemini-fallback'
OUT.mkdir()
load_repo_env(ROOT)
environment = json.loads((OUT.parent/'environment-corrected/environment.json').read_bytes())
engine = Path(environment['tesseract_executable'])
assert hashlib.sha256(engine.read_bytes()).hexdigest() == environment['executable_sha256']
data = engine.parent/'tessdata/eng.traineddata'
assert hashlib.sha256(data.read_bytes()).hexdigest() == environment['english_data_sha256']
os.environ['PATH'] = str(engine.parent)+os.pathsep+os.environ.get('PATH','')
os.environ['TESSDATA_PREFIX'] = str(data.parent)
model = 'gemini/'+DEFAULT_MODEL
row = {'model':model,'model_source':'autotester.providers.gemini.DEFAULT_MODEL',
       'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'started_at':datetime.now(UTC).isoformat(),'environment':environment,
       'limits':'One challenge only; <=2 physical calls/shared45s including repair, no generation-token cap or hard cancellation guarantee.'}
started = time.monotonic()
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    with attempt_budget(2,wall_clock_s=45) as budget:
        try:
            result = probe_vision(LiteLLMProvider(model=model))
        except AttemptBudgetExhausted as exc:
            result = getattr(exc,'probe_result',None)
            row['global_budget_exhausted'] = True
        except Exception as exc:
            result = None
            row['safe_error_category'] = type(exc).__name__
        row['physical_attempts'] = [a.model_dump(mode='json') for a in budget.attempts]
if result is not None:
    row['result'] = result.model_dump(mode='json')
    row['status'],row['reason'] = result.status,result.reason
    row['validated_output_sha256'] = (hashlib.sha256(result.observed.model_dump_json().encode()).hexdigest()
                                      if result.observed is not None else None)
    if result.capability:
        (OUT/'capability.json').write_bytes(result.capability.model_dump_json(indent=2).encode())
else:
    row['status'],row['reason'] = 'inconclusive','budget_exhausted_or_runner_failure'
row['duration_s'],row['ended_at'] = time.monotonic()-started,datetime.now(UTC).isoformat()
(OUT/'receipt.json').write_bytes(json.dumps(row,indent=2).encode())
print(model,row['status'],row['reason'],'physical_attempts',len(row['physical_attempts']),flush=True)
print('RECEIPT',str(OUT/'receipt.json'),flush=True)
