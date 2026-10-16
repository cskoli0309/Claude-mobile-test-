import sys, numpy as np
def binary_dilation(m,iterations=1):
    for _ in range(iterations):
        d=m.copy(); d[1:]|=m[:-1]; d[:-1]|=m[1:]; d[:,1:]|=m[:,:-1]; d[:,:-1]|=m[:,1:]; m=d
    return m
W,H=1080,1920; n=W*H*3
rng=np.random.default_rng(1)
bg=np.array([28,26,24],np.int16)
def clean(f):
    a=f.astype(np.int16)
    mx=a.max(-1); mn=a.min(-1)
    m=(mx-mn<24)&(mx>38)
    box=np.zeros_like(m); box[520:1460,180:920]=True; m&=box
    m=binary_dilation(m,iterations=2)
    # keep anything clearly blue
    blue=(a[...,2]-a[...,0]>40)
    m&=~blue
    out=a.copy()
    out[m]=bg+rng.integers(-3,4,(m.sum(),1))
    return out.clip(0,255).astype(np.uint8)
if __name__=='__main__':
    src=sys.stdin.buffer; dst=sys.stdout.buffer
    while True:
        b=src.read(n)
        if len(b)<n: break
        dst.write(clean(np.frombuffer(b,np.uint8).reshape(H,W,3)).tobytes())
