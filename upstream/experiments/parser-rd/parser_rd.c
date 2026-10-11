/* parser_rd.c -- hand-written recursive-descent replacement for Scotch's
** flex/bison strategy-string parser front-end (parser_ll.l + parser_yy.y).
**
** Phase-1 contract (strictly behavior-preserving):
** - accepts exactly the strings the flex/bison parser accepts;
** - builds Strat trees whose stratSave serialization is byte-identical
**   (proven by the differ harness in this directory);
** - emits the same number of hollow-strategy-parameter warnings
**   (errorPrintW), in the same situations;
** - all diagnostics still go through errorPrint, with sharper content
**   (what was expected, where) -- message TEXT is explicitly not part of
**   the compatibility contract, accept/reject verdicts and trees are.
**
** Everything downstream of parsing (parser.c tree routines, stratTestEval,
** stratSave, stratExit) is untouched: this file only produces the same
** Strat / StratTest structures the bison actions produce, off the same
** method/parameter/condition tables.
**
** Lexical fidelity notes (mirroring parser_ll.l exactly):
** - whitespace is ' ', '\t', '\n' ONLY ('\r' is a syntax error, as upstream);
** - character classes are ASCII ranges, not locale-dependent isalnum();
** - method names are single [0-9A-Za-z] characters;
** - identifiers are [A-Za-z][0-9A-Za-z]*, truncated to PARSERSTRINGLEN-1
**   before table matching (like the flex strncpy);
** - numbers follow flex maximal-munch with backtracking: '.' only binds
**   when followed by a digit, 'e'/'E' only when followed by an optional
**   sign and a digit; values go through atof()/atol() on the exact token
**   text (so "0x10" is 0 followed by a syntax error, never hex);
** - table lookups are longest-name-prefix strncasecmp matches, so a
**   parameter token "sepx" matches parameter "sep" exactly as upstream.
*/

#define SCOTCH_PARSER_RD

#include "module.h"
#include "common.h"

#undef INTEGER                                    /* In case someone defined them */
#undef DOUBLE

#include "parser.h"

#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#define PRDSTRINGLEN                256           /* Must match PARSERSTRINGLEN (parser_yy.h): flex token-text truncation */

/*
**  The scanner state.
*/

typedef struct PrdScan_ {
  const char *              textptr;              /*+ Start of strategy string +*/
  const char *              charptr;              /*+ Current scan position    +*/
} PrdScan;

/*
**  Character classes: ASCII, exactly like the flex rules.
*/

static int
prdIsDigit (
const int                   c)
{
  return ((c >= '0') && (c <= '9'));
}

static int
prdIsAlpha (
const int                   c)
{
  return (((c >= 'a') && (c <= 'z')) || ((c >= 'A') && (c <= 'Z')));
}

static int
prdIsAlnum (
const int                   c)
{
  return (prdIsDigit (c) || prdIsAlpha (c));
}

/*
**  Scanner primitives.
*/

/* Skip whitespace: only ' ', '\t' and '\n', as in the flex rule "[ \t\n]*". */

static void
prdSkip (
PrdScan * const             scanptr)
{
  while ((*scanptr->charptr == ' ')  ||
         (*scanptr->charptr == '\t') ||
         (*scanptr->charptr == '\n'))
    scanptr->charptr ++;
}

/* Skip whitespace and return the next significant character
** without consuming it ('\0' at end of string).
*/

static int
prdPeek (
PrdScan * const             scanptr)
{
  prdSkip (scanptr);
  return ((int) (unsigned char) *scanptr->charptr);
}

/* Compute the 1-based line and column of a position, for messages. */

static void
prdPos (
const PrdScan * const       scanptr,
const char * const          posptr,
int * const                 lineptr,
int * const                 colptr)
{
  const char *        p;
  int                 line = 1;
  int                 col  = 1;

  for (p = scanptr->textptr; p < posptr; p ++) {
    if (*p == '\n') {
      line ++;
      col = 1;
    }
    else
      col ++;
  }
  *lineptr = line;
  *colptr  = col;
}

/* Report a syntax error at the current position. */

static void
prdErr (
PrdScan * const             scanptr,
const char * const          mesgptr)
{
  int                 line;
  int                 col;

  prdSkip (scanptr);                              /* Point at the offending character, not at leading blanks */
  prdPos  (scanptr, scanptr->charptr, &line, &col);
  errorPrint ("stratParserParseRd: %s, line %d, column %d, at \"%s\"",
              mesgptr, line, col, scanptr->charptr);
}

/*
**  Token lexers.
*/

/* Lex an identifier [A-Za-z][0-9A-Za-z]* into buf (size PRDSTRINGLEN),
** truncated like the flex strncpy. Returns 1 on success, 0 if the next
** significant character does not start an identifier (nothing consumed).
*/

