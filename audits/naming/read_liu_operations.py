"""Extract the displayed Seitz representatives from Liu SM Tables S3--S9.

The PDF's displayed row numbers anchor the nearby stacked numerator/denominator
operations. Every extracted operation is subsequently checked against its
space group after a single exact origin transformation.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
text = (ROOT/'tmp/naming_rule/liu_supplement.txt').read_text()
start=text.index('Table S3:')
text = text[start:text.index('II. SITE-SYMMETRY',start)]
lines = text.splitlines()
anchors=[]
for i,line in enumerate(lines):
    m=re.match(r'^\s*(\d+)\s+([PABCIFR][^\s]*)(?:\s|$)',line)
    if m: anchors.append((i,int(m[1])))
assert sorted(n for _,n in anchors)==list(range(1,231)),sorted(set(range(1,231))-{n for _,n in anchors})
out={str(n):[] for _,n in anchors}
for i,line in enumerate(lines):
    ops=re.findall(r'\{([^|{}]+)\|([^{}]+)\}',line)
    if not ops: continue
    distances=sorted((abs(i-j),n) for j,n in anchors)
    assert distances[0][0] <= 3,(i,line,distances[:2])
    n=distances[0][1]
    if distances[0][0] == distances[1][0]:
        # Numerators precede the centred row number; denominators follow it.
        tied={n for d,n in distances if d==distances[0][0]}
        n=min(tied) if ops[0][0].strip().startswith(('m','𝑚')) else max(tied)
    for rotation,translation in ops:
        rotation=rotation.strip().replace('𝑚','m').replace('−','-')
        values=translation.split()
        if values==['0']: values=['0','0','0']
        assert len(values)==3,(n,values)
        out[str(n)].append({'rotation_symbol':rotation,'translation':values})
assert all(out.values())
target=ROOT/'audits/naming/liu_operations.json'
target.write_text(json.dumps(out,indent=2)+'\n')
print('Extracted',sum(map(len,out.values())),'operations for',len(out),'parents')
