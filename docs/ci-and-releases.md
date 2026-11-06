# CI and releases

The `ci` workflow validates pull requests targeting `main`, pushes to `main`, and `v*` tags. It runs the Python tests on pinned Python 3.9.25 and 3.14.10 builds using Ubuntu 24.04, checks package metadata, validates the plugin with Omarchy's official validator, and loads the QML in an isolated headless Wayland session. Plancks ships as Python and QML source, so there is no separate compilation step.

Every job explicitly selects Ubuntu 24.04; none uses `ubuntu-latest`. Release-tag validation explicitly installs Python rather than relying on the runner’s default interpreter. GitHub Actions use full commit SHAs.

The QML job uses a digest-pinned Arch base image, the Omarchy revision in `scripts/ci/omarchy-ref` and the Arch Linux package snapshot selected by `ARCH_SNAPSHOT` in `scripts/ci/Containerfile`. Update these pins deliberately when adopting newer shell components or Qt/Quickshell packages, and rebuild and verify the headless smoke test before merging. When changing Python or Ubuntu versions, first confirm that every matrix version has an x64 build for that Ubuntu release in the [setup-python version manifest](https://github.com/actions/python-versions/blob/main/versions-manifest.json). Environment-policy tests reject moving runner labels, unpinned actions, incomplete Python versions, and unpinned container/shell inputs.

The Ubuntu label pins the OS release, not an immutable hosted VM: GitHub still updates Docker, Git, and `gh`, and eventually retires runner releases. Registry/archive availability can also affect builds. Review these pins during release preparation and adopt security updates deliberately. Local demo generation follows the installed desktop so previews reflect actual appearance; it is not the reproducible CI environment. To block merging failed PRs, configure a GitHub branch ruleset for `main` that requires **all systems go**. The workflow supplies that check; repository rules enforce it.

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

For an existing marketplace listing, request verification of the **new upstream commit** using the [verification workflow](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/VERIFICATION.md). Submit the final, pushed commit SHA after CI passes. An older verification does not cover a new release; changing the target commit during review requires fresh validation and approval.

The marketplace baseline detects `package-manager` in `scripts/ci/Containerfile`. Those package commands run only while building the isolated test container; the installed plugin never invokes them. This capability required and received maintainer review for [Plancks 1.7.0](https://github.com/omacom/omarchy-plugin-marketplace/issues/11860), and must be reviewed again against each new snapshot. A local baseline check is preparation, not marketplace approval.
