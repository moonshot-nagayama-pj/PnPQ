#!/usr/bin/env bash

# Usage: release.bash [next-version]
# If a version number is not provided, the next version will be a patch version increment.

set -o errexit
set -o nounset
set -o pipefail

# Print functions
stdmsg() {
  local IFS=' '
  printf '%s\n' "$*"
}

errmsg() {
  stdmsg "$*" 1>&2
}

# To avoid cross-platform problems between MacOS sed and GNU sed, do
# not use sed -i below, instead, write to a temp file
temp_sphinx_conf=$(mktemp)

# Trap exit handler
trap_exit() {
  # It is critical that the first line capture the exit code. Nothing
  # else can come before this. The exit code recorded here comes from
  # the command that caused the script to exit.
  local exit_status="$?"

  rm -rf "${temp_sphinx_conf}"

  if [[ ${exit_status} -ne 0 ]]; then
    errmsg 'The script did not complete successfully.'
    errmsg 'The exit code was '"${exit_status}"
  fi
}
trap trap_exit EXIT

# Get the base and project directories
base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd -P)"
project_dir="$(cd "${base_dir}/.." >/dev/null && pwd -P)"

# cd to the directory before running uv
cd "${project_dir}"

# Ensure that the script is run from the main branch
current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ ${current_branch} != "main" ]]; then
  errmsg "Error: This script must be run on the main branch." >&2
  exit 1
fi

# Ensure that there are no uncommitted changes
if ! git diff-index --quiet HEAD --; then
  errmsg "Error: There are uncommitted changes in the repository. Please commit or stash them before running this script."
  exit 1
fi

stdmsg "Parsing current version and get next version..."

# Get current version
uv_version_str=$(uv version)
current_version=$(stdmsg "${uv_version_str}" | awk '{print $2}')

# Remove `.dev0` from the version
updated_version=${current_version%.dev0}

# Check format of updated_version
if [[ ! ${updated_version} =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  errmsg "Error: Current version '${updated_version}' is not in the correct format (A.B.C). Please update the version in pyproject.toml."
  exit 1
fi

# Parse optional next version argument
new_version=""

# If an argument is passed, validate it
if [[ -n ${1-} ]]; then
  if [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    new_version="$1"
  else
    errmsg "Error: Invalid next version format. Use A.B.C (e.g., 1.2.3)"
    exit 1
  fi
else
  # No argument provided, increment patch version
  IFS='.' read -r major minor patch <<<"${updated_version}"
  new_version="${major}.${minor}.$((patch + 1))"
fi

stdmsg "Next version will be: ${new_version}"

# Run the checks script
stdmsg "Run checks before starting the release process..."
"${base_dir}/check.bash"

stdmsg "Starting release process..."

stdmsg "Removing '.dev0' from version in pyproject.toml..."
uv version "${updated_version}"

stdmsg "Updating smv_latest_version in the Sphinx config..."
sed "s/smv_latest_version.*=.*'v.*'/smv_latest_version = 'v${updated_version}'/" "${project_dir}"/sphinx/source/conf.py >"${temp_sphinx_conf}"
mv "${temp_sphinx_conf}" "${project_dir}"/sphinx/source/conf.py

stdmsg "Releasing version: ${updated_version}"

# Create branch 'release-<version>'
branch_name="release-${updated_version}"
stdmsg "Creating release branch '${branch_name}'..."
git checkout -b "${branch_name}"

# Commit the version change and push
stdmsg "Committing and pushing version change..."
git commit -am "Release version: ${updated_version}"
git push origin "${branch_name}"

# Create a tag 'v<version>'
stdmsg "Creating tag 'v${updated_version}'..."
git tag -am "Release version: ${updated_version}" "v${updated_version}"
git push origin "v${updated_version}"

# Update the version to the new version (e.g. <version>.dev)
stdmsg "Starting next version: ${new_version}"
uv version "${new_version}.dev"

# Commit the next version change
stdmsg "Committing next version change..."
git commit -am "Start next version: ${new_version}"
git push origin "${branch_name}"

# Create a pull request
pull_request_url="https://github.com/moonshot-nagayama-pj/pnpq/pull/new/${branch_name}"
stdmsg "Please check the pull request at ${pull_request_url}."
if command -v xdg-open &>/dev/null; then
  xdg-open "${pull_request_url}"
elif command -v open &>/dev/null; then
  open "${pull_request_url}"
fi

stdmsg "The script completed successfully."
