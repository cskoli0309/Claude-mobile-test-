# Renders the "lettering writes itself" passes: time-remaps the process timelapses
# so each word finishes as the voice says it, removes the tracing reference, and
# applies an eased camera. Writes raw rgb24 1080x1920 frames to stdout.
# Usage: python3 writing.py <pass-name> <P1.mov> <P2.mov>
import sys, subprocess, numpy as np
from PIL import Image
from degrey import clean, is_flash
W,H,FPS=1080,1920,30
P2OFF=58.0   # combined source time = P1 time, then P2 time + 58s
# combined-source time at which each word is finished being painted
SRC={'start':2.5,'Break':18,'pattern':27,'today':39,'loop':56,'will':62.2,'repeat':75.5,'tomorrow':98.2}
WORDY={'Break':690,'pattern':830,'today':930,'loop':1070,'will':1070,'repeat':1170,'tomorrow':1320}
# (out_seconds, word finished) from the voiceover transcript, per pass; plus frames and camera keys (t,z,cy)
PASSES={
 'p1':dict(n=89, keys=[(0,'start'),(0.6,'Break'),(0.98,'pattern'),(1.30,'today'),(2.02,'loop'),(2.22,'will'),(2.50,'repeat'),(2.96,'tomorrow')],
           cam=[(0,1.0,960),(2.96,1.06,960)]),
 'p2':dict(n=92, keys=[(0,'start'),(0.68,'Break'),(1.18,'pattern'),(1.50,'today'),(2.22,'loop'),(2.42,'will'),(2.68,'repeat'),(3.06,'tomorrow')],
           cam=[(0,1.8,690),(0.55,1.8,690),(0.9,1.8,830),(1.25,1.8,930),(1.75,1.7,1070),(2.35,1.7,1170),(2.72,1.6,1320),(3.06,1.5,1300)]),
 'p3':dict(n=90, keys=[(0,'start'),(0.6,'start'),(1.22,'Break'),(1.72,'pattern'),(2.06,'today'),(2.80,'loop'),(3.0,'will')],
           cam=[(0,1.0,960),(3.0,1.18,960)]),
}
def interp(keys,t):
    for (t0,a),(t1,b) in zip(keys,keys[1:]):
        if t<=t1:
            p=0 if t1==t0 else (t-t0)/(t1-t0); return a+(b-a)*p
    return keys[-1][1]
def ease(keys,t):  # smoothstep between camera keys
    for (t0,*a),(t1,*b) in zip(keys,keys[1:]):
        if t<=t1:
            p=0 if t1==t0 else (t-t0)/(t1-t0); p=p*p*(3-2*p)
            return [x+(y-x)*p for x,y in zip(a,b)]
    return keys[-1][1:]
def decoder(path,ss):
    pr=subprocess.Popen(["ffmpeg","-v","error","-ss",str(ss),"-i",path,"-vf",
        f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
        "-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
    t=ss
    while True:
        b=pr.stdout.read(W*H*3)
        if len(b)<W*H*3: return
        yield t,np.frombuffer(b,np.uint8).reshape(H,W,3); t+=1/FPS
def source(p1,p2):
    for t,f in decoder(p1,SRC['start']): yield t,f
    for t,f in decoder(p2,0): yield t+P2OFF,f
name,p1,p2=sys.argv[1:4]; P=PASSES[name]
want=[interp([(a,SRC[w]) for a,w in P['keys']],i/FPS) for i in range(P['n'])]
src=source(p1,p2); cur=None; last=None; out=sys.stdout.buffer
st,sf=next(src)
for i,tw in enumerate(want):
    while st<tw:
        try: st,sf=next(src)
        except StopIteration: break
    if cur is None or cur[0]!=st:
        f=sf if not is_flash(sf) or last is None else last
        cur=(st,clean(f)); last=f
    z,cy=ease(P['cam'],i/FPS)
    w,h=W/z,H/z; cy=min(max(cy,h/2),H-h/2); x0=(W-w)/2; y0=cy-h/2
    img=Image.fromarray(cur[1]).resize((W,H),Image.BICUBIC,box=(x0,y0,x0+w,y0+h))
    out.write(img.tobytes())
