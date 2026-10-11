# Target architectures — Scotch v7.0.11

Analyst 05. Submodule at commit `626b88c`, tag `v7.0.11`. Territory: the
`arch_*.c` / `arch.c` / `arch.h` family under
`external/scotch/src/libscotch/` (READ-ONLY; nothing here was modified).

## Scope

Reviewed: the generic dispatch layer (`arch.c`, `arch.h`), and the per-type
architecture modules `arch_cmplt`, `arch_cmpltw`, `arch_deco`, `arch_deco2`,
`arch_dist`, `arch_hcub`, `arch_tleaf` (incl. the labeled `ltleaf` variant),
`arch_mesh` (mesh2/mesh3/meshX), `arch_torus` (torus2/3/X), `arch_sub`,
`arch_vcmplt`, `arch_vhcub`. The `*_mpi.c` twins (all ~77-119 lines, thin
type-descriptor/pack-unpack wrappers) were skimmed but are not the focus here.
Emphasis, per the brief, on the class-dispatch design, `archLoad`/`archSave`
serialization, hostile-input parsing, and integer-overflow / asymmetry in
domain distance/size arithmetic.

`SCOTCH_archBuild` / `SCOTCH_archVar` being undocumented in the manuals was
already reported by another analyst and is not repeated here.

## Architecture (the design)

**Class dispatch via a virtual method table.** `arch.h` defines `ArchClass`
(lines 152-172), a struct of ~18 function pointers: load/save/free for the arch
itself, a matching triple (`matchInit`/`matchExit`/`matchMate`) used for
architecture coarsening, and the domain operations
`domNum`/`domTerm`/`domSize`/`domWght`/`domDist`/`domFrst`/`domLoad`/`domSave`/`domBipart`/`domIncl`,
plus `domsizeof`. Every concrete arch supplies a family of `arch<Name>...`
functions, and the `ARCHCLASSBLOCK(n,s,f)` macro (arch.h:295-312) token-pastes
those names into one table row, casting each to the generic pointer type. The
master table `archClassTab[]` (arch.c:102-119) lists 17 rows: cmplt, cmpltw,
deco, deco2 (hidden), dist, hcub, tleaf, ltleaf, mesh2D/3D/XD, sub, torus2D/3D/XD,
varcmplt, varhcub.

**Domain representation.** `ArchDom` (arch.h:216-218) is a fixed-size union
(`ArchDomDummy`, arch.h:200-212) large enough for the widest concrete domain;
`archDomSizeof()` returns the real per-class byte size. This is why PyScotch
must size domain buffers dynamically. The dispatch macros
`archDomNum2`/`archDomDist2`/etc. (arch.h:275-282) call through the table with
the arch/domain pointers cast to `void *`; in non-debug builds these are the
real entry points (the `arch.c` wrappers exist only under
`SCOTCH_DEBUG_ARCH2`).

**Serialization.** `archSave` (arch.c:229-247) writes the class `archname` as a
text token then delegates to the class `archSave`. `archLoad` (arch.c:189-221)
reads a `%255s` name, resolves it with `archClass()` (case-insensitive
`strcasecmp`, arch.c:271-274), sets `ARCHFREE`, then calls the class loader.
Format is whitespace-separated ASCII integers via `intLoad`/`fscanf` — e.g.
cmplt is a single count, mesh2D is two dims, tleaf is `levlnbr` followed by
`(size,link)` pairs, meshX is `dimnnbr` then that many dims. Variable-sized
archs (vcmplt, vhcub) have `archLoad == NULL` (arch_vcmplt.h:91,
arch_vhcub.h:84): they carry no data, so they serialize as just the class name.
torus{2,3,X} reuse the mesh loaders/savers by macro alias (arch_torus.h:102-144),
differing only in `domDist` (wrap-around Manhattan distance).

**The `deco` decomposition-defined arch.** `arch_deco.c` stores an
architecture derived from an arbitrary decomposition graph: a terminal-vertex
table plus a full lower-triangular terminal-to-terminal distance matrix. Its
loader (`archDecoArchLoad`) branches on a leading `typeval` (0 = raw, 1 =
compiled, 2 = hand off to the newer `arch_deco2` type). Type-2 switches the
class pointer to the hidden `Deco2` row via `archClass2("deco", 1)`
(arch.c:105). `deco2` is the memory-frugal successor that stores distances
implicitly.

