#!/usr/bin/env python3
"""
Pro Autopilot for Puzzle-71 (CPU edition)
Автор: ChatGPT-o3 2025-12-24
Отладка: macOS, только CPU.
Работает циклом «маска → поиск → статистика → фиксация позиций».
"""

import subprocess, re, json, math, time, os
from pathlib import Path
from collections import Counter, defaultdict

# ───────────────────────────────── CONFIG ─────────────────────────────────
TARGET = "1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
VANITY = "./VanitySearch"
BITR   = "71"
THREAD = "4"
ITER_S = 40           # секунд поиск на одном шаге
MIN_CONF = 0.08       # 8 % порог фиксации
MAX_IT = 15
RESULTS = Path("runs"); RESULTS.mkdir(exist_ok=True)
PUZ_START = 2**70; PUZ_END = 2**71-1; PUZ_SIZE = PUZ_END-PUZ_START

# старт: лучший 10-символ. ключ 0x7360CD4B5AEFB6C9EA ≈ 80.2783 %
BEST_HEX = int("7360CD4B5AEFB6C9EA",16)
BEST_PCT = (BEST_HEX-PUZ_START)/PUZ_SIZE*100

# ───────────────────────────── helpers ───────────────────────────────

def run_vs(segfile:str, mask:str, sec:int) -> str:
    cmd=[VANITY,"-seg",segfile,"-bits",BITR,"-t",THREAD,mask,"-n"]
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        out,_=proc.communicate(timeout=sec)
    except subprocess.TimeoutExpired:
        proc.kill(); out,_=proc.communicate()
    return out

def pub_from_output(buf:str):
    return re.findall(r"^PubAddress:\s+(1[0-9A-Za-z]{25,34})",buf,re.MULTILINE)

class Heat:
    def __init__(s): s.stat=defaultdict(Counter)
    def add(s,addr):
        for i,c in enumerate(addr):
            if i<len(TARGET) and c==TARGET[i]: s.stat[i][c]+=1
    def best(s,taken:set):
        total=sum(s.stat[0].values()) or 1
        best=(-1,'',0.0)
        for i,cnt in s.stat.items():
            if i in taken: continue
            ch,n=cnt.most_common(1)[0]; conf=n/total
            if conf>=MIN_CONF and conf>best[2]: best=(i,ch,conf)
        return best if best[0]!=-1 else None

def mk_segments(pct:float,span=0.01,n=8):
    lo=max(0,pct-span); hi=min(100,pct+span); step=(hi-lo)/n
    segs=[]
    for i in range(n): segs.append((lo+i*step,lo+(i+1)*step,f"opt_{i+1}"))
    return segs

# ───────────────────────────── main loop ──────────────────────────────
mask="1PWo*"; fixed=set(); segs=mk_segments(BEST_PCT)
for it in range(1,MAX_IT+1):
    segfile=RESULTS/f"seg_{it}.txt"
    with open(segfile,'w') as f:
        for a,b,n in segs: f.write(f"{a:.12f} {b:.12f} up {n}\n")
    buf=run_vs(str(segfile),mask,ITER_S)
    addrs=pub_from_output(buf)
    with open(RESULTS/f"out_{it}.txt","w") as w: w.write(buf)
    if not addrs:
        print(f"Iter {it}: 0 addr → stop"); break
    heat=Heat(); [heat.add(a) for a in addrs]
    best=heat.best(fixed)
    if not best: print("No new positions"); break
    pos,ch,conf=best; fixed.add(pos)
    print(f"Iter {it}: fix pos{pos}='{ch}' conf={conf:.2%}  addr={len(addrs)}")
    m=list(mask.ljust(len(TARGET),'*')); m[pos]=ch; mask=''.join(m)
    if it%2==0: segs=mk_segments(BEST_PCT,span=0.005)
print("Final mask:",mask)