static int
prdLexIdent (
PrdScan * const             scanptr,
char * const                buf)
{
  const char *        beg;
  size_t              len;

  prdSkip (scanptr);
  if (! prdIsAlpha ((int) (unsigned char) *scanptr->charptr))
    return (0);

  beg = scanptr->charptr;
  do
    scanptr->charptr ++;
  while (prdIsAlnum ((int) (unsigned char) *scanptr->charptr));

  len = (size_t) (scanptr->charptr - beg);
  if (len >= PRDSTRINGLEN)                        /* Flex stores at most PARSERSTRINGLEN-1 chars of token text */
    len = PRDSTRINGLEN - 1;
  memcpy (buf, beg, len);
  buf[len] = '\0';
  return (1);
}

/* Lex a number token exactly as the flex {INTEGER}/{FLOAT} rules do:
** digits, then a fractional part only if '.' is directly followed by a
** digit, then an exponent only if 'e'/'E' (with optional sign) is followed
** by a digit. Converts through atof()/atol() on the exact token text.
** Returns 1 on success (dblflag says whether the token was a FLOAT),
** 0 if the next significant character is not a digit (nothing consumed),
** -1 on out-of-memory.
*/

static int
prdLexNumber (
PrdScan * const             scanptr,
int * const                 dblflagptr,           /*+ Set to 1 if token matched {FLOAT}, 0 if {INTEGER}  +*/
double * const              dblptr,               /*+ atof() of token text                               +*/
INT * const                 intptr)               /*+ (INT) atol() / (INT) atof() of token text          +*/
{
  const char *        beg;
  const char *        p;
  char                sbuf[128];
  char *              tbuf;
  size_t              len;
  int                 dblflag = 0;

  prdSkip (scanptr);
  if (! prdIsDigit ((int) (unsigned char) *scanptr->charptr))
    return (0);

  beg = scanptr->charptr;
  p   = beg;
  do
    p ++;
  while (prdIsDigit ((int) (unsigned char) *p));

  if ((*p == '.') && prdIsDigit ((int) (unsigned char) p[1])) { /* Fractional part binds only before a digit */
    dblflag = 1;
    p += 2;
    while (prdIsDigit ((int) (unsigned char) *p))
      p ++;
  }
  if ((*p == 'e') || (*p == 'E')) {               /* Exponent binds only when well-formed */
    const char *        q = p + 1;

    if ((*q == '+') || (*q == '-'))
      q ++;
    if (prdIsDigit ((int) (unsigned char) *q)) {
      dblflag = 1;
      p = q + 1;
      while (prdIsDigit ((int) (unsigned char) *p))
        p ++;
    }
  }

  len  = (size_t) (p - beg);                      /* Convert the exact token text, as the flex actions do */
  tbuf = (len < sizeof (sbuf)) ? sbuf : (char *) memAlloc (len + 1);
  if (tbuf == NULL) {
    errorPrint ("stratParserParseRd: out of memory");
    return (-1);
  }
  memcpy (tbuf, beg, len);
  tbuf[len] = '\0';

  *dblflagptr = dblflag;
  *dblptr     = atof (tbuf);
  *intptr     = dblflag ? (INT) atof (tbuf) : (INT) atol (tbuf);

  if (tbuf != sbuf)
    memFree (tbuf);

  scanptr->charptr = p;
  return (1);
}

/*
**  Node allocation.
*/

static Strat *
prdStratAlloc (
const StratTab * const      stratab,
const StratNodeType         typeval)
{
  Strat *             straptr;

  if ((straptr = (Strat *) memAlloc (sizeof (Strat))) == NULL) {
    errorPrint ("stratParserParseRd: out of memory");
    return (NULL);
  }
  straptr->tablptr = stratab;
  straptr->typeval = typeval;
  return (straptr);
}

static StratTest *
prdTestAlloc (
const StratTestType         testval,
const StratParamType        nodeval)
{
  StratTest *         testptr;

  if ((testptr = (StratTest *) memAlloc (sizeof (StratTest))) == NULL) {
    errorPrint ("stratParserParseRd: out of memory");
    return (NULL);
  }
  testptr->testval = testval;
  testptr->nodeval = nodeval;
  return (testptr);
}

/* Tell whether a test node is a logical (condition) node or an
** arithmetic (expression) node. In the bison grammar this distinction
** is structural (TESTOR..TESTREL vs TESTEXPR1..TESTEXPR4); here it is
** recovered from the node type, which encodes exactly the same split.
*/

static int
prdTestLogic (
const StratTest * const     testptr)
{
  switch (testptr->testval) {
    case STRATTESTOR  :
    case STRATTESTAND :
    case STRATTESTNOT :
    case STRATTESTEQ  :
    case STRATTESTGT  :
    case STRATTESTLT  :
      return (1);
    default :
      return (0);
  }
}

/*
**  Forward declarations.
*/

