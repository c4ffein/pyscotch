/* COR-13 differential check: random test expressions -> fully parenthesised string -> parse (T1)
** -> SCOTCH_stratSave (S1) -> parse (T2) -> compare T1 and T2 structurally, and S1 with save (T2).
** Uses libscotch internal headers for the Strat/StratTest layouts only. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "module.h"
#include "common.h"
#include "parser.h"
#include "scotch.h"

#define VARNBR 4
static const char * varnames[VARNBR] = { "vert", "edge", "levl", "load" };

typedef struct Node_ { int kind; int op; int ival; double dval; int var; struct Node_ * l; struct Node_ * r; } Node;
/* kind: 0 = int val, 1 = dbl val, 2 = var, 3 = arith (op: '+','-','*','%'), 4 = rel ('<','=','>'), 5 = and, 6 = or, 7 = not */

static unsigned int seed;
static int rnd (int n) { seed = seed * 1103515245u + 12345u; return ((seed >> 16) % n); }

static Node * mk (int kind) { Node * n = calloc (1, sizeof (Node)); n->kind = kind; return n; }
static Node * genarith (int depth)
{
  int c = (depth <= 0) ? rnd (3) : rnd (7);
  Node * n;
  if (c == 0) { n = mk (0); n->ival = rnd (200) - 50; return n; }
  if (c == 1) { n = mk (1); n->dval = (double) (rnd (100)) / 4.0; return n; }
  if (c == 2) { n = mk (2); n->var = rnd (VARNBR); return n; }
  n = mk (3); n->op = "+-*%"[rnd (4)]; n->l = genarith (depth - 1); n->r = genarith (depth - 1); return n;
}
static Node * genlog (int depth)
{
  int c = (depth <= 0) ? 0 : rnd (5);
  Node * n;
  if (c <= 1) { n = mk (4); n->op = "<=>"[rnd (3)]; n->l = genarith (depth); n->r = genarith (depth); return n; }
  if (c == 2) { n = mk (5); n->l = genlog (depth - 1); n->r = genlog (depth - 1); return n; }
  if (c == 3) { n = mk (6); n->l = genlog (depth - 1); n->r = genlog (depth - 1); return n; }
  n = mk (7); n->l = genlog (depth - 1); return n;
}
static void pr (const Node * n, FILE * f)                 /* Fully parenthesised printer */
{
  switch (n->kind) {
    case 0 : if (n->ival < 0) fprintf (f, "(%d)", n->ival); else fprintf (f, "%d", n->ival); break;
    case 1 : fprintf (f, "%.2f", n->dval); break;
    case 2 : fprintf (f, "%s", varnames[n->var]); break;
    case 3 : case 4 : fprintf (f, "("); pr (n->l, f); fprintf (f, ")%c(", n->op); pr (n->r, f); fprintf (f, ")"); break;
    case 5 : fprintf (f, "("); pr (n->l, f); fprintf (f, ")&("); pr (n->r, f); fprintf (f, ")"); break;
    case 6 : fprintf (f, "("); pr (n->l, f); fprintf (f, ")|("); pr (n->r, f); fprintf (f, ")"); break;
    case 7 : fprintf (f, "!("); pr (n->l, f); fprintf (f, ")"); break;
  }
}
static int cmp (const StratTest * a, const StratTest * b)  /* Structural comparison of two Scotch test trees */
{
  if (a->testval != b->testval) return 1;
  switch (a->testval) {
    case STRATTESTVAL :
      if (a->nodeval != b->nodeval) return 1;
      if (a->nodeval == STRATPARAMINT) return (a->data.val.valint != b->data.val.valint);
      return (a->data.val.valdbl != b->data.val.valdbl);
    case STRATTESTVAR : return (a->data.var.dataoft != b->data.var.dataoft);
    case STRATTESTNOT : return cmp (a->data.testtab[0], b->data.testtab[0]);
    default : return (cmp (a->data.testtab[0], b->data.testtab[0]) || cmp (a->data.testtab[1], b->data.testtab[1]));
  }
}
static int cmpmine (const Node * n, const StratTest * t)  /* Check that Scotch parsed my string as I meant it */
{
  static const int ops[128] = { 0 };
  switch (n->kind) {
    case 0 : return (t->testval != STRATTESTVAL || t->nodeval != STRATPARAMINT || t->data.val.valint != n->ival);
    case 1 : return (t->testval != STRATTESTVAL || t->nodeval != STRATPARAMDOUBLE || t->data.val.valdbl != n->dval);
    case 2 : return (t->testval != STRATTESTVAR);
    case 3 : { StratTestType e = (n->op == '+') ? STRATTESTADD : (n->op == '-') ? STRATTESTSUB : (n->op == '*') ? STRATTESTMUL : STRATTESTMOD;
               return (t->testval != e || cmpmine (n->l, t->data.testtab[0]) || cmpmine (n->r, t->data.testtab[1])); }
    case 4 : { StratTestType e = (n->op == '<') ? STRATTESTLT : (n->op == '=') ? STRATTESTEQ : STRATTESTGT;
               return (t->testval != e || cmpmine (n->l, t->data.testtab[0]) || cmpmine (n->r, t->data.testtab[1])); }
    case 5 : return (t->testval != STRATTESTAND || cmpmine (n->l, t->data.testtab[0]) || cmpmine (n->r, t->data.testtab[1]));
    case 6 : return (t->testval != STRATTESTOR || cmpmine (n->l, t->data.testtab[0]) || cmpmine (n->r, t->data.testtab[1]));
    case 7 : return (t->testval != STRATTESTNOT || cmpmine (n->l, t->data.testtab[0]));
  }
  (void) ops; return 1;
}
static const StratTest * testof (SCOTCH_Strat * s) { Strat * p = *((Strat **) s); return (p->typeval == STRATNODECOND) ? p->data.conddat.testptr : NULL; }
static int save (SCOTCH_Strat * s, char * buf, size_t siz)
{
  FILE * f = tmpfile (); size_t n;
  if (f == NULL) return 1;
  if (SCOTCH_stratSave (s, f) != 0) { fclose (f); return 1; }
  rewind (f); n = fread (buf, 1, siz - 1, f); buf[n] = '\0'; fclose (f); return 0;
}
int main (int argc, char * argv[])
{
  int nbr = (argc > 1) ? atoi (argv[1]) : 1000, i, bad = 0, badmine = 0, badidem = 0, verbose = (argc > 3);
  seed = (argc > 2) ? atoi (argv[2]) : 1;
  for (i = 0; i < nbr; i ++) {
    Node * n = genlog (3); char e[4096], s1[8192], s2[8192]; FILE * f; SCOTCH_Strat t1, t2;
    f = fmemopen (e, sizeof (e), "w"); fprintf (f, "/("); pr (n, f); fprintf (f, ")?r;"); fclose (f);
    SCOTCH_stratInit (&t1);
    if (SCOTCH_stratGraphMap (&t1, e) != 0) { printf ("PARSE FAIL: %s\n", e); return 2; }
    if (cmpmine (n, testof (&t1))) { badmine ++; printf ("MY-GRAMMAR MISMATCH: %s\n", e); }
    if (save (&t1, s1, sizeof (s1))) return 2;
    SCOTCH_stratInit (&t2);
    if (SCOTCH_stratGraphMap (&t2, s1) != 0) { bad ++; printf ("REPARSE FAIL: %s\n  saved: %s\n", e, s1); SCOTCH_stratExit (&t1); continue; }
    if (cmp (testof (&t1), testof (&t2))) { bad ++; if (bad <= 5 || verbose) printf ("TREE DIFFERS:\n  in:    %s\n  saved: %s\n", e, s1); }
    if (save (&t2, s2, sizeof (s2))) return 2;
    if (strcmp (s1, s2)) badidem ++;
    SCOTCH_stratExit (&t1); SCOTCH_stratExit (&t2);
  }
  printf ("%d expressions: %d round-trip tree mismatches, %d non-idempotent saves, %d generator mismatches\n", nbr, bad, badidem, badmine);
  return (bad + badidem + badmine) ? 1 : 0;
}
