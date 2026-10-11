/* differ.c -- differential harness: bison parser vs recursive-descent parser.
**
** For every input strategy string (built-in corpus + one per stdin line) and
** every sequential strategy grammar (graph mapping, graph ordering, overlap
** partitioning, mesh ordering), this harness:
**
**   1. parses with the library's own flex/bison parser (stratParserParse,
**      straight from libscotch.so) and with the RD parser (parser_rd.c);
**   2. compares accept/reject verdicts;
**   3. on double accept, byte-compares the stratSave serializations
**      (the canonical-form oracle);
**   4. re-parses the canonical form with both parsers and byte-compares
**      again (canonicalization stability);
**   5. compares errorPrintW warning counts (hollow-parameter warnings).
**
** The harness IS the library's error sink: libscotch.so leaves
** SCOTCH_errorPrint / SCOTCH_errorPrintW undefined, so our capturing
** definitions below receive every diagnostic from both parsers.
**
** Exit status: 0 if no mismatches, 1 otherwise. -v prints captured
** diagnostics along with each mismatch.
*/

#define _GNU_SOURCE                               /* open_memstream */

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#include "module.h"
#include "common.h"

#undef INTEGER
#undef DOUBLE

#include "parser.h"

/* Strategy tables of the sequential grammars (renamed by module.h). */

extern StratTab             kgraphmapststratab;
extern StratTab             hgraphorderststratab;
extern StratTab             wgraphpartststratab;
extern StratTab             hmeshorderststratab;

/* The two parsers under comparison. */

Strat *                     stratParserParse    (const StratTab * const, const char * const); /* bison, from libscotch.so */
extern Strat *              stratParserParseRd  (const StratTab * const, const char * const); /* parser_rd.c              */

/*
**  Error capture: we provide the SCOTCH_errorPrint / SCOTCH_errorPrintW
**  the library was linked against.
*/

static int                  errcnt  = 0;
static int                  warncnt = 0;
static char                 msgbuf[65536];
static size_t               msglen  = 0;

static void
msgcapture (
const char * const          kind,
const char * const          fmt,
va_list                     ap)
{
  int                 o;

  if (msglen < sizeof (msgbuf) - 256) {
    o = snprintf (msgbuf + msglen, sizeof (msgbuf) - msglen, "    [%s] ", kind);
    if (o > 0)
      msglen += (size_t) o;
    o = vsnprintf (msgbuf + msglen, sizeof (msgbuf) - msglen, fmt, ap);
    if (o > 0)
      msglen += (size_t) o;
    o = snprintf (msgbuf + msglen, sizeof (msgbuf) - msglen, "\n");
    if (o > 0)
      msglen += (size_t) o;
  }
}

void
errorPrint (                                      /* Expands to SCOTCH_errorPrint */
const char * const          errstr,
...)
{
  va_list             ap;

  errcnt ++;
  va_start (ap, errstr);
  msgcapture ("ERROR", errstr, ap);
  va_end (ap);
}

void
errorPrintW (                                     /* Expands to SCOTCH_errorPrintW */
const char * const          errstr,
...)
{
  va_list             ap;

  warncnt ++;
  va_start (ap, errstr);
  msgcapture ("WARN", errstr, ap);
  va_end (ap);
}

static void
msgreset (void)
{
  errcnt    = 0;
  warncnt   = 0;
  msglen    = 0;
  msgbuf[0] = '\0';
}

/*
**  Helpers.
*/

/* Serialize a strategy tree. Because the bison parser can build trees with
** stray heap pointers reinterpreted as scalar parameter slots (see the
** empty-scalar-value finding), stratSave can dereference garbage and crash;
** we therefore run it in a forked child and pipe the text back. A child
** that dies by signal yields the sentinel "<UNSAVEABLE>", which the caller
** treats as a distinguished value (never equal to a real save), so the
** harness survives and attributes the fault to that tree.
*/

static char *
saveStr (
const Strat * const         straptr)
{
  int                 fds[2];
  pid_t               pid;
  char *              buf;
  size_t              cap = 4096;
  size_t              len = 0;
  int                 status;

  if (pipe (fds) != 0) {
    fprintf (stderr, "differ: pipe failed\n");
    exit (2);
  }
  if ((pid = fork ()) == 0) {                     /* Child: save, write to pipe, _exit */
    char *              cbuf = NULL;
    size_t              clen = 0;
    FILE *              stream;

    close (fds[0]);
    if ((stream = open_memstream (&cbuf, &clen)) != NULL) {
      stratSave (straptr, stream);                /* May segfault on a corrupt tree; contained here */
      fclose (stream);
      { const char * p = cbuf; size_t left = clen; ssize_t w;
        while (left > 0) { w = write (fds[1], p, left); if (w <= 0) break; p += w; left -= (size_t) w; } }
    }
    close (fds[1]);
    _exit (0);
  }
  close (fds[1]);
  buf = (char *) malloc (cap);
  for ( ; ; ) {
    ssize_t             r;

    if (len + 1 >= cap) { cap *= 2; buf = (char *) realloc (buf, cap); }
    r = read (fds[0], buf + len, cap - len - 1);
    if (r <= 0)
      break;
    len += (size_t) r;
  }
  buf[len] = '\0';
  close (fds[0]);
  waitpid (pid, &status, 0);

  if (! WIFEXITED (status)) {                     /* Child crashed inside stratSave */
    free (buf);
    return (strdup ("<UNSAVEABLE>"));
  }
  return (buf);
}

