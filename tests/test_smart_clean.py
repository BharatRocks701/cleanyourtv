"""Unit tests for the non-destructive Smart Clean helper."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

MODULE = pathlib.Path(__file__).resolve().parents[1] / "tools" / "smart_clean.py"
spec = importlib.util.spec_from_file_location("smart_clean", MODULE)
clean = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clean)


class SmartCleanTests(unittest.TestCase):
    def test_parse_disk_uses_data_only(self):
        output = "Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/a 100 20 80 20% /\n/dev/b 8192 4096 4096 50% /data"
        self.assertEqual(clean.parse_storage(output), {
            "total_bytes": 8192 * 1024, "used_bytes": 4096 * 1024,
            "free_bytes": 4096 * 1024})
        self.assertIsNone(clean.parse_storage("Filesystem 1K-blocks Used Available Use% Mounted on"))

    def test_parse_memory(self):
        self.assertEqual(clean.parse_memory("MemTotal: 1000 kB\nMemAvailable: 250 kB\n"),
                         {"memtotal_bytes": 1000 * 1024, "memavailable_bytes": 250 * 1024})

    @patch.object(clean, "tv_shell", return_value="")
    def test_trim_only_asks_package_manager(self, shell):
        clean.trim_caches(1024)
        shell.assert_called_once_with("pm trim-caches 1024M", timeout=180)

    @patch.object(clean, "tv_shell", return_value="Error: unknown command")
    def test_refuses_unsupported_command(self, _shell):
        with self.assertRaises(clean.TVCommandError):
            clean.trim_caches(1024)

    @patch.dict("os.environ", {"TV_HOST": "192.0.2.1"})
    @patch.object(clean, "take_snapshot")
    @patch.object(clean, "trim_caches")
    def test_default_mode_is_read_only(self, trim, snapshot):
        snapshot.return_value = {"brand": "OnePlus", "model": "Y1S Edge", "android_version": "11",
                                 "storage": None, "memory": {}, "third_party_apps": 0, "disabled_packages": 0}
        self.assertEqual(clean.main([]), 0)
        trim.assert_not_called()


if __name__ == "__main__":
    unittest.main()
