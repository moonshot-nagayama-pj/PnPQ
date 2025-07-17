# Contributing

Thank you for your interest in contributing to our project. To make it as easy as possible to engage with our work, please read this short guide.

## Preparing your environment

Please see [`development-environment.md`](https://github.com/moonshot-nagayama-pj/public-documents/blob/main/engineering/development-environment.md) for more information.

## Development

We run unit tests on all pull requests using simulated hardware. Use `pytest` to run these unit tests.

For ad-hoc testing of real hardware, use `pytest hardware_tests`.

Before making a pull request, please be sure to run the script `bin/check.bash`. This will run our static analysis checks and unit tests, all of which must pass before a pull request will be accepted.

## Discussing and proposing changes

To make a trivial change, or a change that has already been agreed to in discussions outside of GitHub, please create a pull request.

If a change might need more discussion, please create a GitHub issue in this project before working on a pull request.

## Licensing and attribution

By contributing your work to this repository, you agree to license it in perpetuity under the terms described in [`LICENSE.md`](LICENSE.md). You are also asserting that the work is your own, and that you have the right to license it to us.

If you wish to integrate our work into your own projects, please follow the attribution guidelines in `LICENSE.md`.

## Code of conduct

In order to provide a safe and welcoming environment for all people to contribute to our project, we have adopted a code of conduct, which you can read in [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Making a release

Follow the steps below in order to create and publish a release for PnPQ

1. Decide to create a release
2. Ensures all PRs have user-friendly titles
3. Create a `release-A.B.C` branch
4. Remove the `.dev` suffix in the version field in `pyproject.toml` (update version if necessary)
5. Commit `git commit -am 'Release version A.B.C'` and push changes to branch
6. Create a tag `git tag -am 'Release version A.B.C' vA.B.C` and push `git push origin vA.B.C`
7. Wait for the release check script to finish
8. Edit the release in the draft (the generate release note function is sufficient for most cases)
9. Publish the draft page, this will initiate the upload script
10. Approve the upload script
11. Start the next version (with the `.dev` prefix)
12. Create a PR to merge this branch
13. Wait for approval to merge the PR, and finish!
