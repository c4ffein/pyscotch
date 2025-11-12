# Instructions for Claude AI

## Scotch Submodule Setup
- At the start of each session, initialize the scotch submodule: `git submodule update --init --recursive`
- If this fails, inform the user they likely forgot to grant access to `gitlab.inria.fr` in their environment configuration.

## Testing strategy
- When importing a test from Scotch, maximize the similarity with the existing test. NEVER PUT THE DUST UNDER THE RUG.
