"""Exercise release gates against disposable Git repositories."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

VALIDATOR = Path(__file__).resolve().parents[1] / 'scripts/ci/validate.py'


class ReleaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Release test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.root.joinpath('manifest.json').write_text(json.dumps({
            'id': 'test.plugin', 'name': 'Test', 'version': '1.0.0',
            'author': 'Test', 'description': 'Release validation fixture',
        }))
        for name in ('README.md', 'LICENSE', 'preview.png', 'qmldir', 'plancks.py',
                     'Widget.qml', 'EpochPanel.qml', 'EpochController.qml'):
            self.root.joinpath(name).write_text('fixture\n')
        self.git('add', '.')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'Initial package')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.git('-c', 'tag.gpgsign=false', 'tag', 'v1.0.0')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, text=True,
                              capture_output=True, check=True)

    def validate(self, *args):
        return subprocess.run([sys.executable, str(VALIDATOR), *args], cwd=self.root,
                              text=True, capture_output=True)

    def test_matching_release_on_main_passes(self):
        result = self.validate('--tag', 'v1.0.0')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrong_version_fails(self):
        result = self.validate('--tag', 'v2.0.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('matching manifest.json', result.stderr)

    def test_unmerged_release_fails(self):
        self.root.joinpath('README.md').write_text('Unmerged change\n')
        self.git('add', '.')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'Unmerged')
        self.git('-c', 'tag.gpgsign=false', 'tag', '-f', 'v1.0.0')
        self.assertNotEqual(self.validate('--tag', 'v1.0.0').returncode, 0)

    def test_tag_must_identify_tested_commit(self):
        self.root.joinpath('README.md').write_text('New main commit\n')
        self.git('add', '.')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'Next commit')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        result = self.validate('--tag', 'v1.0.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checked-out commit', result.stderr)

    def test_missing_runtime_file_fails_without_tag(self):
        self.root.joinpath('EpochController.qml').unlink()
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('EpochController.qml', result.stderr)


if __name__ == '__main__':
    unittest.main()
