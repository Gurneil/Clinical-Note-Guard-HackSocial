"""
Central place for 'which model does which job, and why'. Change a node's
model here rather than hunting through pipeline.py — this file is also
what backs the required 'which LLM model is used at each stage' section
of the submission documentation.

All models below are free-tier Gemini models (no cost, no credit card).
"""
import json
import os

_TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "..", "taxonomy.json")
with open(_TAXONOMY_PATH) as f:
    TAXONOMY = json.load(f)

# --- Model assignment per node -------------------------------------------
# Flash-Lite is used for structural, low-ambiguity tasks (pulling claims
# out of text, picking one label from a fixed list) where speed matters
# more than deep reasoning. Flash is used for the two steps that need
# more careful judgment: drafting the note in the first place, and
# deciding whether a specific claim is actually supported by the
# transcript (this is the step doing the real verification work).
#
# NOTE: gemini-2.5-flash is no longer issued to new API keys as of when
# this was tested (confirmed via a live 404 from the API) - Google has
# moved new accounts onto the 3.x generation. gemini-3.6-flash and
# gemini-3.5-flash-lite are both still free-tier (Flash-family models
# stay free; only the Pro tier requires billing).
MODEL_DRAFT = "gemini-3.6-flash"
MODEL_EXTRACT = "gemini-3.5-flash-lite"
MODEL_ENTAILMENT = "gemini-3.6-flash"
MODEL_CLASSIFY = "gemini-3.5-flash-lite"

# IMPORTANT: the single-prompt baseline uses the SAME model as the
# pipeline's strongest node (Flash), not a weaker model. This is
# deliberate - if the baseline used a worse model, any improvement from
# the pipeline could just be "we used a better model," not "the workflow
# helps." Comparing workflow vs. single-prompt on the SAME underlying
# model is what makes the comparison actually mean something.
MODEL_BASELINE = "gemini-3.6-flash"
