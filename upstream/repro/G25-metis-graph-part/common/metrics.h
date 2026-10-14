/* Shared helpers: cut, communication volume and load imbalance of a partition. */
static SCOTCH_Num
cutCompute (SCOTCH_Num n, SCOTCH_Num baseval, const SCOTCH_Num * xadj, const SCOTCH_Num * adjncy, const SCOTCH_Num * adjwgt, const SCOTCH_Num * part)
{
  SCOTCH_Num v, e, cut = 0;
  for (v = 0; v < n; v ++)
    for (e = xadj[v] - baseval; e < xadj[v + 1] - baseval; e ++)
      if (part[adjncy[e] - baseval] != part[v])
        cut += (adjwgt != NULL) ? adjwgt[e] : 1;
  return cut / 2;
}
static SCOTCH_Num
volCompute (SCOTCH_Num n, SCOTCH_Num baseval, const SCOTCH_Num * xadj, const SCOTCH_Num * adjncy, const SCOTCH_Num * vsize, SCOTCH_Num nparts, const SCOTCH_Num * part)
{
  SCOTCH_Num v, e, p, vol = 0;
  SCOTCH_Num * seen = malloc (nparts * sizeof (SCOTCH_Num));
  for (p = 0; p < nparts; p ++) seen[p] = -1;
  for (v = 0; v < n; v ++) {
    seen[part[v] - baseval] = v;
    for (e = xadj[v] - baseval; e < xadj[v + 1] - baseval; e ++) {
      SCOTCH_Num pe = part[adjncy[e] - baseval] - baseval;
      if (seen[pe] != v) { seen[pe] = v; vol += (vsize != NULL) ? vsize[v] : 1; }
    }
  }
  free (seen);
  return vol;
}
/* Imbalance of constraint c (stride ncon) as max_i (load_i / target_i) with target_i = tpwgts or 1/nparts. */
static double
imbalCompute (SCOTCH_Num n, SCOTCH_Num baseval, const SCOTCH_Num * vwgt, SCOTCH_Num ncon, SCOTCH_Num c, SCOTCH_Num nparts, const double * tpwgts, const SCOTCH_Num * part)
{
  double * load = calloc (nparts, sizeof (double)), tot = 0.0, imb = 0.0;
  SCOTCH_Num v, p;
  for (v = 0; v < n; v ++) { double w = (vwgt != NULL) ? vwgt[v * ncon + c] : 1.0; load[part[v] - baseval] += w; tot += w; }
  for (p = 0; p < nparts; p ++) { double t = (tpwgts != NULL) ? tpwgts[p * ncon + c] : 1.0 / nparts; double r = load[p] / (tot * t); if (r > imb) imb = r; }
  free (load);
  return imb;
}
