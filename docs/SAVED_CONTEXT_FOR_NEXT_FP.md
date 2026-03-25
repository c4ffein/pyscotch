● Interesting! Hypothesis found a potential bug!

  The test found that for a graph with 19 vertices and a single edge (0, 9), the color() function assigned the same color
  (0) to both adjacent vertices 0 and 9. This is a violation of the fundamental graph coloring property.

  However, the failure is marked as "Flaky" - it failed initially but couldn't reproduce on retry. This suggests the
  coloring algorithm in Scotch may be non-deterministic (perhaps using internal randomness).

  Let me investigate further:

● Bash(python3 -c "                timeout: 1m 0s
      from pyscotch import Graph…)
  ⎿  Run 1: color[0]=1, color[9]=0, same=False, num_colors=2
     Run 2: color[0]=1, color[9]=0, same=False, num_colors=2
     Run 3: color[0]=0, color[9]=0, same=True, num_colors=1
     … +19 lines (ctrl+o to expand)

● This is a genuine bug in Scotch's SCOTCH_graphColor function!

  The bug is reproducible - about 50% of the time, graphColor returns an invalid coloring where adjacent vertices 0 and 9
  are assigned the same color 0. The bug appears to be related to:
  1. A sparse graph (19 vertices but only 1 edge)
  2. Non-deterministic behavior in Scotch's internal random number generator

  Let me check if resetting the random seed helps and understand the root cause better:

● Bash(python3 -c "                timeout: 1m 0s
      from pyscotch import Graph…)
  ⎿  <string>:23: SyntaxWarning: invalid escape sequence '\!'
     With SCOTCH_randomReset() before each run:
     Run 1: color[0]=1, color[9]=0, same=False, num_colors=2
     … +9 lines (ctrl+o to expand)

● When the random seed is reset before each call, the coloring is consistent and correct. Without the reset, certain random
  states lead to an incorrect coloring.

  Let me test a few more graph shapes to see if this is specific to very sparse graphs:

● Bash(python3 -c "                timeout: 1m 0s
      from pyscotch import Graph…)
  ⎿  Testing various sparse graphs (10 runs each, no random reset):
       19 vertices, edge (0, 9): 5/10 failures
       10 vertices, edge (0, 5): 5/10 failures
     … +3 lines (ctrl+o to expand)

● This is a confirmed bug in Scotch's SCOTCH_graphColor function affecting sparse graphs! The bug occurs approximately 50%
  of the time across various sparse graph configurations when the internal random state is in certain states.

● Summary

  The Hypothesis property tests found a genuine bug in Scotch's SCOTCH_graphColor function:

  Bug Details

  | Aspect             | Details                                                                |
  |--------------------|------------------------------------------------------------------------|
  | Affected function  | SCOTCH_graphColor                                                      |
  | Symptom            | Returns invalid colorings where adjacent vertices share the same color |
  | Trigger            | Sparse graphs (graphs with few edges relative to vertices)             |
  | Frequency          | ~50% of calls without SCOTCH_randomReset()                             |
  | Workaround         | Call SCOTCH_randomReset() before graphColor()                          |
  | Minimal reproducer | 19 vertices, single edge (0,9)                                         |

  Test Results

  - 9/10 tests passed (ordering, partitioning, graph validity)
  - 1 test found a bug (coloring validity)

  Next Steps

  1. This should be reported to the Scotch team (add to QUESTIONS_FOR_SCOTCH_TEAM.md)
  2. The test file is at tests/hypothesis/test_graph_properties.py
  3. Consider adding SCOTCH_randomReset() before coloring in the Python wrapper as a workaround

  Would you like me to add this bug to QUESTIONS_FOR_SCOTCH_TEAM.md?

> No. This is perfect already. I'll just show this context to Francois (the author), and we'll check with him if this is a
bug in scotch, pyscotch, or a misunderstanding from our side.

● Sounds good. The key findings to share with François:

  1. Minimal reproducer: 19 vertices, 1 edge (0,9) → graphColor assigns same color to both endpoints ~50% of the time
  2. Workaround: SCOTCH_randomReset() before each call makes it deterministic and correct
  3. Hypothesis found it by testing the invariant "no adjacent vertices share a color" across random graph structures

  The test file is ready at tests/hypothesis/test_graph_properties.py if you want to show him the exact test that caught it.
   Good luck with the discussion!

> Hey, I wonder if the problem is not just that we should automatically call SCOTCH_randomReset from our side automatically.
 Will check with him, and he'll discover /hypothesis for the next real bugs, will be fun.

● That's a fair point - it could just be that graphColor (and possibly other randomized algorithms) expects the caller to
  manage the random state, and the Python wrapper should handle that automatically to provide deterministic behavior by
  default.

  Either way, you've got a nice demo of /hypothesis in action for François. Finding edge cases in graph algorithms with 3
  lines of property definition is pretty compelling. Have fun!