**The `sub` sub-architecture.** `arch_sub.c` is a meta-arch: it wraps a parent
arch and a vertex-subset list, remapping terminal numbers so a partition can
target a slice of a larger machine. The test suite builds sub-archs of every
other type (and of sub-archs), exercising the delegation.

## Code-quality observations

- The `arch_*.c` files are near-twins; the `ARCHCLASSBLOCK` macro plus the
  `#define arch<X>Fn NULL`/alias headers keep the dispatch table honest and
  make copy-paste divergence unlikely at the *table* level. I found no
  mismatched-slot bug (e.g. a `DomDist` wired to the wrong type's function).
- Input validation is **inconsistent across the twins**: some loaders bound
  both ends of a count, others only one (see Findings F2, F3). This is the main
  quality weakness in the territory.
- `archCmpltwArchSave` (arch_cmpltw.c:298-313) contains dead code: an
  `if (verttmp == archptr->vertnbr)` internal-error check placed *inside* a
  `for (verttmp = 0; verttmp < archptr->vertnbr; ...)` loop — the condition can
  never hold because the loop already exited. Harmless, but signals the
  invariant is not actually being checked.
- Overflow-guarded arithmetic is the exception, not the rule: terminal/vertex
  counts are built by repeated multiplication with no saturation check (tleaf
  `sizeval *= sizetab[]`, mesh product terms, deco distance-matrix sizing).

## Findings

### F1 — `archCmpltwArchLoad`: heap leak of `vecwtab` on malformed weight input — confidence HIGH

`external/scotch/src/libscotch/arch_cmpltw.c:243-257`

```c
  for (vertnum = 0, velosum = 0; vertnum < vertnbr; vertnum ++) {
    long                velotmp;
    Anum                veloval;

    if ((fscanf (stream, "%ld", &velotmp) != 1) ||
        (velotmp < 1)) {
      errorPrint ("archCmpltwArchLoad: bad input (2)");
      return (1);                                 /* <-- vecwtab NOT freed */
    }
    veloval = (Anum) velotmp;
    if (veloval <= 0) {                           /* Target weights cannot be negative nor null */
      errorPrint ("archCmpltwArchLoad: bad input (3)");
      memFree    (vecwtab);                        /* <-- this path DOES free */
      return (1);
    }
```

Mechanism: `vecwtab` is allocated at line 238 before the read loop. The first
rejection path (bad/short weight, `velotmp < 1`) returns without `memFree`,
leaking the buffer; the second path (line 253) frees correctly. Any truncated
or non-numeric weight in a loaded `cmpltw` architecture file leaks
`vertnbr * sizeof(ArchCmpltwLoad)` bytes. Not memory-unsafe, but a
loader-driven leak, and directly reachable through `SCOTCH_archLoad` on a
`cmpltw` file — which PyScotch exposes.

### F2 — `archMeshXArchLoad`: missing lower bound on `dimnnbr` — confidence MEDIUM

`external/scotch/src/libscotch/arch_mesh.c:634-638`

```c
  if ((intLoad (stream, &archptr->dimnnbr) != 1) ||
      (archptr->dimnnbr > ARCHMESHDIMNMAX)) {
    errorPrint ("archMeshXArchLoad: bad input (1)");
    return     (1);
  }
```

Mechanism: only the upper bound is checked (`> ARCHMESHDIMNMAX`, which is 5,
arch_mesh.h:81). A zero or negative `dimnnbr` is accepted. The dimension read
loop `for (dimnnum = 0; dimnnum < archptr->dimnnbr; ...)` then never executes,
leaving `archptr->c[]` uninitialized while the arch is reported as loaded OK.
Downstream `domFrst`/`domNum` loops also skip, yielding degenerate domains from
uninitialized data. Contrast `archHcubArchLoad` (arch_hcub.c:104-108) which
correctly checks `dimnnbr < 1`. No buffer overflow (fixed `c[5]` array, upper
bound enforced), so this is a robustness/validation gap rather than a memory
bug — hence MEDIUM.

### F3 — `archTleafDomLoad` / `archMeshXDomLoad`: domain coordinates not bounded against the architecture — confidence MEDIUM

`external/scotch/src/libscotch/arch_tleaf.c:532-548`

```c
  if ((intLoad (stream, &domnptr->levlnum) != 1) ||
      (intLoad (stream, &domnptr->indxmin) != 1) ||
      (intLoad (stream, &domnptr->indxnbr) != 1) ||
      (domnptr->levlnum < 0)                     ||
      (domnptr->levlnum > archptr->levlnbr)) {
    errorPrint ("archTleafDomLoad: bad input");
    return     (1);
  }
```

`external/scotch/src/libscotch/arch_mesh.c:960-968`

```c
    if ((intLoad (stream, &domptr->c[dimnnum][0]) != 1) ||
        (intLoad (stream, &domptr->c[dimnnum][1]) != 1) ||
        (domptr->c[dimnnum][0] > domptr->c[dimnnum][1])  ||
        (domptr->c[dimnnum][0] < 0)) {
      errorPrint ("archMeshXDomLoad: bad input");
      return     (1);
    }
```

Mechanism: tleaf validates `levlnum` but never checks that `indxmin`/`indxnbr`
fall within the level's block size — a hostile `indxmin` (large or negative)
flows into `archTleafDomNum` (`domnptr->indxmin * sizeval`, tleaf.c:377) and,
for the labeled variant, `archLtleafDomNum` uses it in a `% archptr->permnbr`
and a `permtab[]`/`peritab[]` index (tleaf.c:799-801, 831). Similarly meshX
rejects `c[i][0] < 0` and inverted ranges but does **not** check
`c[i][1] < archptr->c[dimnnum]`, so a domain may claim coordinates outside the
mesh, producing out-of-range terminal numbers from `archMeshXDomNum`. Contrast
`archCmpltDomLoad` (arch_cmplt.c:343-349) and `archCmpltwDomLoad`
(arch_cmpltw.c:481-488), which *do* reject `termnbr + termmin > archptr->termnbr`.
The asymmetry is the finding; whether any caller feeds untrusted `.map`/domain
files determines severity, so MEDIUM.

### F4 — `archDecoArchLoad`: unchecked `termdommax` in distance-matrix allocation size — confidence MEDIUM

`external/scotch/src/libscotch/arch_deco.c` (type-0 branch, allocation)

```c
    if (memAllocGroup ((void **) (void *)
                       &termverttab, (size_t) (termdomnbr * sizeof (ArchDecoTermVert)),
                       &termdisttab, (size_t) ((((termdommax * (termdommax - 1)) / 2) + 1) * sizeof (Anum)), NULL) == NULL) {
```

Mechanism: `termdommax` is read from the file and only lower-bounded
(`termdommax >= termdomnbr >= 1`); there is no upper bound. The size expression
`termdommax * (termdommax - 1) / 2` is computed in `INT` arithmetic and can
overflow for large `termdommax`, producing a too-small (or wrapped) allocation.
The type-1 (compiled) branch has the identical expression for
`domdisttab` and then reads `(termdommax*(termdommax-1))/2` entries into it —
an overflowed size there is a heap out-of-bounds write. Exploitability depends
on the width of Scotch `INT` (64-bit builds need an infeasibly large value that
`memAllocGroup` would reject; 32-bit-`INT` builds overflow around
`termdommax ≈ 92682`). Because `deco` files are typically machine-generated and
the overflow needs a hostile hand-crafted file, MEDIUM. Noting it because the
arithmetic is genuinely unchecked and the write loop trusts it.

### F5 — `archDistArchLoad`: distance multiplier `crloval` not validated — confidence LOW

`external/scotch/src/libscotch/arch_dist.c` (`archDistArchLoad`)

```c
  if (intLoad (stream, &archptr->crloval) != 1) {
    errorPrint ("archDistArchLoad: bad input");
    return     (1);
  }
  return (archLoad (archptr->archptr, stream));   /* Load sub-architecture */
```

Mechanism: `crloval` (the distance multiplier) is accepted with no range check;
a zero or negative value makes `archDistDomDist` return zero/negative
distances, corrupting the mapping cost model rather than crashing. `dist` has
no public `SCOTCH_arch*` builder, so this is only reachable via a crafted
loaded file; LOW.

No memory-safety defect was found in the dispatch layer itself
(`arch.c`/`arch.h`), in the torus/mesh `domDist` functions (the
`c[i][0]+c[i][1]` center sums can overflow only with near-`INT_MAX`
coordinates, which the loaders' `>= 1` / range checks make unreachable in
practice), or in the `sub`/`hcub` loaders (`hcub` bounds `dimnnbr` on both
ends). "No further findings" for those.

## Test coverage

Two C tests touch this territory, both in `external/scotch/src/check/`:

- **`test_scotch_arch.c`** — a save/load round-trip smoke test. It builds one
  instance each of: **hcub, cmplt, mesh2D, mesh3D, meshXD, tleaf, torus2D,
  torus3D, torusXD, sub** (and a sub of each), saves them all to a file, exits
  them, then reloads (test_scotch_arch.c:93-184). It verifies only that
  `archSave`→`archExit`→`archInit`→`archLoad` return 0. It does **not** call
  `archDomDist`, `archDomBipart`, `archDomNum`, `archDomIncl`, etc., so the
  domain arithmetic — where the Findings above live — is entirely unexercised.
- **`test_scotch_arch_deco.c`** — builds decomposition-defined archs via
  `SCOTCH_archBuild0`/`archBuild2` and a `sub` of one, then saves them
  (test_scotch_arch_deco.c:134-159). Covers **deco / deco2** construction and
  save.

**Arch types with a public `SCOTCH_arch*` builder but NO test at all**
(absent from both files): **`cmpltw`** (weighted complete — the F1 leak lives
here), **`ltleaf`** (labeled tree-leaf — the permutation path in F3),
**`vcmplt`** (varcmplt), **`vhcub`** (varhcub). `dist` is an internal pseudo-arch
with no public builder and is likewise untested. So the two arch types with the
most parsing logic and the weakest validation (cmpltw, ltleaf) have zero direct
coverage, and no test anywhere checks a `domDist`/`domBipart`/`domIncl` result
value. This matches the CLAUDE.md warning that Scotch C tests verify return
codes, not output validity.

## PyScotch relevance

PyScotch wraps `archCmplt`, `archCmpltw`, `archHcub`, `archMesh(X)`,
`archTorus(X)`, `archTleaf`, `archVcmplt`, `archVhcub` over ctypes.

- **Serialization round-trip.** `archLoad`/`archSave` is plain
  whitespace-delimited ASCII. Variable-sized archs (`vcmplt`, `vhcub`) persist
  as *only* their class name (`archLoad == NULL`); a PyScotch round-trip that
  assumes a numeric payload for those will mis-parse. When feeding
  Python-generated architecture files into `SCOTCH_archLoad`, treat every
  count/dimension as attacker-controlled and pre-validate on the Python side —
  the C loaders are inconsistent about bounds (F2, F3, F4).
- **Weighted-arch (cmpltw) input.** F1 makes a malformed weight list leak
  memory inside the C loader. If PyScotch builds `cmpltw` archs by writing a
  temp file and calling `SCOTCH_archLoad` (rather than `SCOTCH_archCmpltw` with
  an in-memory array), a bad weight leaks; prefer the in-memory builder
  `SCOTCH_archCmpltw`, whose `archCmpltwArchBuild` path (arch_cmpltw.c:157-205)
  validates `veloval <= 0` and frees on error. Note all weights must be
  strictly positive (`veloval <= 0` rejected).
- **Domain size / coordinate limits.** F3 means a domain read from a file can
  legally exceed the architecture bounds for tleaf/meshX. If PyScotch ever
  exposes `archDomLoad`, wrap it with a Python-side range assertion against the
  arch dimensions. Terminal-count products (tleaf `sizeval`, mesh dim products)
  are unchecked for overflow — cap the product of tleaf level sizes / mesh
  dimensions in Python before handing them to Scotch.
- Property-based tests (the repo's Hypothesis suite) are the right place to
  cover the domain-arithmetic gap the C tests leave open: round-trip
  `archSave`/`archLoad` for **cmpltw, ltleaf, vcmplt, vhcub** (currently
  untested upstream), and assert `archDomDist` symmetry / non-negativity across
  random domain pairs.
