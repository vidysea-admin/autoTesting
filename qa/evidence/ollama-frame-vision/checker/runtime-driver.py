import pathlib,shutil,os,subprocess,time,json
r=pathlib.Path.cwd();o=r/'qa/evidence/ollama-frame-vision/checker';c=r/'.work/checker-vision-subject';c.mkdir(exist_ok=True)
for n in ('src','tests','scripts'):shutil.copytree(r/n,c/n,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for n in ('pyproject.toml','uv.lock'):shutil.copy2(r/n,c/n)
env=dict(os.environ,PYTHONPATH=str(c/'src'),PYTHONDONTWRITEBYTECODE='1');py=r.parents[1]/'.venv/Scripts/python.exe'
def run(n,args):
 t=time.monotonic();p=subprocess.run([str(py),'-B',*args],cwd=c,env=env,capture_output=True,timeout=50);(o/(n+'.log')).write_bytes(p.stdout+p.stderr);print(n,p.returncode);return {'name':n,'exit':p.returncode,'duration_s':time.monotonic()-t}
res=[run('preflight',['C:/Users/product/.agents/skills/checker/scripts/review_budget.py','preflight','--root',str(c),'--import-name','autotester','--import-root',str(c/'src'),'--temp-parent',str(c)])];assert res[-1]['exit']==0
probe='''import base64,io
from pathlib import Path
from PIL import Image
import test_video_frames as t
from autotester.providers import video_frames
from autotester.core import image_privacy
from autotester.schema.video_frames import FrameLimits
from autotester.schema.observation import VideoObservation

def test_distinct_colors(monkeypatch,setup):
    colors=[(255,0,0),(0,255,0),(0,0,255)]
    def extract(path,timestamp,output):
        Image.new('RGB',(40,20),colors[int(timestamp)]).save(output,format='PNG');return True
    monkeypatch.setattr(video_frames,'extract_frame',extract)
    calls=[]
    def ocr(path):
        calls.append(path)
        if len(calls)==2:raise ValueError('withhold')
        return t.OCR
    monkeypatch.setattr(image_privacy,'_local_ocr',ocr)
    instance,fake=t.provider(monkeypatch,frame_limits=FrameLimits(max_frames=3))
    result=instance.see_video(Path('synthetic.mp4'),'Observe',VideoObservation)
    parts=fake.calls[0]['messages'][0]['content'];imgs=[x['image_url']['url'] for x in parts if x['type']=='image_url']
    assert [x['text'] for x in parts if x['type']=='text'][1:]==['Frame 0, clip-relative seconds 0.000000','Frame 2, clip-relative seconds 2.000000']
    assert [(f.index,f.timestamp_s,f.status) for f in result.visual_coverage.frames]==[(0,0,'included'),(1,1,'withheld'),(2,2,'included')]
    assert len(imgs)==2
    for url,color in zip(imgs,[colors[0],colors[2]]):
        im=Image.open(io.BytesIO(base64.b64decode(url.split(',')[1])));assert im.getpixel((2,15))==color;assert im.getpixel((2,2))==(0,0,0)
setup=t.setup
'''
(c/'tests/test_checker_distinct.py').write_text(probe)
nodes=['tests/test_checker_distinct.py::test_distinct_colors','tests/test_video_frames.py::test_all_withheld_never_sends_text_only_success','tests/test_video_frames.py::test_prompt_secret_guard_precedes_media_processing','tests/test_video_frames.py::test_repair_and_fallback_obey_shared_physical_budget','tests/test_video_frames.py::test_total_bytes_bound_preserves_partial_coverage','tests/test_video_frames.py::test_invalid_limit_shape_and_transport_failures_retain_evidence','tests/test_video_frames.py::test_unsupported_generation_controls_reject_explicitly','tests/test_video_frames.py::test_real_sanitized_bytes_and_clip_relative_timestamp_payload','tests/test_analyze_video.py::test_the_analysis_is_persisted_not_just_returned']
res.append(run('focused',['-m','pytest',*nodes,'--tb=short','--basetemp',str(c/'tmp-green')]))
assert res[-1]['exit']==0
p=c/'src/autotester/providers/video_frames.py';original=p.read_bytes();old=b'safe = stack.enter_context(sanitized_images([frame]))';assert original.count(old)==1;p.write_bytes(original.replace(old,b"safe = type('Unsafe', (), {'paths': [frame]})()"))
res.append(run('privacy-red',['-m','pytest','tests/test_checker_distinct.py::test_distinct_colors','--tb=short','--basetemp',str(c/'tmp-red')]))
p.write_bytes(original);assert res[-1]['exit']==1
res.append(run('restored',['-m','pytest','tests/test_checker_distinct.py::test_distinct_colors','--tb=short','--basetemp',str(c/'tmp-restored')]))
(o/'runtime.json').write_text(json.dumps(res,indent=2));assert res[-1]['exit']==0
