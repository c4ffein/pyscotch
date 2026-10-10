# Licences

PyScotch is distributed under the MIT License (see `../LICENSE`).

PyScotch bundles, patches and redistributes parts of Scotch / PT-Scotch,
© Inria (François Pellegrini and the Scotch team), licensed under the
CeCILL-C free/libre software license (see `CeCILL-C_V1-en.txt` in this directory):

  * binary wheels bundle libscotch, libscotcherr (and the PyScotch compat
    shim) built from the Scotch sources — pyscotch/_libs/;
  * pyscotch/_scotch_patches/ contains small patches to Scotch sources that
    `pyscotch scotch build` may apply, each documented in its README;
  * tests/data/m16x16_b100000_v.grf is a test graph copied verbatim from
    Scotch's src/check/data/.

Scotch's own distribution and licence terms: https://gitlab.inria.fr/scotch/scotch
