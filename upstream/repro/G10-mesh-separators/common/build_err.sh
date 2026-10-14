#!/bin/sh
# Same as build.sh but links the NON-exiting error handler (-lscotcherr), for fault injection runs.
B=$1; gcc -g -O0 -fsanitize=address,undefined -fno-omit-frame-pointer -I$B/include "$2" -o "$3" -L$B/lib -lscotch -lscotcherr -Wl,-rpath,$B/lib -lm -lz -lpthread
