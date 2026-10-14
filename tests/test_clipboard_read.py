from pathlib import Path
import re
import sys
import time
import unittest

from clipboard_read import read_text


class ClipboardReadTests(unittest.TestCase):
    def read(self, script, limit=320, timeout=0.2):
        return read_text([sys.executable, "-c", script], limit, timeout)

    def test_utf8_at_byte_limit(self):
        self.assertEqual(self.read("import os; os.write(1, 'é'.encode() * 160)"), "é" * 160)

    def test_oversized_offer_is_rejected(self):
        self.assertEqual(self.read("import os; os.write(1, b'x' * 321)"), "")

    def test_stalled_offer_is_rejected_and_reaped(self):
        start = time.monotonic()
        self.assertEqual(self.read("import time; time.sleep(30)"), "")
        self.assertLess(time.monotonic() - start, 2)

    def test_partial_offer_does_not_escape_deadline(self):
        start = time.monotonic()
        self.assertEqual(self.read("import os,time\nwhile True:\n os.write(1,b'x'); time.sleep(.03)"), "")
        self.assertLess(time.monotonic() - start, 2)

    def test_endless_offer_is_rejected(self):
        self.assertEqual(self.read("import os\nwhile True: os.write(1,b'x'*4096)"), "")

    def test_missing_reader(self):
        with self.assertRaises(FileNotFoundError):
            read_text(["/nonexistent/clipboard-reader"], 320)


class ClipboardControlPolicyTests(unittest.TestCase):
    def test_runtime_inputs_use_bounded_control(self):
        # Native editable TextInput/TextField reads clipboard payloads even without
        # pasting. Keep every runtime input on the explicitly bounded paste path.
        root = Path(__file__).resolve().parents[1]
        native = re.compile(r"\b(?:(?:[A-Za-z_]\w*)\.)?(TextField|TextInput|TextArea|TextEdit)\s*\{")
        for path in root.glob("*.qml"):
            source = re.sub(r"/\*.*?\*/|//[^\n]*", "", path.read_text(), flags=re.S)
            matches = native.findall(source)
            with self.subTest(file=path.name):
                self.assertEqual(matches, ["TextArea"] if path.name == "BoundedTextField.qml" else [])
