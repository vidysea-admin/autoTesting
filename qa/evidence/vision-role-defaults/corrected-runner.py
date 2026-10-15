"""One authorized live neutral-only probe burst; no application source changes."""
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
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.ollama_cloud import DEEPSEEK, GLM
from autotester.providers.vision_probe import probe_vision

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "environment-corrected"
OUT.mkdir()
load_repo_env(ROOT)
identity = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert identity == '24f7cb93ef9ada736e616a787c93d6539fe6485d'

import shutil
from tempfile import TemporaryDirectory
from autotester.core.image_privacy import sanitized_images
from autotester.providers.vision_probe import _new_challenges
engine = ROOT/'.work/tools/tesseract-5.5.3/tesseract.exe'
data = engine.parent/'tessdata/eng.traineddata'
assert engine.is_file() and data.is_file()
setup = {'scope':'process only; no global environment mutation',
         'tesseract_executable':str(engine),'executable_sha256':hashlib.sha256(engine.read_bytes()).hexdigest(),
         'english_data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
         'original_discoverable':shutil.which('tesseract') is not None}
with TemporaryDirectory(prefix='neutral-sanitation-diagnosis-') as temporary:
    images,_ = _new_challenges(Path(temporary))
    with sanitized_images([images[0]]) as batch:
        setup['original_sanitation']={'withheld':batch.withheld,'reasons':batch.reasons}
    os.environ['PATH']=str(engine.parent)+os.pathsep+os.environ.get('PATH','')
    os.environ['TESSDATA_PREFIX']=str(data.parent)
    assert Path(shutil.which('tesseract')).resolve()==engine.resolve()
    setup['version']=subprocess.run([str(engine),'--version'],capture_output=True,text=True,timeout=10,check=True).stdout.splitlines()[0]
    with sanitized_images(images) as batch:
        setup['corrected_sanitation']={'withheld':batch.withheld,'reasons':batch.reasons,'included':len(batch.paths)}
(OUT/'environment.json').write_bytes(json.dumps(setup,indent=2).encode())
assert setup['corrected_sanitation']['withheld']==0, 'corrected sanitation remains withheld; no API call'

source_paths = ['src/autotester/providers/vision_probe.py',
                'src/autotester/providers/litellm_provider.py',
                'src/autotester/providers/attempts.py',
                'src/autotester/core/image_privacy.py',
                'src/autotester/schema/vision_probe.py',
                'src/autotester/schema/video_frames.py',
                'src/autotester/skills/vision-probe/SKILL.md','uv.lock']
receipt = {'source_sha':identity, 'started_at':datetime.now(UTC).isoformat(),
           'source_fingerprints':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
           'environment_receipt':'environment.json', 'results':[], 'limits':'Neutral geometry only; two calls/45s per model and outer6calls/135s. No generation-token cap or hard cancellation guarantee. No defaults/project changes. API/SDK diagnostic streams discarded in memory; no raw vendor error/credential logging.'}

def save():
    (OUT/'receipt.json').write_bytes(json.dumps(receipt,indent=2).encode())

def run(model):
    started = time.monotonic()
    provider = LiteLLMProvider(model=model)
    row = {'model':model, 'started_at':datetime.now(UTC).isoformat()}
    # SDK diagnostics can contain vendor responses; retain only typed safe results.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            result = probe_vision(provider)
        except AttemptBudgetExhausted as exc:
            result = getattr(exc,'probe_result',None)
            row['global_budget_exhausted'] = True
        except Exception as exc:
            result = None
            row['status'], row['reason'] = 'inconclusive','runner_error_'+type(exc).__name__
    if result is not None:
        row['result'] = result.model_dump(mode='json')
        row['status'], row['reason'] = result.status,result.reason
        row['fixture_sha256'] = result.capability.fixture_sha256 if result.capability else None
        row['validated_output_sha256'] = (hashlib.sha256(result.observed.model_dump_json().encode()).hexdigest()
                                           if result.observed is not None else None)
        row['endpoint_sha256'] = result.endpoint_sha256
    else:
        row.setdefault('status','inconclusive'); row.setdefault('reason','budget_exhausted')
    row['ended_at'], row['duration_s'] = datetime.now(UTC).isoformat(),time.monotonic()-started
    receipt['results'].append(row); save()
    print(model,row['status'],row['reason'],flush=True)
    return row

save()
with attempt_budget(6,wall_clock_s=135) as global_budget:
    first = run(GLM)
    blocked = {'image_preparation_or_sanitation_failed','provider_error','budget_exhausted'}
    if first['reason'] not in blocked and not first.get('global_budget_exhausted'):
        second = run(DEEPSEEK)
    else:
        second = None
        receipt['not_attempted'] = [DEEPSEEK,'gemini/gemini-3.6-flash']
        receipt['stop_reason'] = 'shared_preparation_privacy_or_budget_failure; no fallback eligible'
    eligible = {'provider_unavailable','visual_answer_mismatch','physical_transport_unproven'}
    if second and all(r['reason'] in eligible for r in (first,second)):
        run('gemini/gemini-3.6-flash')
    receipt['physical_attempts'] = [a.model_dump(mode='json') for a in global_budget.attempts]
receipt['ended_at'] = datetime.now(UTC).isoformat(); save()
print('RECEIPT',str(OUT/'receipt.json'),'physical_attempts',len(receipt['physical_attempts']),flush=True)