static Strat *              prdParseSelect      (PrdScan * const, const StratTab * const);
static Strat *              prdParseEmpty       (PrdScan * const, const StratTab * const);
static Strat *              prdParseStratTest   (PrdScan * const, const StratTab * const);
static Strat *              prdParseMethod      (PrdScan * const, const StratTab * const);
static int                  prdParseParams      (PrdScan * const, const StratTab * const, Strat * const);
static StratTest *          prdParseTestOr      (PrdScan * const, const StratTab * const);
static StratTest *          prdParseTestAnd     (PrdScan * const, const StratTab * const);
static StratTest *          prdParseTestNot     (PrdScan * const, const StratTab * const);
static StratTest *          prdParseTestRel     (PrdScan * const, const StratTab * const);
static StratTest *          prdParseTestExpr1   (PrdScan * const, const StratTab * const);
static StratTest *          prdParseTestExpr2   (PrdScan * const, const StratTab * const);
static StratTest *          prdParseTestExpr3   (PrdScan * const, const StratTab * const);
static StratTest *          prdParseTestExpr4   (PrdScan * const, const StratTab * const);

/*
**  Strategy-level productions.
*/

/* STRATSELECT : STRATSELECT '|' STRATEMPTY | STRATEMPTY */

static Strat *
prdParseSelect (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  Strat *             straptr;

  if ((straptr = prdParseEmpty (scanptr, stratab)) == NULL)
    return (NULL);

  while (prdPeek (scanptr) == '|') {
    Strat *             strat2ptr;
    Strat *             seleptr;

    scanptr->charptr ++;
    if ((strat2ptr = prdParseEmpty (scanptr, stratab)) == NULL) {
      stratExit (straptr);
      return (NULL);
    }
    if ((seleptr = prdStratAlloc (stratab, STRATNODESELECT)) == NULL) {
      stratExit (straptr);
      stratExit (strat2ptr);
      return (NULL);
    }
    seleptr->data.seledat.stratab[0] = straptr;
    seleptr->data.seledat.stratab[1] = strat2ptr;
    straptr = seleptr;
  }
  return (straptr);
}

/* STRATEMPTY : STRATCONCAT | (empty)
** STRATCONCAT : STRATCONCAT STRATTEST | STRATTEST
** A concatenation item starts with '/', '(' or a method-name character;
** anything else at this position is the empty strategy (the caller then
** validates its own terminator, which yields the same accept/reject
** verdicts as the LALR automaton).
*/

static Strat *
prdParseEmpty (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  Strat *             straptr;
  int                 c;

  c = prdPeek (scanptr);
  if ((c != '/') && (c != '(') && (! prdIsAlnum (c)))
    return (prdStratAlloc (stratab, STRATNODEEMPTY)); /* Empty production */

  if ((straptr = prdParseStratTest (scanptr, stratab)) == NULL)
    return (NULL);

  for ( ; ; ) {
    Strat *             strat2ptr;
    Strat *             concptr;

    c = prdPeek (scanptr);
    if ((c != '/') && (c != '(') && (! prdIsAlnum (c)))
      break;
    if ((strat2ptr = prdParseStratTest (scanptr, stratab)) == NULL) {
      stratExit (straptr);
      return (NULL);
    }
    if ((concptr = prdStratAlloc (stratab, STRATNODECONCAT)) == NULL) {
      stratExit (straptr);
      stratExit (strat2ptr);
      return (NULL);
    }
    concptr->data.concdat.stratab[0] = straptr;
    concptr->data.concdat.stratab[1] = strat2ptr;
    straptr = concptr;
  }
  return (straptr);
}

/* STRATTEST : '/' TEST '?' STRATSELECT [ ':' STRATSELECT ] ';' | STRATGROUP
** STRATGROUP : '(' STRATSELECT ')' | STRATMETHOD
*/

static Strat *
prdParseStratTest (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  int                 c;

  c = prdPeek (scanptr);
  if (c == '/') {                                 /* Condition node */
    StratTest *         testptr;
    Strat *             thenptr;
    Strat *             elseptr = NULL;
    Strat *             condptr;

    scanptr->charptr ++;
    if ((testptr = prdParseTestOr (scanptr, stratab)) == NULL)
      return (NULL);
    if (! prdTestLogic (testptr)) {
      prdErr (scanptr, "condition does not reduce to a comparison");
      stratTestExit (testptr);
      return (NULL);
    }
    if (prdPeek (scanptr) != '?') {
      prdErr (scanptr, "expected \"?\" after condition");
      stratTestExit (testptr);
      return (NULL);
    }
    scanptr->charptr ++;
    if ((thenptr = prdParseSelect (scanptr, stratab)) == NULL) {
      stratTestExit (testptr);
      return (NULL);
    }
    if (prdPeek (scanptr) == ':') {
      scanptr->charptr ++;
      if ((elseptr = prdParseSelect (scanptr, stratab)) == NULL) {
        stratTestExit (testptr);
        stratExit     (thenptr);
        return (NULL);
      }
    }
    if (prdPeek (scanptr) != ';') {
      prdErr (scanptr, "expected \";\" to close condition");
      stratTestExit (testptr);
      stratExit     (thenptr);
      if (elseptr != NULL)
        stratExit (elseptr);
      return (NULL);
    }
    scanptr->charptr ++;
    if ((condptr = prdStratAlloc (stratab, STRATNODECOND)) == NULL) {
      stratTestExit (testptr);
      stratExit     (thenptr);
      if (elseptr != NULL)
        stratExit (elseptr);
      return (NULL);
    }
    condptr->data.conddat.testptr    = testptr;
    condptr->data.conddat.stratab[0] = thenptr;
    condptr->data.conddat.stratab[1] = elseptr;
    return (condptr);
  }

  if (c == '(') {                                 /* Grouping */
    Strat *             straptr;

    scanptr->charptr ++;
    if ((straptr = prdParseSelect (scanptr, stratab)) == NULL)
      return (NULL);
    if (prdPeek (scanptr) != ')') {
      prdErr    (scanptr, "expected \")\" to close group");
      stratExit (straptr);
      return (NULL);
    }
    scanptr->charptr ++;
    return (straptr);
  }

  return (prdParseMethod (scanptr, stratab));
}

