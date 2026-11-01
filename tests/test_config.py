import importlib
import sys
import os
import unittest
from pathlib import Path


class ConfigImportFallbackTests(unittest.TestCase):
    def test_config_import_without_python_dotenv(self):
        original = sys.modules.get("dotenv")
        sys.modules["dotenv"] = None
        if "config" in sys.modules:
            del sys.modules["config"]

        try:
            module = importlib.import_module("config")
            self.assertTrue(hasattr(module, "BOT_TOKEN"))
            self.assertIsInstance(module.ADMIN_IDS, list)
            self.assertIsInstance(module.ADMIN_GROUP, int)
        finally:
            if original is not None:
                sys.modules["dotenv"] = original
            else:
                sys.modules.pop("dotenv", None)
            sys.modules.pop("config", None)


if __name__ == "__main__":
    unittest.main()
