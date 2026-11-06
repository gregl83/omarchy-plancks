"""Keep release checks off moving operating-system and dependency defaults."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CiEnvironmentTests(unittest.TestCase):
    def test_all_jobs_select_a_versioned_runner(self):
        workflows = list((ROOT / '.github/workflows').glob('*.y*ml'))
        self.assertTrue(workflows)
        for path in workflows:
            runners = re.findall(r'^\s*runs-on:\s*(.+)$', path.read_text(), re.M)
            self.assertTrue(runners, path.name)
            for runner in runners:
                self.assertRegex(runner, r'^ubuntu-\d{2}\.\d{2}$', path.name)

    def test_actions_and_python_have_exact_versions(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        actions = re.findall(r'^\s*- uses:\s*(\S+)', workflow, re.M)
        self.assertTrue(actions)
        for action in actions:
            self.assertRegex(action, r'@([0-9a-f]{40})$')
        matrix = re.search(r"python:\s*\[([^\]]+)\]", workflow)
        self.assertIsNotNone(matrix)
        versions = re.findall(r"'([^']+)'", matrix.group(1))
        self.assertEqual(len(versions), 2)
        for version in versions:
            self.assertRegex(version, r'^\d+\.\d+\.\d+$')
        release_check = workflow.split('  release-check:', 1)[1].split('  all-go:', 1)[0]
        self.assertIn('actions/setup-python@', release_check)
        self.assertRegex(release_check, r"python-version: '\d+\.\d+\.\d+'")

    def test_qml_container_and_shell_are_immutable_inputs(self):
        container = (ROOT / 'scripts/ci/Containerfile').read_text()
        self.assertRegex(container, r'^FROM \S+@sha256:[0-9a-f]{64}\n')
        self.assertRegex(container, r'ARG ARCH_SNAPSHOT=\d{4}/\d{2}/\d{2}\n')
        revision = (ROOT / 'scripts/ci/omarchy-ref').read_text().strip()
        self.assertRegex(revision, r'^[0-9a-f]{40}$')