/* STRATMETHOD : METHODNAME [ '{' PARAMLIST '}' ]
** Method names are single [0-9A-Za-z] characters (flex INITIAL rule),
** matched longest-table-name-prefix (case-insensitive) as in the bison
** action; then the hollow-strategy-parameter warning scan is replayed.
*/

static Strat *
prdParseMethod (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  char                nametxt[2];
  const char *        nameat;
  StratMethodTab *    methtab;
  StratParamTab *     paratab;
  Strat *             straptr;
  int                 methnum;
  size_t              methlen;
  int                 i;

  prdSkip (scanptr);
  nameat = scanptr->charptr;
  if (! prdIsAlnum ((int) (unsigned char) *nameat)) {
    prdErr (scanptr, "expected a method name, \"(\" or \"/\"");
    return (NULL);
  }
  nametxt[0] = *nameat;
  nametxt[1] = '\0';
  scanptr->charptr ++;

  methnum = 0;
  methlen = 0;                                    /* No method recognized yet */
  methtab = stratab->methtab;
  for (i = 0; methtab[i].nameptr != NULL; i ++) { /* Longest matching code name, as upstream */
    size_t              j = strlen (methtab[i].nameptr);

    if ((strncasecmp (nametxt, methtab[i].nameptr, j) == 0) && (j > methlen)) {
      methnum = methtab[i].methnum;
      methlen = j;
    }
  }
  if (methlen == 0) {
    int                 line;
    int                 col;

    prdPos (scanptr, nameat, &line, &col);
    errorPrint ("stratParserParseRd: invalid method name \"%s\", line %d, column %d, at \"%s\"",
                nametxt, line, col, nameat);
    return (NULL);
  }

  if ((straptr = prdStratAlloc (stratab, STRATNODEMETHOD)) == NULL)
    return (NULL);
  straptr->data.methdat.methnum = methnum;
  if (methtab[methnum].dataptr != NULL)           /* If default values exist, set values to default */
    memcpy (&straptr->data.methdat.datadat, methtab[methnum].dataptr, sizeof (StratNodeMethodData));

  if (prdPeek (scanptr) == '{') {                 /* Optional parameter list */
    scanptr->charptr ++;
    if (prdParseParams (scanptr, stratab, straptr) != 0) {
      stratExit (straptr);
      return (NULL);
    }
  }

  paratab = stratab->paratab;                     /* Warn about strategy parameters left unset, as upstream */
  for (i = 0; paratab[i].nameptr != NULL; i ++) {
    if ((paratab[i].methnum == straptr->data.methdat.methnum) &&
        (paratab[i].typeval == STRATPARAMSTRAT)) {
      if (*((Strat **) ((byte *) &straptr->data.methdat.datadat +
            (paratab[i].doffptr - paratab[i].dbasptr))) == NULL) {
        int                 line;
        int                 col;

        prdPos (scanptr, scanptr->charptr, &line, &col);
        errorPrintW ("stratParserParseRd: strategy parameter \"%s\" of method \"%s\" not set, line %d, column %d, before \"%s\"",
                     paratab[i].nameptr, methtab[straptr->data.methdat.methnum].nameptr,
                     line, col, scanptr->charptr);
      }
    }
  }

  return (straptr);
}

/* Report an invalid parameter value, upstream-style. */

static void
prdErrValue (
PrdScan * const             scanptr,
const StratParamTab * const paraptr,
const Strat * const         straptr)
{
  int                 line;
  int                 col;

  prdSkip (scanptr);
  prdPos  (scanptr, scanptr->charptr, &line, &col);
  errorPrint ("stratParserParseRd: invalid value for parameter \"%s\" of method \"%s\", line %d, column %d, before \"%s\"",
              paraptr->nameptr, straptr->tablptr->methtab[straptr->data.methdat.methnum].nameptr,
              line, col, scanptr->charptr);
}

/* PARAMLIST : PARAMLIST ',' PARAMPARAM | PARAMPARAM
** PARAMPARAM : PARAMNAME '=' PARAMVAL
** Called after the opening '{'; consumes the closing '}'.
** Returns 0 on success, 1 on error (caller frees the method node).
*/

