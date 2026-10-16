"""Ensure every notification state ships a correctly sized PNG."""
from pathlib import Path
import struct
import unittest


class NotificationAssetsTests(unittest.TestCase):
    def test_all_states_are_packaged(self):
        root = Path(__file__).resolve().parents[1] / 'assets/notifications'
        for graphic in ('sun-moon', 'coffee', 'starship'):
            for phase in ('active', 'off-time'):
                paths = [f'{phase}/fill-{level:03}.png' for level in range(0, 101, 5)]
                paths += [f'{state}/{phase}.png' for state in ('learning', 'overtime')]
                for path in paths:
                    with self.subTest(graphic=graphic, path=path):
                        data = (root / graphic / path).read_bytes()
                        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                        self.assertEqual(struct.unpack('>II', data[16:24]), (116, 108))
                        self.assertEqual(data[25], 6)  # RGBA, including transparency.
