# Wedge quad mesh in Scotch mesh format (elements first, base 0): column x has h(x) rows of quads, decreasing with x.
import sys
W, H = int(sys.argv[1]), int(sys.argv[2])
cols = [max(1, H - (x*H)//W) for x in range(W)]
nodeid = {}; elems = []
for x in range(W):
    for y in range(cols[x]):
        q = [(x,y),(x+1,y),(x,y+1),(x+1,y+1)]
        for n in q:
            if n not in nodeid: nodeid[n] = len(nodeid)
        elems.append([nodeid[n] for n in q])
ne, nn = len(elems), len(nodeid)
adj = [[] for _ in range(nn)]
for e, q in enumerate(elems):
    for n in q: adj[n].append(e)
with open(sys.argv[3],'w') as f:
    f.write("1\n%d\t%d\t%d\n0\t%d\t000\n" % (ne, nn, 8*ne, ne))
    for q in elems: f.write("4\t" + "\t".join(str(n) for n in q) + "\n")
    for n in range(nn): f.write("%d\t" % len(adj[n]) + "\t".join(str(e) for e in adj[n]) + "\n")
print("wedge: ne=%d nn=%d" % (ne, nn))