static int
prdParseParams (
PrdScan * const             scanptr,
const StratTab * const      stratab,
Strat * const               straptr)
{
  StratParamTab *     paratab;

  paratab = stratab->paratab;
  for ( ; ; ) {
    char                nametxt[PRDSTRINGLEN];
    const char *        nameat;
    const StratParamTab * paraptr;
    byte *              dataptr;
    int                 paraidx;
    size_t              paralen;
    int                 deprecated;
    int                 i;
    int                 c;

    prdSkip (scanptr);
    nameat = scanptr->charptr;
    if (! prdLexIdent (scanptr, nametxt)) {
      prdErr (scanptr, "expected a parameter name");
      return (1);
    }

    paraidx = 0;
    paralen = 0;                                  /* No parameter recognized yet */
    for (i = 0; paratab[i].nameptr != NULL; i ++) { /* Longest matching parameter name for this method */
      size_t              j;

      if (paratab[i].methnum != straptr->data.methdat.methnum)
        continue;
      j = strlen (paratab[i].nameptr);
      if ((strncasecmp (nametxt, paratab[i].nameptr, j) == 0) && (j > paralen)) {
        paraidx = i;
        paralen = j;
      }
    }
    if (paralen == 0) {
      int                 line;
      int                 col;

      prdPos (scanptr, nameat, &line, &col);
      errorPrint ("stratParserParseRd: invalid method parameter name \"%s\", line %d, column %d, before \"%s\"",
                  nametxt, line, col, nameat);
      return (1);
    }
    paraptr    = &paratab[paraidx];
    deprecated = ((paraptr->typeval & STRATPARAMDEPRECATED) != 0);
    dataptr    = (byte *) &straptr->data.methdat.datadat + (paraptr->doffptr - paraptr->dbasptr);

    if (prdPeek (scanptr) != '=') {
      prdErr (scanptr, "expected \"=\" after parameter name");
      return (1);
    }
    scanptr->charptr ++;

    switch (paraptr->typeval & ~STRATPARAMDEPRECATED) {
      case STRATPARAMCASE : {                     /* Single [0-9A-Za-z] character, looked up in the selector string */
        const char *        valat;

        c = prdPeek (scanptr);
        valat = scanptr->charptr;
        if (! prdIsAlnum (c)) {
          prdErrValue (scanptr, paraptr, straptr);
          return (1);
        }
        scanptr->charptr ++;
        if (! deprecated) {                       /* Deprecated case values are consumed but neither checked nor stored */
          char                cc = (char) c;
          char *              p;

          for (p = (char *) paraptr->dselptr, i = 0; (*p != '\0') && (*p != cc); p ++, i ++) ;
          if (*p == '\0') {                       /* Char was not found: retry in lower case */
            cc = (char) tolower ((unsigned char) cc);
            for (p = (char *) paraptr->dselptr, i = 0; (*p != '\0') && (*p != cc); p ++, i ++) ;
            if (*p == '\0') {
              int                 line;
              int                 col;

              prdPos (scanptr, valat, &line, &col);
              errorPrint ("stratParserParseRd: invalid method parameter switch \"%s=%c\", line %d, column %d, before \"%s\"",
                          paraptr->nameptr, (char) c, line, col, valat);
              return (1);
            }
          }
          *((int *) dataptr) = i;
        }
        break;
      }
      case STRATPARAMDOUBLE : {                   /* Optionally signed FLOAT-or-INTEGER token, atof()ed */
        double              val;
        INT                 dum;
        int                 dblflag;
        int                 negflag = 0;
        int                 o;

        c = prdPeek (scanptr);
        if ((c == '+') || (c == '-')) {
          negflag = (c == '-');
          scanptr->charptr ++;
        }
        o = prdLexNumber (scanptr, &dblflag, &val, &dum);
        if (o <= 0) {
          if (o == 0)
            prdErrValue (scanptr, paraptr, straptr);
          return (1);
        }
        if (! deprecated)
          *((double *) dataptr) = negflag ? - val : val;
        break;
      }
      case STRATPARAMINT : {                      /* Optionally signed number; INTEGER via atol, FLOAT via (INT) atof */
        double              dblval;
        INT                 val;
        int                 dblflag;
        int                 negflag = 0;
        int                 o;

        c = prdPeek (scanptr);
        if ((c == '+') || (c == '-')) {
          negflag = (c == '-');
          scanptr->charptr ++;
        }
        o = prdLexNumber (scanptr, &dblflag, &dblval, &val);
        if (o <= 0) {
          if (o == 0)
            prdErrValue (scanptr, paraptr, straptr);
          return (1);
        }
        if (! deprecated)
          *((INT *) dataptr) = negflag ? - val : val;
        break;
      }
      case STRATPARAMSTRING : {                   /* Double-quoted string, quotes stripped, truncated */
        const char *        endptr;
        size_t              len;

        prdSkip (scanptr);
        if (*scanptr->charptr != '"') {
          prdErrValue (scanptr, paraptr, straptr);
          return (1);
        }
        for (endptr = scanptr->charptr + 1; (*endptr != '\0') && (*endptr != '"'); endptr ++) ;
        if (*endptr == '\0') {                    /* Unterminated string never matches the flex rule */
          prdErrValue (scanptr, paraptr, straptr);
          return (1);
        }
        len = (size_t) (endptr - (scanptr->charptr + 1));
        if (len >= PRDSTRINGLEN)                  /* Flex token-text truncation */
          len = PRDSTRINGLEN - 1;
        if (! deprecated) {
          /* Upstream strcpy()s up to PARSERSTRINGLEN-1 chars into the fixed
          ** StratNodeMethodData field with no release-mode bound check (see
          ** QUESTIONS_FOR_SCOTCH_TEAM.md). We keep the accepted-string set
          ** identical but clamp the copy to the field, so overlong values
          ** differ from upstream only where upstream overflows the heap.  */
          size_t              max = sizeof (StratNodeMethodData) - (size_t) (paraptr->doffptr - paraptr->dbasptr) - 1;

          if (len > max)
            len = max;
          memcpy ((char *) dataptr, scanptr->charptr + 1, len);
          ((char *) dataptr)[len] = '\0';
        }
        scanptr->charptr = endptr + 1;
        break;
      }
      case STRATPARAMSTRAT : {                    /* Nested strategy, parsed with the parameter's own tables */
        const StratTab *    subtab;
        Strat *             subptr;

        subtab = (paraptr->typeval == STRATPARAMSTRAT) /* Deprecated strategy parameters keep the current tables, */
                 ? (const StratTab *) paraptr->dselptr /* exactly as the bison action's == comparison does        */
                 : stratab;
        if ((subptr = prdParseSelect (scanptr, subtab)) == NULL)
          return (1);
        if (! deprecated)
          *((Strat **) dataptr) = subptr;
        else
          stratExit (subptr);                     /* Upstream leaks it; freeing is unobservable */
        break;
      }
      default :
        errorPrint ("stratParserParseRd: internal error: unknown parameter type (%d)", (int) paraptr->typeval);
        return (1);
    }

    c = prdPeek (scanptr);
    if (c == ',') {
      scanptr->charptr ++;
      continue;
    }
    if (c == '}') {
      scanptr->charptr ++;
      return (0);
    }
    prdErr (scanptr, "expected \",\" or \"}\" in parameter list");
    return (1);
  }
}

