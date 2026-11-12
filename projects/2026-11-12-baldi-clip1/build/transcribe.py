import json,sys,wave
import numpy as np
from faster_whisper import WhisperModel
wf=wave.open(sys.argv[1]); a=np.frombuffer(wf.readframes(wf.getnframes()),np.int16).astype(np.float32)/32768
m=WhisperModel("small",device="cpu",compute_type="int8")
segs,_=m.transcribe(a,language="pt",word_timestamps=True)
out=[]
for s in segs:
  print(f"{s.start:6.2f}-{s.end:6.2f} {s.text}")
  for w in s.words: out.append({"w":w.word.strip(),"s":round(w.start,2),"e":round(w.end,2)})
json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False)
