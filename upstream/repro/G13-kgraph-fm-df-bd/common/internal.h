/* Internal-API harness header: mirrors the libscotch include chain */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "module.h"
#include "common.h"
#include "context.h"
#include "gain.h"
#include "fibo.h"
#include "parser.h"
#include "graph.h"
#include "arch.h"
#include "mapping.h"
#include "bgraph.h"
#include "kgraph.h"
#include "kgraph_map_fm.h"
#include "kgraph_map_st.h"
#include "kgraph_map_bd.h"
#include "kgraph_map_df.h"
#include "scotch.h"

/* Build a WxH grid graph into a Graph (opaque SCOTCH_Graph is the same storage) */
static void
mkgrid (Graph * const g, const int w, const int h, const Gnum * const velotab)
{
  Gnum n = (Gnum) w * h, e = 0, i;
  Gnum * vt = malloc ((n + 1) * sizeof (Gnum));
  Gnum * et = malloc (4 * n * sizeof (Gnum));
  for (i = 0; i < n; i ++) {
    int x = i % w, y = i / w;
    vt[i] = e;
    if (x > 0)     et[e ++] = i - 1;
    if (x < w - 1) et[e ++] = i + 1;
    if (y > 0)     et[e ++] = i - w;
    if (y < h - 1) et[e ++] = i + w;
  }
  vt[n] = e;
  SCOTCH_graphInit ((SCOTCH_Graph *) g);
  if (SCOTCH_graphBuild ((SCOTCH_Graph *) g, 0, n, vt, NULL, velotab, NULL, e, et, NULL) != 0) {
    fprintf (stderr, "mkgrid: graphBuild failed\n");
    exit (9);
  }
}
