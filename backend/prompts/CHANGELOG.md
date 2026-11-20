# Prompt changelog

The active version is set by the `PROMPT_VERSION` environment variable (default `v2.1`). Every report returns the version it used in `llm.prompt_version`, and every log and trace line carries it.

Published versions are never edited. A change means a new file, a new entry in `PROMPT_VERSIONS` in `__init__.py`, and a line here.

## v2.1 (2026-11-20)

- When the technical and fundamental scores conflict, the summary's second paragraph must begin with "Mixed signals:" and explain the tension using the two scores.
- Otherwise identical to v2.0.

## v2.0 (2026-11-20)

- The prompt used by Quantum v2.0.0, moved out of `master_agent.py` into a template file without changing its wording.
- Asks for one sentence per list item in `key_drivers`, `bull_case` and `bear_case`, because `gpt-oss-20b` was packing several points into one string.
