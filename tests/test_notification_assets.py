"""Ensure every notification state ships a correctly sized PNG."""
from pathlib import Path
import struct
import unittest


class NotificationAssetsTests(unittest.TestCase):
    def test_all_states_are_packaged(self):
        root = Path(__file__).resolve().parents[1] / 'assets/notifications'
        for graphic in ('sun-moon', 'coffee', 'starship', 'roadster'):
            for phase in ('active', 'off-time'):
                levels = set(range(0, 101, 5))
                if graphic == 'roadster' and phase == 'active':
                    levels.update(range(45, 56))
                paths = [f'{phase}/fill-{level:03}.png' for level in sorted(levels)]
                paths += [f'{state}/{phase}.png' for state in ('learning', 'overtime')]
                for path in paths:
                    with self.subTest(graphic=graphic, path=path):
                        data = (root / graphic / path).read_bytes()
                        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                        self.assertEqual(struct.unpack('>II', data[16:24]), (116, 116))
                        self.assertEqual(data[25], 6)  # RGBA, including transparency.
