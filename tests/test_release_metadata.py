"""Catch marketplace metadata rejections before tagging a release."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.ci.validate import validate


class MarketplaceMetadataTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((Path(__file__).resolve().parents[1] / 'manifest.json').read_text())

    def test_overlong_fields_are_rejected(self):
        for field, limit in {'id': 128, 'name': 120, 'version': 64,
                             'author': 120, 'description': 500, 'license': 120}.items():
            with self.subTest(field=field):
                manifest = dict(self.manifest, **{field: 'x' * (limit + 1)})
                with patch('pathlib.Path.read_text', return_value=json.dumps(manifest)):
                    with self.assertRaisesRegex(ValueError, 'marketplace limit'):
                        validate()

    def test_description_counts_like_javascript(self):
        manifest = dict(self.manifest, description='🚀' * 251)
        with patch('pathlib.Path.read_text', return_value=json.dumps(manifest)):
            with self.assertRaisesRegex(ValueError, 'marketplace limit'):
                validate()

    def test_control_characters_are_rejected(self):
        manifest = dict(self.manifest, description='Timer\nwith sessions')
        with patch('pathlib.Path.read_text', return_value=json.dumps(manifest)):
            with self.assertRaisesRegex(ValueError, 'control characters'):
                validate()
