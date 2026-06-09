import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


class DoctorAccessControlTests(unittest.TestCase):
    def load_doctor_auth_module(self):
        import doctor_auth
        return doctor_auth

    def load_main_module(self):
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.admin.command.return_value = True

        with patch("pymongo.MongoClient", return_value=mock_client), patch("groq.Groq", return_value=MagicMock()):
            sys.modules.pop("main", None)
            return importlib.import_module("main")

    def test_patient_ownership_check_blocks_other_doctors(self):
        main = self.load_main_module()

        patient = {
            "patid": "PT111111",
            "pname": "Other Doctor Patient",
            "phone_number": "03001234567",
            "added_by_doctor_id": "DR1-0000-000",
        }

        self.assertFalse(main._patient_belongs_to_doctor(patient, "DR1-9999-999"))
        self.assertTrue(main._patient_belongs_to_doctor(patient, "DR1-0000-000"))

    def test_masking_hides_personal_identifiers_for_other_doctors(self):
        doctor_auth = self.load_doctor_auth_module()

        patient = {
            "patid": "PT111111",
            "pname": "Other Doctor Patient",
            "phone_number": "03001234567",
            "patient_email": "patient@example.com",
            "added_by_doctor_id": "DR1-0000-000",
        }

        masked = doctor_auth._mask_patient_for_doctor(patient, "DR1-9999-999")

        self.assertEqual(masked["pname"], "")
        self.assertEqual(masked["phone_number"], "")
        self.assertEqual(masked["patient_email"], "")
        self.assertFalse(masked.get("is_owned_patient", True))


if __name__ == "__main__":
    unittest.main()