/*
**  Condition (test) productions. The single unification with respect to
**  the bison grammar: '(' is handled once, at the TESTEXPR4 level, and
**  may yield either a logical or an arithmetic subtree; every operator
**  then validates its operands' kind, which reproduces exactly the
**  accept/reject decisions of the LALR automaton's two paren productions
**  (TESTNOT '(' TESTOR ')' and TESTEXPR4 '(' TESTEXPR1 ')').
*/

/* TESTOR : TESTOR '|' TESTAND | TESTAND */

static StratTest *
prdParseTestOr (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  StratTest *         testptr;

  if ((testptr = prdParseTestAnd (scanptr, stratab)) == NULL)
    return (NULL);

  while (prdPeek (scanptr) == '|') {
    StratTest *         test2ptr;
    StratTest *         orptr;

    if (! prdTestLogic (testptr)) {
      prdErr        (scanptr, "left operand of \"|\" is not a condition");
      stratTestExit (testptr);
      return (NULL);
    }
    scanptr->charptr ++;
    if ((test2ptr = prdParseTestAnd (scanptr, stratab)) == NULL) {
      stratTestExit (testptr);
      return (NULL);
    }
    if (! prdTestLogic (test2ptr)) {
      prdErr        (scanptr, "right operand of \"|\" is not a condition");
      stratTestExit (testptr);
      stratTestExit (test2ptr);
      return (NULL);
    }
    if ((orptr = prdTestAlloc (STRATTESTOR, STRATPARAMLOG)) == NULL) {
      stratTestExit (testptr);
      stratTestExit (test2ptr);
      return (NULL);
    }
    orptr->data.testtab[0] = testptr;
    orptr->data.testtab[1] = test2ptr;
    testptr = orptr;
  }
  return (testptr);
}

/* TESTAND : TESTAND '&' TESTNOT | TESTNOT */

static StratTest *
prdParseTestAnd (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  StratTest *         testptr;

  if ((testptr = prdParseTestNot (scanptr, stratab)) == NULL)
    return (NULL);

  while (prdPeek (scanptr) == '&') {
    StratTest *         test2ptr;
    StratTest *         andptr;

    if (! prdTestLogic (testptr)) {
      prdErr        (scanptr, "left operand of \"&\" is not a condition");
      stratTestExit (testptr);
      return (NULL);
    }
    scanptr->charptr ++;
    if ((test2ptr = prdParseTestNot (scanptr, stratab)) == NULL) {
      stratTestExit (testptr);
      return (NULL);
    }
    if (! prdTestLogic (test2ptr)) {
      prdErr        (scanptr, "right operand of \"&\" is not a condition");
      stratTestExit (testptr);
      stratTestExit (test2ptr);
      return (NULL);
    }
    if ((andptr = prdTestAlloc (STRATTESTAND, STRATPARAMLOG)) == NULL) {
      stratTestExit (testptr);
      stratTestExit (test2ptr);
      return (NULL);
    }
    andptr->data.testtab[0] = testptr;
    andptr->data.testtab[1] = test2ptr;
    testptr = andptr;
  }
  return (testptr);
}

