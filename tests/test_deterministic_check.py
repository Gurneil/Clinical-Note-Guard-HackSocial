"""
Node 4 (deterministic numeric/medication check) against every case in the
real benchmark. Imports the actual function from pipeline.py rather than
reimplementing the regex, so this test breaks if the real logic breaks -
not just a copy of it.

Run:
    D:\\Python312\\python.exe -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline import deterministic_numeric_check  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "test_cases.json")


class TestDeterministicNumericCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA_PATH, encoding="utf-8") as f:
            cls.cases = {c["id"]: c for c in json.load(f)["cases"]}

    def _flagged_values(self, case_id):
        case = self.cases[case_id]
        flags = deterministic_numeric_check(case["note_under_test"], case["transcript"])
        return {f["flagged_value"] for f in flags}

    def test_numeric_error_case_flags_the_wrong_dose(self):
        flagged = self._flagged_values("case_01_numeric_medication_error")
        self.assertIn("20mg", flagged)
        self.assertNotIn("10mg", flagged)  # the correct dose must not itself be flagged

    def test_clean_control_case_raises_no_flags(self):
        flagged = self._flagged_values("case_06_clean_control")
        self.assertEqual(flagged, set())

    def test_lab_value_is_not_mistaken_for_a_dose(self):
        # Regression test for the bug documented in ARCHITECTURE.md: "58 mg/dL"
        # (a glucose lab value) was originally matched by the dose regex
        # because it starts with "\d+\s*mg". Fixed with a negative lookahead
        # excluding mg/mcg matches immediately followed by a slash.
        flagged = self._flagged_values("case_04_distortion")
        self.assertNotIn("58mg", flagged)

    def test_non_numeric_error_categories_raise_no_deterministic_flags(self):
        # fabrication, negation, and misattribution errors have no numbers in
        # them at all - Node 4 has nothing to check and must stay silent,
        # not guess.
        for case_id in ("case_02_fabrication", "case_03_negation_error",
                         "case_05_misattribution"):
            with self.subTest(case_id=case_id):
                self.assertEqual(self._flagged_values(case_id), set())

    def test_every_case_in_the_benchmark_is_covered(self):
        # Guards against someone adding a new case to test_cases.json without
        # this test suite noticing - if the benchmark grows, this list should
        # too, or a case is silently going untested.
        self.assertEqual(set(self.cases.keys()), {
            "case_01_numeric_medication_error",
            "case_02_fabrication",
            "case_03_negation_error",
            "case_04_distortion",
            "case_05_misattribution",
            "case_06_clean_control",
            "case_07_numeric_medication_error_pediatric_dose",
            "case_08_numeric_medication_error_beta_blocker",
            "case_09_fabrication_allergy_visit",
            "case_10_fabrication_knee_exam",
            "case_11_negation_error_shortness_of_breath",
            "case_12_negation_error_blood_in_stool",
            "case_13_distortion_fever_duration",
            "case_14_misattribution_smoking_history",
            "case_15_omission_otc_medication",
            "case_16_omission_drug_allergy",
            "case_17_clean_control_dermatology",
            "case_18_clean_control_annual_physical",
        })

    def test_new_numeric_cases_flag_their_planted_dose_error(self):
        self.assertIn("500mg", self._flagged_values("case_07_numeric_medication_error_pediatric_dose"))
        self.assertIn("50mg", self._flagged_values("case_08_numeric_medication_error_beta_blocker"))

    def test_omission_cases_raise_no_deterministic_flags(self):
        # Omission errors are things ABSENT from the note - by definition
        # there's no wrong number physically present in the note text for
        # Node 4 to catch. This is exactly why the omission node exists as
        # a separate detection approach (see pipeline.py).
        for case_id in ("case_15_omission_otc_medication", "case_16_omission_drug_allergy"):
            with self.subTest(case_id=case_id):
                self.assertEqual(self._flagged_values(case_id), set())

    def test_all_clean_controls_raise_no_deterministic_flags(self):
        for case_id in ("case_06_clean_control", "case_17_clean_control_dermatology",
                         "case_18_clean_control_annual_physical"):
            with self.subTest(case_id=case_id):
                self.assertEqual(self._flagged_values(case_id), set())


if __name__ == "__main__":
    unittest.main()
