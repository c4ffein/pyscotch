#!/usr/bin/env python3
"""mkdiff.py OUT.diff  -- reads a JSON spec on stdin: {"base": "<git rev>", "files": {path: [[old,new],...]}}
Produces a unified diff of the edits against the given revision of $WORK/scotch."""
import json, subprocess, sys, os, tempfile
WORK=os.environ['WORK']; spec=json.load(sys.stdin); out=sys.argv[1]; base=spec.get('base','base-combined')
chunks=[]
for path, pairs in spec['files'].items():
    orig=subprocess.run(['git','-C',WORK+'/scotch','show',f'{base}:{path}'],capture_output=True,text=True,check=True).stdout
    new=orig
    for a,b in pairs:
        assert new.count(a)==1, (path, a[:60], new.count(a))
        new=new.replace(a,b)
    with tempfile.NamedTemporaryFile('w',delete=False,suffix='.c') as f1, tempfile.NamedTemporaryFile('w',delete=False,suffix='.c') as f2:
        f1.write(orig); f2.write(new); n1=f1.name; n2=f2.name
    d=subprocess.run(['diff','-u','--label','a/'+path,'--label','b/'+path,n1,n2],capture_output=True,text=True).stdout
    os.unlink(n1); os.unlink(n2); chunks.append(d)
open(out,'w').write(''.join(chunks)); print(out, sum(c.count('\n') for c in chunks), 'lines')
