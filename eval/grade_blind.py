"""
Interactive blind grader for scorecard_blind.csv.

Shows one case at a time: the planted error (from the benchmark's ground
truth), then the two systems' outputs as System A and System B, with no
indication of which is which. You answer four questions, it writes the row,
and it saves after EVERY case so you can stop and resume.

The point of the exercise is that you do not know which system you are
grading. blind_key.json holds the mapping and this script never reads it.
Do not open it until compute_metrics.py has run.

Usage:
    python grade_blind.py           grade the next ungraded case
    python grade_blind.py --review  re-grade rows already filled in
    python grade_blind.py --status  progress only, grade nothing

Keys, at any prompt:
    y / n     yes / no
    number    a count (for false positives)
    s         skip this case for now
    q         save and quit
"""
import argparse
import csv
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)
SCORECARD_PATH = os.path.join(BASE, "scorecard_blind.csv")
DATA_PATH = os.path.join(BASE, "..", "data", "test_cases.json")

CAUGHT_COLS = {"A": "A_caught_target_error(1/0)", "B": "B_caught_target_error(1/0)"}
FP_COLS = {"A": "A_false_positive_count", "B": "B_false_positive_count"}
ALL_GRADE_COLS = list(CAUGHT_COLS.values()) + list(FP_COLS.values())

RULE = "=" * 78
THIN = "-" * 78


def load():
    with open(SCORECARD_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames
    with open(DATA_PATH, encoding="utf-8") as f:
        cases = {c["id"]: c for c in json.load(f)["cases"]}
    return rows, fields, cases


def save(rows, fields):
    with open(SCORECARD_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def is_graded(row, has_error):
    cols = ALL_GRADE_COLS if has_error else list(FP_COLS.values())
    return all((row.get(c) or "").strip() for c in cols)


def wrap(text, width=74, indent="    "):
    words, line, out = (text or "").split(), "", []
    for word in words:
        if len(line) + len(word) + 1 > width:
            out.append(indent + line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(indent + line)
    return "\n".join(out) or indent + "(nothing)"


def show_items(cell):
    """One flagged item per line - much easier to count than a pipe-joined blob."""
    items = [i.strip() for i in (cell or "").split("|") if i.strip()]
    if not items or items == ["(nothing flagged)"]:
        return "    (nothing flagged)"
    return "\n".join(wrap(f"{n}. {item}") for n, item in enumerate(items, 1))


def ask(prompt, valid=None, numeric=False):
    while True:
        answer = input(prompt).strip().lower()
        if answer == "q":
            return "q"
        if answer == "s":
            return "s"
        if numeric:
            if answer.isdigit():
                return answer
            print("    Enter a number (0 if none), or s to skip, q to quit.")
            continue
        if valid and answer in valid:
            return answer
        print(f"    Enter one of {'/'.join(valid)}, or s to skip, q to quit.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", action="store_true", help="Include rows already graded.")
    parser.add_argument("--status", action="store_true", help="Show progress and exit.")
    args = parser.parse_args()

    rows, fields, cases = load()

    done = sum(1 for r in rows
               if is_graded(r, cases.get(r["case_id"], {}).get("ground_truth", {}).get("has_error", True)))
    print(f"\n{RULE}\nBLIND GRADING - {done}/{len(rows)} cases graded\n{RULE}")

    if args.status:
        remaining = len(rows) - done
        print(f"\n{remaining} case(s) left. Run without --status to continue.\n")
        return

    print("\nYou are grading System A vs System B without knowing which is which.")
    print("That is the whole point - do not open blind_key.json until you finish.")
    print("\nAt any prompt: 's' skips this case, 'q' saves and quits.\n")

    graded_this_session = 0

    for index, row in enumerate(rows):
        case = cases.get(row["case_id"], {})
        gt = case.get("ground_truth", {})
        has_error = gt.get("has_error", True)

        if is_graded(row, has_error) and not args.review:
            continue

        print(f"\n{RULE}")
        print(f"Case {index + 1} of {len(rows)}   ({row['case_id']})")
        if case.get("specialty"):
            print(f"Specialty: {case['specialty']}")
        print(RULE)

        if has_error:
            err = (gt.get("injected_errors") or [{}])[0]
            print("\nTHE PLANTED ERROR (what a system had to catch):")
            print(f"\n  category:   {err.get('category', '?')}")
            print(f"  wrong text: {err.get('claim_text', '?')}")
            if err.get("correct_value"):
                print(f"  should be:  {err['correct_value']}")
            if err.get("transcript_evidence"):
                print("  transcript says:")
                print(wrap(err["transcript_evidence"], indent="      "))
        else:
            print("\nCLEAN CONTROL - there is NO planted error in this note.")
            print("Anything either system flagged is a false positive.")

        print(f"\n{THIN}\nSYSTEM A flagged:\n{THIN}")
        print(show_items(row["system_A_output"]))
        print(f"\n{THIN}\nSYSTEM B flagged:\n{THIN}")
        print(show_items(row["system_B_output"]))
        print()

        answers = {}
        aborted = False

        if has_error:
            for label in ("A", "B"):
                answer = ask(f"  Did SYSTEM {label} catch the planted error? [y/n] ",
                             valid={"y", "n"})
                if answer in ("q", "s"):
                    aborted = answer
                    break
                answers[CAUGHT_COLS[label]] = "1" if answer == "y" else "0"

        if not aborted:
            for label in ("A", "B"):
                hint = "" if has_error else " (count everything it flagged)"
                answer = ask(f"  How many FALSE POSITIVES did SYSTEM {label} raise?{hint} ",
                             numeric=True)
                if answer in ("q", "s"):
                    aborted = answer
                    break
                answers[FP_COLS[label]] = answer

        if aborted == "q":
            save(rows, fields)
            print(f"\nSaved. {graded_this_session} case(s) graded this session.")
            print("Run `python grade_blind.py` again to pick up where you left off.\n")
            return
        if aborted == "s":
            print("  Skipped.")
            continue

        row.update(answers)
        note = input("  Notes (optional, Enter to skip): ").strip()
        if note:
            row["notes"] = note

        save(rows, fields)  # after every case, so a crash costs one row at most
        graded_this_session += 1
        done += 1
        print(f"  Saved. {done}/{len(rows)} done.")

    print(f"\n{RULE}")
    print(f"All {len(rows)} cases graded. {graded_this_session} in this session.")
    print(RULE)
    print("\nNow score it:\n    python compute_metrics.py")
    print("\nThat is the point at which blind_key.json gets used - not before.\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nStopped. Everything graded so far is already saved.\n")
