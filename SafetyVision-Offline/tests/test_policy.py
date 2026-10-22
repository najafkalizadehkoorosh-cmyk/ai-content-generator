import unittest
from safetyvision.policy import violation_label


class ViolationPolicyTests(unittest.TestCase):
    def test_missing_mask_variants(self):
        for name in ("NO-Mask", "no_mask", "NO Mask"):
            self.assertEqual(violation_label(name), "ماسک شناسایی نشد")

    def test_missing_helmet_variants(self):
        for name in ("NO-Hardhat", "no_hardhat", "NO-Helmet"):
            self.assertEqual(violation_label(name), "کلاه ایمنی شناسایی نشد")

    def test_positive_classes_do_not_trigger_alert(self):
        for name in ("Mask", "Hardhat", "Person", "Safety Vest", "NO-Gloves"):
            self.assertIsNone(violation_label(name))


if __name__ == "__main__":
    unittest.main()