static void
printStr (
const char * const          s)
{
  const char *        p;

  fputc ('"', stdout);
  for (p = s; *p != '\0'; p ++) {
    if (*p == '\n')
      fputs ("\\n", stdout);
    else if (*p == '\t')
      fputs ("\\t", stdout);
    else if (*p == '"')
      fputs ("\\\"", stdout);
    else if (((unsigned char) *p < 32) || ((unsigned char) *p > 126))
      printf ("\\x%02x", (unsigned char) *p);
    else
      fputc (*p, stdout);
  }
  fputc ('"', stdout);
}

/*
**  The comparison core.
*/

static int                  verbflag  = 0;
static long                 parsecnt  = 0;        /* (string, grammar) pairs checked  */
static long                 acceptcnt = 0;        /* pairs both parsers accepted      */
static long                 badcnt    = 0;        /* mismatching pairs                */

typedef struct TabEnt_ { const char * name; const StratTab * tab; } TabEnt;

static void                 checkOne (const char * const, const StratTab * const, const char * const);

/* Run all grammars for one input inside a forked child, so a segfault in
** either parser (or in saving a corrupt tree) is contained and reported
** against this exact input instead of killing the survey. Returns:
**   0 = clean, 1 = mismatch(es) printed by the child, 2 = child crashed.
** The child prints mismatch lines to our inherited stdout; only the count
** categories are aggregated in the parent (per-input granularity is enough).
*/

static int
checkInputForked (
const char * const          string,
const TabEnt * const        tabs,
const size_t                tabnbr)
{
  pid_t               pid;
  int                 status;

  fflush (stdout);
  if ((pid = fork ()) == 0) {
    size_t              j;

    for (j = 0; j < tabnbr; j ++)
      checkOne (tabs[j].name, tabs[j].tab, string);
    fflush (stdout);
    _exit ((badcnt != 0) ? 1 : 0);
  }
  waitpid (pid, &status, 0);
  if (! WIFEXITED (status)) {
    printf ("CRASH input=");
    printStr (string);
    printf ("\n  a parser or a tree-save segfaulted on this input (signal %d)\n", WTERMSIG (status));
    return (2);
  }
  return (WEXITSTATUS (status));
}

static void
reportMismatch (
const char * const          kind,
const char * const          tabname,
const char * const          string,
const char * const          detail,
const char * const          yymsgs,
const char * const          rdmsgs)
{
  badcnt ++;
  printf ("MISMATCH[%s] grammar=%s input=", kind, tabname);
  printStr (string);
  printf ("\n  %s\n", detail);
  if (verbflag) {
    if ((yymsgs != NULL) && (yymsgs[0] != '\0'))
      printf ("  bison diagnostics:\n%s", yymsgs);
    if ((rdmsgs != NULL) && (rdmsgs[0] != '\0'))
      printf ("  rd diagnostics:\n%s", rdmsgs);
  }
}

