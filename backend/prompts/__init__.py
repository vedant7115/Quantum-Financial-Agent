# prompts — versioned prompt templates for the written brief.
#
# Each version is a text file using string.Template placeholders ($name,
# $evidence, $stance, $composite, $confidence, $risk, $conflict, $categories).
# An optional section after a line "[[conflict]]" is inserted as $conflict when
# the report is flagged as conflicted, and is empty otherwise.
#
# The active version comes from the PROMPT_VERSION env var (default below). An
# unknown value falls back to the default with a warning. Changes to a template
# go in a new file and a new entry here, recorded in prompts/CHANGELOG.md;
# published versions are not edited.

import logging
import os
from functools import lru_cache
from pathlib import Path
from string import Template

logger = logging.getLogger("quantum_agent.prompts")

PROMPT_DIR = Path(__file__).resolve().parent
PROMPT_VERSIONS = {
    "v2.0": "brief_v2_0.txt",
    "v2.1": "brief_v2_1.txt",
}
DEFAULT_PROMPT_VERSION = "v2.1"
CONFLICT_MARKER = "\n[[conflict]]\n"


def active_version() -> str:
    wanted = os.getenv("PROMPT_VERSION", DEFAULT_PROMPT_VERSION).strip()
    if wanted in PROMPT_VERSIONS:
        return wanted
    logger.warning(f"Unknown PROMPT_VERSION {wanted!r}; using {DEFAULT_PROMPT_VERSION}")
    return DEFAULT_PROMPT_VERSION


@lru_cache(maxsize=None)
def _load(version: str):
    # Normalise line endings: a Windows checkout may turn the files into CRLF.
    text = (PROMPT_DIR / PROMPT_VERSIONS[version]).read_text(encoding="utf-8").replace("\r\n", "\n")
    body, _, conflict = text.partition(CONFLICT_MARKER)
    return Template(body), conflict.strip()


def render(version: str, *, conflicted: bool, **fields) -> str:
    """The prompt for one report. Raises KeyError if a placeholder is missing."""
    template, conflict_line = _load(version)
    return template.substitute(conflict=("\n" + conflict_line) if (conflicted and conflict_line) else "", **fields)
