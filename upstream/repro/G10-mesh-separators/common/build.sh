#!/bin/sh
# usage: build.sh <builddir> <src.c> <out>
B=$1; gcc -g -O0 -fsanitize=address,undefined -fno-omit-frame-pointer -I$B/include "$2" -o "$3" -L$B/lib -lscotch -lscotcherrexit -Wl,-rpath,$B/lib -lm -lz -lpthread