/* TESTNOT : '!' TESTNOT | TESTREL ('(' TESTOR ')' is subsumed by TESTEXPR4) */

static StratTest *
prdParseTestNot (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  if (prdPeek (scanptr) == '!') {
    StratTest *         operptr;
    StratTest *         notptr;

    scanptr->charptr ++;
    if ((operptr = prdParseTestNot (scanptr, stratab)) == NULL)
      return (NULL);
    if (! prdTestLogic (operptr)) {
      prdErr        (scanptr, "operand of \"!\" is not a condition");
      stratTestExit (operptr);
      return (NULL);
    }
    if ((notptr = prdTestAlloc (STRATTESTNOT, STRATPARAMLOG)) == NULL) {
      stratTestExit (operptr);
      return (NULL);
    }
    notptr->data.testtab[0] = operptr;
    return (notptr);
  }
  return (prdParseTestRel (scanptr, stratab));
}

/* TESTREL : TESTEXPR1 TESTRELOP TESTEXPR1
** Unified: when no relational operator follows, the arithmetic
** expression is returned as-is and the consumer validates kinds.
*/

static StratTest *
prdParseTestRel (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  StratTest *         testptr;
  StratTest *         test2ptr;
  StratTest *         relptr;
  StratTestType       testval;
  int                 c;

  if ((testptr = prdParseTestExpr1 (scanptr, stratab)) == NULL)
    return (NULL);

  c = prdPeek (scanptr);
  switch (c) {
    case '<' : testval = STRATTESTLT; break;
    case '=' : testval = STRATTESTEQ; break;
    case '>' : testval = STRATTESTGT; break;
    default :
      return (testptr);                           /* Plain arithmetic expression: caller decides */
  }
  if (prdTestLogic (testptr)) {
    prdErr        (scanptr, "left operand of comparison is not an arithmetic expression");
    stratTestExit (testptr);
    return (NULL);
  }
  scanptr->charptr ++;
  if ((test2ptr = prdParseTestExpr1 (scanptr, stratab)) == NULL) {
    stratTestExit (testptr);
    return (NULL);
  }
  if (prdTestLogic (test2ptr)) {
    prdErr        (scanptr, "right operand of comparison is not an arithmetic expression");
    stratTestExit (testptr);
    stratTestExit (test2ptr);
    return (NULL);
  }
  if ((relptr = prdTestAlloc (testval, STRATPARAMLOG)) == NULL) {
    stratTestExit (testptr);
    stratTestExit (test2ptr);
    return (NULL);
  }
  relptr->data.testtab[0] = testptr;
  relptr->data.testtab[1] = test2ptr;
  return (relptr);
}

/* Shared body for the three left-associative arithmetic levels.
** opchr2 is 0 for the single-operator levels.
*/

static StratTest *
prdParseTestArith (
PrdScan * const             scanptr,
const StratTab * const      stratab,
StratTest * (* subparse) (PrdScan * const, const StratTab * const),
const int                   opchr1,
const StratTestType         opval1,
const int                   opchr2,
const StratTestType         opval2)
{
  StratTest *         testptr;

  if ((testptr = subparse (scanptr, stratab)) == NULL)
    return (NULL);

  for ( ; ; ) {
    StratTest *         test2ptr;
    StratTest *         nodeptr;
    StratTestType       testval;
    int                 c;

    c = prdPeek (scanptr);
    if (c == opchr1)
      testval = opval1;
    else if ((opchr2 != 0) && (c == opchr2))
      testval = opval2;
    else
      break;
    if (prdTestLogic (testptr)) {
      prdErr        (scanptr, "left operand of arithmetic operator is not an arithmetic expression");
      stratTestExit (testptr);
      return (NULL);
    }
    scanptr->charptr ++;
    if ((test2ptr = subparse (scanptr, stratab)) == NULL) {
      stratTestExit (testptr);
      return (NULL);
    }
    if (prdTestLogic (test2ptr)) {
      prdErr        (scanptr, "right operand of arithmetic operator is not an arithmetic expression");
      stratTestExit (testptr);
      stratTestExit (test2ptr);
      return (NULL);
    }
    /* The bison actions for TESTEXPR1..3 leave nodeval unset (it is
    ** recomputed at evaluation time); 0 here is equally unobservable
    ** but deterministic.                                             */
    if ((nodeptr = prdTestAlloc (testval, 0)) == NULL) {
      stratTestExit (testptr);
      stratTestExit (test2ptr);
      return (NULL);
    }
    nodeptr->data.testtab[0] = testptr;
    nodeptr->data.testtab[1] = test2ptr;
    testptr = nodeptr;
  }
  return (testptr);
}

/* TESTEXPR1 : TESTEXPR1 ('+'|'-') TESTEXPR2 | TESTEXPR2 */

static StratTest *
prdParseTestExpr1 (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  return (prdParseTestArith (scanptr, stratab, prdParseTestExpr2,
                             '+', STRATTESTADD, '-', STRATTESTSUB));
}

