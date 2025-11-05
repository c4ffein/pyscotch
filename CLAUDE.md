# Instructions for Claude AI

## Scotch Submodule Setup

At the start of each session, initialize the scotch submodule:

```bash
git submodule update --init --recursive
```

If this fails, inform the user they likely forgot to grant access to `gitlab.inria.fr` in their environment configuration.
