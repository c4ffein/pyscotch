#!/bin/sh
# usage: failscan.sh <program and args...>   (program built with -lscotcherr, ASan)
# Runs the program once to count allocations, then once per allocation index with that allocation failing.
# Reports every run that shows an ASan/LSan error, a crash, or a successful return despite the injected failure.
FM=$(dirname "$0")/failmalloc.so
export ASAN_OPTIONS=verify_asan_link_order=0:detect_leaks=1
export UBSAN_OPTIONS=print_stacktrace=0
total=$(FAIL_COUNT=1 LD_PRELOAD=$FM "$@" 2>&1 | sed -n 's/^FAILMALLOC calls=//p')
echo "total allocations: $total"
bad=0; errs=0; leaks=0
for k in $(seq 1 $total); do
  out=$(FAIL_NTH=$k LD_PRELOAD=$FM "$@" 2>&1); rc=$?
  tag=""
  echo "$out" | grep -q "attempting free\|heap-buffer-overflow\|SEGV\|heap-use-after-free\|stack-overflow\|double-free\|runtime error" && tag="$tag ASAN"
  echo "$out" | grep -q "LeakSanitizer" && tag="$tag LEAK"
  if [ -n "$tag" ]; then bad=$((bad+1)); echo "N=$k rc=$rc:$tag :: $(echo "$out" | grep -m1 "ERROR: \|runtime error" | cut -c1-120)"; fi
done
echo "runs with sanitizer findings: $bad / $total"