/* TESTEXPR2 : TESTEXPR2 '*' TESTEXPR3 | TESTEXPR3 */

static StratTest *
prdParseTestExpr2 (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  return (prdParseTestArith (scanptr, stratab, prdParseTestExpr3,
                             '*', STRATTESTMUL, 0, STRATTESTMUL));
}

/* TESTEXPR3 : TESTEXPR3 '%' TESTEXPR4 | TESTEXPR4 */

static StratTest *
prdParseTestExpr3 (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  return (prdParseTestArith (scanptr, stratab, prdParseTestExpr4,
                             '%', STRATTESTMOD, 0, STRATTESTMOD));
}

/* TESTEXPR4 : '(' ... ')' | TESTVAL | TESTVAR
** TESTVAL : [('+'|'-')] (VALDOUBLE | VALINT)  -- sign only before literals
** TESTVAR : PARAMNAME, longest-prefix matched against the condition table
*/

static StratTest *
prdParseTestExpr4 (
PrdScan * const             scanptr,
const StratTab * const      stratab)
{
  StratTest *         testptr;
  int                 c;

  c = prdPeek (scanptr);

  if (c == '(') {                                 /* Both paren productions of the bison grammar at once */
    scanptr->charptr ++;
    if ((testptr = prdParseTestOr (scanptr, stratab)) == NULL)
      return (NULL);
    if (prdPeek (scanptr) != ')') {
      prdErr        (scanptr, "expected \")\" in condition");
      stratTestExit (testptr);
      return (NULL);
    }
    scanptr->charptr ++;
    return (testptr);
  }

  if ((c == '+') || (c == '-') || prdIsDigit (c)) { /* Numeric literal, optionally signed */
    double              dblval;
    INT                 intval;
    int                 dblflag;
    int                 negflag = 0;
    int                 o;

    if ((c == '+') || (c == '-')) {
      negflag = (c == '-');
      scanptr->charptr ++;
    }
    o = prdLexNumber (scanptr, &dblflag, &dblval, &intval);
    if (o < 0)
      return (NULL);
    if (o == 0) {                                 /* Sign not followed by a number token */
      prdErr (scanptr, "expected a number");
      return (NULL);
    }
    if (dblflag) {
      if ((testptr = prdTestAlloc (STRATTESTVAL, STRATPARAMDOUBLE)) == NULL)
        return (NULL);
      testptr->data.val.valdbl = negflag ? - dblval : dblval;
    }
    else {
      if ((testptr = prdTestAlloc (STRATTESTVAL, STRATPARAMINT)) == NULL)
        return (NULL);
      testptr->data.val.valint = negflag ? - intval : intval;
    }
    return (testptr);
  }

  if (prdIsAlpha (c)) {                           /* Condition variable */
    char                nametxt[PRDSTRINGLEN];
    const char *        nameat;
    StratParamTab *     condtab;
    int                 para;
    size_t              paralen;
    int                 i;

    prdSkip (scanptr);
    nameat = scanptr->charptr;
    prdLexIdent (scanptr, nametxt);

    para    = 0;
    paralen = 0;                                  /* No parameter recognized yet */
    condtab = stratab->condtab;
    for (i = 0; condtab[i].nameptr != NULL; i ++) { /* Longest matching parameter name */
      size_t              j = strlen (condtab[i].nameptr);

      if ((strncasecmp (nametxt, condtab[i].nameptr, j) == 0) && (j > paralen)) {
        para    = i;
        paralen = j;
      }
    }
    if (paralen == 0) {
      int                 line;
      int                 col;

      prdPos (scanptr, nameat, &line, &col);
      errorPrint ("stratParserParseRd: invalid graph parameter name \"%s\", line %d, column %d, before \"%s\"",
                  nametxt, line, col, nameat);
      return (NULL);
    }

    if ((testptr = prdTestAlloc (STRATTESTVAR, condtab[para].typeval)) == NULL)
      return (NULL);
    testptr->data.var.datatab = stratab;
    testptr->data.var.dataoft = condtab[para].doffptr - condtab[para].dbasptr;
    return (testptr);
  }

  prdErr (scanptr, "expected a number, a graph parameter or \"(\" in condition");
  return (NULL);
}

/*
**  The entry point.
*/

/* This routine is the recursive-descent counterpart of stratParserParse.
** It returns:
** - !NULL  : pointer to the strategy.
** - NULL   : on error.
*/

Strat *
stratParserParseRd (
const StratTab * const      stratab,              /*+ Pointer to parsing tables +*/
const char * const          textptr)              /*+ Strategy string to parse  +*/
{
  PrdScan             scandat;
  Strat *             straptr;

  scandat.textptr = textptr;
  scandat.charptr = textptr;

  if ((straptr = prdParseSelect (&scandat, stratab)) == NULL)
    return (NULL);

  prdSkip (&scandat);
  if (*scandat.charptr != '\0') {                 /* The whole string must be one strategy */
    prdErr    (&scandat, "unexpected characters after strategy");
    stratExit (straptr);
    return (NULL);
  }
  return (straptr);
}
