#!/usr/bin/env python3
"""Analyze list of addresses, compute common positions vs TARGET and suggest new mask.
Usage: analyze_mask.py addr_file [threshold=0.08] [current_mask]
Outputs stats and NEW_MASK line.
"""
import sys, collections
TARGET="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
addr_file=sys.argv[1]
thr=float(sys.argv[2]) if len(sys.argv)>2 else 0.08
cur_mask=list(sys.argv[3]) if len(sys.argv)>3 else list('*'*len(TARGET))
fixed=set(i for i,c in enumerate(cur_mask) if c!='*')
stat=collections.defaultdict(int)
with open(addr_file) as f:
    for line in f:
        a=line.strip().split()[1] if line.startswith('PubAddress') else line.strip()
        if not a.startswith('1'):continue
        for i,ch in enumerate(a):
            if i>=len(TARGET):break
            if ch==TARGET[i]:
                stat[i]+=1
count=sum(1 for _ in open(addr_file))
print(f"Addresses analysed: {count}\n")
best_pos,best_conf,best_char=-1,0,'*'
for i in range(len(TARGET)):
    if i in fixed:continue
    match=stat.get(i,0)
    conf=match/max(count,1)
    if conf>best_conf:
        best_pos,best_conf=i,conf;best_char=TARGET[i]
print("Pos | Conf")
for i in range(len(TARGET)):
    conf=stat.get(i,0)/max(count,1)
    mark='*' if i in fixed else ' '
    print(f"{i:2d}{mark} | {conf:.3f}")
if best_conf>=thr:
    cur_mask[best_pos]=best_char
    print(f"\nNEW_MASK:{''.join(cur_mask)} (fixed pos {best_pos}={best_char}, conf={best_conf:.2%})")
else:
    print("\nNO_CONFIDENT_POSITION")
