"""
Generates docs/workflow_flowchart.png - the required submission asset
showing the full pipeline: which steps need a human, which are LLM
calls (and which model/chain backs each one), which are plain code, and
what each node does. Built programmatically (matplotlib, no Graphviz
binary dependency) so it can be regenerated any time pipeline.py or
config.py changes, rather than hand-maintained as a static image that
silently drifts out of sync with the code.

This script is a documentation/dev tool, not part of the runtime
pipeline - matplotlib is not a project dependency, only a dev-time one
for this script. Run:
    D:\\Python312\\python.exe -m pip install matplotlib
    D:\\Python312\\python.exe docs\\generate_flowchart.py
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

OUT_PATH = os.path.join(os.path.dirname(__file__), "workflow_flowchart.png")

# Color scheme: distinguishes WHO/WHAT does each node at a glance.
COLOR_HUMAN = "#2b6cb0"      # human-in-the-loop steps
COLOR_LLM_CORE = "#c05621"   # fairness-linked core-reasoning LLM calls
COLOR_LLM_MECH = "#2f855a"   # mechanical-tier LLM calls (no fairness link)
COLOR_CODE = "#4a5568"       # plain code, no LLM
COLOR_BASELINE = "#805ad5"   # the comparison baseline
COLOR_AUDIO = "#b83280"      # optional audio path (--audio only)
BG = "white"


def box(ax, xy, w, h, text, color, fontsize=9.5, text_color="white"):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.5, edgecolor=color, facecolor=color, alpha=0.92,
        mutation_aspect=1,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fontsize, color=text_color, wrap=True, linespacing=1.35)
    return (x + w / 2, y), (x + w / 2, y + h)  # (bottom-center, top-center)


def arrow(ax, start, end, color="#2d3748", style="-|>", lw=1.6, connectionstyle="arc3,rad=0.0"):
    a = FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=14,
                         color=color, lw=lw, connectionstyle=connectionstyle, zorder=1)
    ax.add_patch(a)


def main():
    W, H = 12.5, 15.9
    fig, ax = plt.subplots(figsize=(W, H), dpi=200)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    fig.patch.set_facecolor(BG)

    ax.text(W / 2, H - 0.35, "Clinical Note Hallucination Guard \u2014 Workflow", ha="center",
            fontsize=17, fontweight="bold", color="#1a202c")
    ax.text(W / 2, H - 0.75, "Draft \u2192 decompose \u2192 independently verify \u2192 classify \u2192 human checkpoint",
            ha="center", fontsize=10.5, color="#4a5568", style="italic")

    col_w = 5.6
    left_x = 0.5
    x_center = left_x + col_w / 2

    # Top-down cursor for the left (main pipeline) column - every box is
    # placed relative to the previous one, so resizing any single box
    # never requires re-deriving every coordinate below it by hand.
    cursor = H - 1.35
    gap = 0.3

    def place(height, text, color, fontsize=9.5):
        nonlocal cursor
        top = cursor
        bottom = top - height
        b, t = box(ax, (left_x, bottom), col_w, height, text, color, fontsize=fontsize)
        cursor = bottom - gap
        return b, t

    # --- Node 0: Transcript input (human, or ASR when --audio) ---
    b0, t0 = place(1.0,
                   "0. TRANSCRIPT INPUT\nHuman-sourced data (patient + clinician conversation)\n"
                   "or, with --audio: Whisper via Groq → text + per-segment confidence",
                   COLOR_HUMAN, fontsize=9)

    # --- Node 1: Draft note ---
    b1, t1 = place(1.15,
                    "1. DRAFT NOTE  (live demo only, not in eval)\n"
                    "LLM \u2014 DRAFT_CHAIN:\ngemini-3.6-flash \u2192 Groq \u2192 Featherless\n"
                    "Simulates an ambient scribe producing a SOAP note",
                    COLOR_LLM_MECH)
    arrow(ax, b0, t1)

    label_y_1 = (b1[1] - gap / 2)
    ax.text(x_center, label_y_1, "note_under_test", ha="center", fontsize=8.5,
            style="italic", color="#718096")

    # --- Node 2: extract claims ---
    b2, t2 = place(1.15,
                    "2. EXTRACT CLAIMS\nLLM \u2014 EXTRACT_CHAIN:\nGroq llama-3.1-8b-instant \u2192 Featherless\n"
                    "Note \u2192 atomic, checkable claims",
                    COLOR_LLM_MECH)
    arrow(ax, b1, t2)

    # --- Node 3: entailment check (core reasoning, fairness-linked) ---
    b3, t3 = place(1.3,
                    "3. ENTAILMENT CHECK (batched, 1 call/case)\n"
                    "LLM \u2014 CORE_REASONING_CHAIN:\ngemini-3.6-flash \u2192 Groq \u2192 Featherless\n"
                    "FAIRNESS-LINKED to the baseline (same tier, always)\n"
                    "Claims vs. transcript \u2192 supported /\ncontradicted / not_mentioned",
                    COLOR_LLM_CORE)
    arrow(ax, b2, t3)
    node3_fairness_y = b3[1] + 1.3 * 0.5  # mid-height, used by the fairness-link arrow below

    # --- Node 3b: transcript confidence (only fires on --audio runs) ---
    b3b, t3b = place(1.25,
                     "3b. TRANSCRIPT CONFIDENCE  (--audio runs only)\n"
                     "Plain Python — NO LLM\n"
                     "Joins each verdict to the audio it rested on. A claim\n"
                     "checked against audio the recogniser was unsure of\n"
                     "becomes UNVERIFIABLE, with a timestamp to re-listen to",
                     COLOR_AUDIO, fontsize=8.8)
    arrow(ax, b3, t3b)

    # --- Node 4: deterministic numeric check ---
    b4, t4 = place(0.95,
                    "4. DETERMINISTIC NUMERIC/MED CHECK\n"
                    "Plain Python regex \u2014 NO LLM\n"
                    "Exact-match doses & vitals: note vs. transcript",
                    COLOR_CODE)
    arrow(ax, b3b, t4)
    node4_top_y = t4[1]
    node4_bottom_y = b4[1]

    # --- Node 5: omission check ---
    b5, t5 = place(1.3,
                    "5. OMISSION CHECK (batched, mirror of 2+3)\n"
                    "LLM \u2014 OMISSION_CHAIN:\nGroq llama-3.1-8b-instant \u2192 Featherless\n"
                    "Transcript \u2192 atomic facts \u2192 checked vs. note\n"
                    "Catches OMISSION errors (opposite of node 3)",
                    COLOR_LLM_MECH, fontsize=9)
    arrow(ax, b4, t5)
    ax.text(x_center, b4[1] - gap / 2, "(also reads note + transcript directly)", ha="center",
            fontsize=7.7, style="italic", color="#718096")

    # --- Node 6: classify ---
    b6, t6 = place(1.15,
                    "6. CLASSIFY FLAGGED CLAIMS (batched)\n"
                    "LLM \u2014 CLASSIFY_CHAIN:\nGroq llama-3.1-8b-instant \u2192 Featherless\n"
                    "Only node 3's flags - node 5's are\nalready \"omission\"",
                    COLOR_LLM_MECH, fontsize=9)
    arrow(ax, b5, t6)

    # --- Node 7: human review (human) ---
    b7, t7 = place(1.32,
                    "7. HUMAN REVIEW CHECKPOINT  \u2014  REQUIRED, NOT OPTIONAL\n"
                    "Human\n"
                    "Every flag (commission + numeric + omission + unverifiable),\nwith category\n"
                    "and evidence, must be actively confirmed before it affects\n"
                    "the final note. Nothing is auto-corrected or auto-removed.",
                    COLOR_HUMAN)
    arrow(ax, b6, t7)
    node7_top_y = t7[1]

    # Numeric flags (node 4) also feed node 7 directly - routed as a small
    # dogleg OUTSIDE the box edges (x = left_x, exactly on the border, is
    # the safe boundary - anything to the right of that is box interior/
    # text), clear of every box's text instead of arcing back through
    # nodes 5/6.
    side_x = left_x - 0.28
    arrow(ax, (left_x, node4_bottom_y), (side_x, node4_bottom_y),
          color="#718096", lw=1.1, style="-", connectionstyle="arc3,rad=0.0")
    arrow(ax, (side_x, node4_bottom_y), (side_x, node7_top_y),
          color="#718096", lw=1.1, style="-", connectionstyle="arc3,rad=0.0")
    arrow(ax, (side_x, node7_top_y), (left_x, node7_top_y),
          color="#718096", lw=1.1, style="-|>", connectionstyle="arc3,rad=0.0")

    pipeline_bottom_y = b7[1]

    # ============================================================
    # Right column: the single-prompt baseline (comparison point)
    # ============================================================
    right_x = 7.3
    rw = col_w - 1.6

    ax.text(right_x + rw / 2, label_y_1, "vs.", ha="center", fontsize=13,
            fontweight="bold", color="#805ad5")

    r_cursor = t2[1]  # align baseline column top with node 2's top

    def place_r(height, text, color, fontsize=9):
        nonlocal r_cursor
        top = r_cursor
        bottom = top - height
        b, t = box(ax, (right_x, bottom), rw, height, text, color, fontsize=fontsize)
        r_cursor = bottom - gap
        return b, t

    bB0, tB0 = place_r(1.0,
                        "SINGLE-PROMPT BASELINE\n(comparison point, not part of the pipeline)\n"
                        "Same transcript + note, given directly", COLOR_BASELINE)
    bB1, tB1 = place_r(1.15,
                        "ONE call \u2014 CORE_REASONING_CHAIN\n(same tier as node 3, same case, always)\n"
                        "\"Find any issues\" \u2014 no decomposition,\n"
                        "no forced per-claim coverage,\nno taxonomy",
                        COLOR_LLM_CORE)
    arrow(ax, bB0, tB1)

    # Fairness link annotation between node 3 and the baseline call
    baseline_mid_y = bB1[1] + 1.15 * 0.5
    arrow(ax, (left_x + col_w, node3_fairness_y), (right_x, baseline_mid_y),
          color="#c05621", lw=1.3, style="<|-|>", connectionstyle="arc3,rad=-0.1")
    ax.text((left_x + col_w + right_x) / 2, node3_fairness_y + 0.55,
            "fairness-linked:\nsame provider/model,\nalways", ha="center", fontsize=7.3,
            color="#c05621", style="italic")

    bB2, tB2 = place_r(0.8, "Raw issue list\n(no forced structure)", COLOR_BASELINE)
    arrow(ax, bB1, tB2)

    ax.annotate("scored against\nthe same\nground truth", xy=(right_x + rw / 2, bB2[1]),
                xytext=(right_x + rw / 2, bB2[1] - 1.6), fontsize=8.2, color="#805ad5",
                ha="center", style="italic",
                arrowprops=dict(arrowstyle="-|>", color="#805ad5", lw=1.2,
                                 connectionstyle="arc3,rad=0.25"))

    # ============================================================
    # Legend + footnote, anchored just below the shorter of the two
    # columns' bottoms rather than floating in leftover canvas space.
    # ============================================================
    legend_top_y = pipeline_bottom_y - 0.35

    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_HUMAN, markersize=13,
               label="Human input required"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_LLM_CORE, markersize=13,
               label="LLM \u2014 core-reasoning tier (fairness-linked)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_LLM_MECH, markersize=13,
               label="LLM \u2014 mechanical tier (no fairness constraint)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_CODE, markersize=13,
               label="Plain code, no LLM"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_AUDIO, markersize=13,
               label="Audio path — optional, --audio runs only"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_BASELINE, markersize=13,
               label="Single-prompt baseline (comparison only)"),
    ]
    legend = ax.legend(handles=legend_elements, loc="upper center",
                        bbox_to_anchor=(W / 2, legend_top_y),
                        bbox_transform=ax.transData,
                        ncol=1, frameon=False, fontsize=9.5, handletextpad=0.8, labelspacing=0.7)

    # 6 legend rows at labelspacing 0.7 - clears the legend block rather
    # than landing inside it, which it did when the audio row was added.
    ax.text(W / 2, legend_top_y - 2.25,
            "Every provider/model shown is the FIRST tier tried; each chain automatically fails over\n"
            "(quota/availability errors only) to the next provider listed \u2014 see src/config.py and src/llm_router.py.",
            ha="center", fontsize=8, color="#718096")

    fig.savefig(OUT_PATH, facecolor=BG, bbox_inches="tight")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
