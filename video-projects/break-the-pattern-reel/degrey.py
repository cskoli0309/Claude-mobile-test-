# Removes the grey tracing-reference layer from the process timelapse and
# replaces flash frames (canvas fills, menu flashes) with the last clean frame.
# Usage: ffmpeg ... -f rawvideo -pix_fmt rgb24 - | python3 degrey.py [--keep-grey] | ffmpeg ...
import sys, numpy as np
W,H=1080,1920; n=W*H*3
rng=np.random.default_rng(1)
bg=np.array([28,26,24],np.int16)
def dilate(m,it):
    for _ in range(it):
        d=m.copy(); d[1:]|=m[:-1]; d[:-1]|=m[1:]; d[:,1:]|=m[:,:-1]; d[:,:-1]|=m[:,1:]; m=d
    return m
def clean(f):
    a=f.astype(np.int16)
    mx=a.max(-1); mn=a.min(-1)
    m=(mx-mn<24)&(mx>38)
    box=np.zeros_like(m); box[520:1460,180:920]=True; m&=box
    m=dilate(m,2) & ~(a[...,2]-a[...,0]>40)
    a[m]=bg+rng.integers(-3,4,(m.sum(),1))
    return a.clip(0,255).astype(np.uint8)
def is_flash(f):
    s=f[::8,::8].astype(np.int16)
    return s[...,2].mean()>120 or s.mean()>90
if __name__=='__main__':
  keep='--keep-grey' in sys.argv
  src=sys.stdin.buffer; dst=sys.stdout.buffer; last=None
  while True:
      b=src.read(n)
      if len(b)<n: break
      f=np.frombuffer(b,np.uint8).reshape(H,W,3)
      if is_flash(f) and last is not None: out=last
      else: out=f if keep else clean(f)
      last=out; dst.write(out.tobytes())