static void
checkOne (
const char * const          tabname,
const StratTab * const     tabptr,
const char * const          string)
{
  Strat *             yyptr;
  Strat *             rdptr;
  char *              yymsgs;
  char *              rdmsgs;
  int                 yywarn;
  int                 rdwarn;
  char                detail[8192];

  parsecnt ++;

  /* DIFFER_ONLY=yy|rd runs a single parser (the other is treated as REJECT
  ** and no comparison is done) so a crash can be attributed to one side. */
  {
    const char *        only = getenv ("DIFFER_ONLY");

    msgreset ();
    yyptr  = ((only != NULL) && (strcmp (only, "rd") == 0)) ? NULL : stratParserParse (tabptr, string);
    yywarn = warncnt;
    yymsgs = strdup (msgbuf);

    msgreset ();
    rdptr  = ((only != NULL) && (strcmp (only, "yy") == 0)) ? NULL : stratParserParseRd (tabptr, string);
    rdwarn = warncnt;
    rdmsgs = strdup (msgbuf);

    if (only != NULL) {                           /* single-parser mode: no comparison */
      if (yyptr != NULL) stratExit (yyptr);
      if (rdptr != NULL) stratExit (rdptr);
      free (yymsgs);
      free (rdmsgs);
      return;
    }
  }

  if ((yyptr != NULL) != (rdptr != NULL)) {
    char *              acsave = (yyptr != NULL) ? saveStr (yyptr) : saveStr (rdptr);

    snprintf (detail, sizeof (detail), "verdict: bison=%s rd=%s; accepted side saves as: %s",
              (yyptr != NULL) ? "ACCEPT" : "REJECT",
              (rdptr != NULL) ? "ACCEPT" : "REJECT", acsave);
    reportMismatch ("VERDICT", tabname, string, detail, yymsgs, rdmsgs);
    free (acsave);
  }
  else if (yyptr != NULL) {
    char *              yysave = saveStr (yyptr);
    char *              rdsave = saveStr (rdptr);

    acceptcnt ++;
    if (strcmp (yysave, rdsave) != 0) {
      snprintf (detail, sizeof (detail), "saved forms differ:\n  bison: %s\n  rd:    %s", yysave, rdsave);
      reportMismatch ("SAVE", tabname, string, detail, yymsgs, rdmsgs);
    }
    else {                                        /* Canonicalization stability on the agreed saved form */
      Strat *             yy2ptr;
      Strat *             rd2ptr;

      msgreset ();
      yy2ptr = stratParserParse   (tabptr, yysave);
      rd2ptr = stratParserParseRd (tabptr, yysave);

      if ((yy2ptr != NULL) != (rd2ptr != NULL)) {
        snprintf (detail, sizeof (detail), "canonical-form verdict: bison=%s rd=%s on saved form %s",
                  (yy2ptr != NULL) ? "ACCEPT" : "REJECT",
                  (rd2ptr != NULL) ? "ACCEPT" : "REJECT", yysave);
        reportMismatch ("CANON-VERDICT", tabname, string, detail, NULL, NULL);
      }
      else if (yy2ptr != NULL) {
        char *              yysave2 = saveStr (yy2ptr);
        char *              rdsave2 = saveStr (rd2ptr);

        if (strcmp (yysave2, rdsave2) != 0) {
          snprintf (detail, sizeof (detail), "canonical re-save differs:\n  bison: %s\n  rd:    %s", yysave2, rdsave2);
          reportMismatch ("CANON-SAVE", tabname, string, detail, NULL, NULL);
        }
        free (yysave2);
        free (rdsave2);
      }
      if (yy2ptr != NULL)
        stratExit (yy2ptr);
      if (rd2ptr != NULL)
        stratExit (rd2ptr);
    }
    free (yysave);
    free (rdsave);
  }

  if (yywarn != rdwarn) {
    snprintf (detail, sizeof (detail), "warning counts differ: bison=%d rd=%d", yywarn, rdwarn);
    reportMismatch ("WARN", tabname, string, detail, yymsgs, rdmsgs);
  }

  if (yyptr != NULL)
    stratExit (yyptr);
  if (rdptr != NULL)
    stratExit (rdptr);
  free (yymsgs);
  free (rdmsgs);
}

/*
**  Grammars and built-in corpus.
*/

static const TabEnt         tabtab[] = {
  { "graphmap",     &kgraphmapststratab   },
  { "graphorder",   &hgraphorderststratab },
  { "graphpartovl", &wgraphpartststratab  },
  { "meshorder",    &hmeshorderststratab  },
};
#define TABNBR  (sizeof (tabtab) / sizeof (tabtab[0]))

/* Cases that cannot travel over the line-based stdin protocol (embedded
** newlines) plus a few always-on basics, so the harness is useful even
** with no generator at all.
*/

static const char *         builtintab[] = {
  "",
  "m",
  "r",
  "m\n{\nasc\n=\nb\n}",
  "b\n|\nf",
  "/vert\n<\n1000?m;",
  " \t\n ",
  "m\rr",
  "\r",
  "r{sep=gf}",
  "m{asc=,low=}",
};
#define BUILTINNBR  (sizeof (builtintab) / sizeof (builtintab[0]))

/*
**  Main.
*/

int
main (
int                         argc,
char *                      argv[])
{
  char *              line = NULL;
  size_t              linecap = 0;
  ssize_t             linelen;
  long                strcnt   = 0;
  long                mismcnt  = 0;               /* inputs with at least one mismatch */
  long                crashcnt = 0;               /* inputs that segfaulted a parser/save */
  size_t              i;
  int                 rc;

  for (i = 1; i < (size_t) argc; i ++) {
    if (strcmp (argv[i], "-v") == 0)
      verbflag = 1;
    else {
      fprintf (stderr, "usage: %s [-v] < corpus-lines\n", argv[0]);
      return (2);
    }
  }

  for (i = 0; i < BUILTINNBR; i ++) {
    strcnt ++;
    rc = checkInputForked (builtintab[i], tabtab, TABNBR);
    if (rc == 1) mismcnt ++;
    else if (rc == 2) crashcnt ++;
  }

  while ((linelen = getline (&line, &linecap, stdin)) > 0) {
    if ((linelen > 0) && (line[linelen - 1] == '\n'))
      line[linelen - 1] = '\0';
    strcnt ++;
    rc = checkInputForked (line, tabtab, TABNBR);
    if (rc == 1) mismcnt ++;
    else if (rc == 2) crashcnt ++;
  }
  free (line);

  fprintf (stderr, "differ: %ld strings; %ld inputs with mismatches; %ld inputs crashed a parser/save\n",
           strcnt, mismcnt, crashcnt);
  return (((mismcnt == 0) && (crashcnt == 0)) ? 0 : 1);
}
