#!/bin/sh
# usage: build.sh <build-tree> <out-suffix>   e.g. build.sh $WORK/build 32
B=$1; S=$2; D=$(dirname "$0")/..
for f in SEP-01/partovl SEP-17/partovl API-22/po GRA-01/gra01 GRA-21/gra21 GRA-23/gra23 GRA-23/gra23b GRA-05/gra05; do
  gcc -O0 -g -fsanitize=address,undefined -fno-omit-frame-pointer -I$B/include -o $D/$f.$S $D/$f.c -L$B/lib -lscotch -lscotcherr -lz -lm -lpthread || exit 1
done
echo built-$S
