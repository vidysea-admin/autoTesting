import base64,io
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
