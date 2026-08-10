"""
Live-demo entry point: draft -> guard -> human review, end to end, against
a real transcript. This is the only way to actually run
pipeline.run_full_pipeline() from the command line - previously it was
only reachable via a hand-typed `python -c "..."` one-liner, which isn't
workable to type live in front of an audience.

Usage:
    python demo.py                  interactive menu, pick a benchmark transcript
    python demo.py 3                run benchmark case #3 directly
    python demo.py --no-review      skip the interactive y/n human review
                                     (auto-lists flags instead of prompting)
"""
import json
import os
import sys

# Windows terminals often default to a non-UTF-8 console codepage (cp1252/
# cp437), which mangles characters like the degree sign a model's output
# can legitimately contain (e.g. "100.4°F") into "100.4?F" mid-demo.
# reconfigure() is a no-op on platforms/terminals that are already UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pipeline import run_full_pipeline  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "test_cases.json")


def load_cases():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)["cases"]


def pick_case(cases):
    print("Pick a transcript to run through the full live pipeline")
    print("(draft note -> guard -> human review):\n")
    for i, c in enumerate(cases, 1):
        print(f"  {i:2d}. {c['id']}  ({c['specialty']})")
    while True:
        choice = input(f"\nCase number (1-{len(cases)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(cases):
            return cases[int(choice) - 1]
        print("Not a valid case number, try again.")


def main():
    interactive_review = "--no-review" not in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    cases = load_cases()

    if args and args[0].isdigit() and 1 <= int(args[0]) <= len(cases):
        case = cases[int(args[0]) - 1]
    else:
        case = pick_case(cases)

    print(f"\n{'=' * 70}\nRunning: {case['id']}  ({case['specialty']})\n{'=' * 70}")
    print("\n--- TRANSCRIPT ---\n")
    print(case["transcript"])

    print(f"\n{'=' * 70}\nDrafting note, then checking it against the transcript...\n{'=' * 70}\n")
    result = run_full_pipeline(case["transcript"], interactive=interactive_review)

    print(f"\n{'=' * 70}\nDRAFTED NOTE\n{'=' * 70}\n")
    print(result["draft_note"])

    guard = result["guard_result"]
    print(f"\n{'=' * 70}\nGUARD SUMMARY\n{'=' * 70}")
    print(f"Claims checked (note vs. transcript): {len(guard['claims_checked'])}")
    print(f"Transcript facts checked (omission):  {len(guard['transcript_facts_checked'])}")
    print(f"Total flags raised:                   {len(guard['all_flags'])}")
    print(f"Core-reasoning provider/model:         {guard['core_reasoning_provider']}/{guard['core_reasoning_model']}")

    review = result["review"]
    print(f"\nReview status: {review['note_status']}")
    print(f"Flags confirmed by reviewer: {len(review['approved_flags'])}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nDemo stopped.")
    except RuntimeError as e:
        print(f"\n\n[ERROR] {e}")
        print("Check that at least one API key is set - see .env.example and smoke_test.py.")
        sys.exit(1)
