#!/bin/sh
# Usage: build.sh <scotch-tree-with-include-and-lib> ; builds the harnesses against that tree (ASan+UBSan)
T=$1; D=$(dirname "$0")
CF="-O0 -g -fsanitize=address,undefined -fno-omit-frame-pointer"
gcc $CF -I$T/include -o $D/archload $D/archload.c -L$T/lib -lscotch -lscotcherr -lm -lpthread -lz &&
gcc $CF -I$T/include -o $D/archtrip $D/archtrip.c -L$T/lib -lscotch -lscotcherr -lm -lpthread -lz &&
gcc $CF -I$T/include -o $D/subapi   $D/subapi.c   -L$T/lib -lscotch -lscotcherr -lm -lpthread -lz &&
gcc $CF -DSCOTCH_RENAME -DCOMMON_PTHREAD -DSCOTCH_PTHREAD -I$T/src/libscotch -I$T/include -o $D/../COR-27/mate $D/../COR-27/mate.c -L$T/lib -lscotch -lscotcherr -lm -lpthread -lz &&
gcc $CF -I$T/include -o $D/../PS2-G01-1/build2one $D/../PS2-G01-1/build2one.c -L$T/lib -lscotch -lscotcherr -lm -lpthread -lz && echo "harnesses built"
