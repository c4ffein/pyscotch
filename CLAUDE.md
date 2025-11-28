# Instructions for Claude AI

## Scotch Submodule Setup
- At the start of each session, initialize the scotch submodule: `git submodule update --init --recursive`
- If this fails, inform the user they likely forgot to grant access to `gitlab.inria.fr` in their environment configuration.

## Testing strategy
- When importing a test from Scotch, maximize the similarity with the existing test. NEVER PUT THE DUST UNDER THE RUG.
- ALWAYS KEEP THE EXACT SAME ASSERTIONS. THE TESTS **NEVER** ARE THE PROBLEM. DON'T TRY TO MODIFY THE TEST. FIX THE IMPLEMENTATION.
- But WHEN YOU THINK A TEST IS INCOMPLETE, and COULD BE MORE COMPREHENSIVE, you can add notes to the `QUESTIONS_FOR_SCOTCH_TEAM.md` file! We'll get back to them so they can potentially improve the tests with your help :)

## GENERAL ADVICE - PLEASE TAKE NOTE
- YOU ARE NOT SUPPOSED TO BE POSITIVE WHEN SOMETHING FAILS.
- IF YOU CAN'T FIX SOMETHING, YOU JUST STOP AND ASK THE USER TO LOOK INTO IT.
