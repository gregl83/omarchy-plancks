# CI and releases

The `ci` workflow validates pull requests targeting `main`, pushes to `main`, and `v*` tags. It runs the Python tests on Python 3.9 and 3.14, checks package metadata, validates the plugin with Omarchy's official validator, and loads the QML in an isolated headless Wayland session. Plancks ships as Python and QML source, so there is no separate compilation step.

The QML job uses the Omarchy revision in `scripts/ci/omarchy-ref` and the Arch Linux package snapshot selected by `ARCH_SNAPSHOT` in `scripts/ci/Containerfile`. Update these pins deliberately when adopting newer shell components or Qt/Quickshell packages, and verify the headless smoke test before merging. To block merging failed PRs, configure a GitHub branch ruleset for `main` that requires **all systems go**. The workflow supplies that check; repository rules enforce it.

To release:

1. Update `manifest.json` to the new stable `MAJOR.MINOR.PATCH` version and merge the changes into `main` through a passing PR.
2. Check out the latest `main`, then create and push the matching tag:

   ```bash
   git switch main
   git pull --ff-only origin main
   version=$(python3 -c 'import json; print(json.load(open("manifest.json"))["version"])')
   git tag -a "v$version" -m "Plancks v$version"
   git push origin "v$version"
   ```

3. The tag runs the same validation again. Its version must match the manifest, and its commit must belong to `main`. Only after every check passes does the workflow create the GitHub release with generated release notes.

Use the tag workflow to publish releases; manually creating a release in GitHub bypasses this gate. Existing releases are left unchanged on reruns. The release badge shows the latest published GitHub release once the first release exists.

Marketplace submission and approval are separate from this workflow. Omarchy's Git-based installer follows the repository's current code, not the release badge or tag, so protect `main` as well as validating releases.
