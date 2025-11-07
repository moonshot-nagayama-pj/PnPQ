# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "PnPQ"
copyright = "2024-present, PnPQ contributors"
author = "PnPQ contributors"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.apidoc",
    "sphinx_multiversion",
]
apidoc_modules = [
    {
        'path': '../../src/pnpq',
        'destination': 'api/',
        'separate_modules': True,
    },
]
autodoc_typehints = "description"

templates_path = ["_templates"]
exclude_patterns: list[str] = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]

html_sidebars = {
    '**': [
        "navbar-logo.html",
        "icon-links.html",
        "search-button-field.html",
        "sbt-sidebar-nav.html",
        'versioning.html',
    ],
}

# Suppress toc not included warning
# Because modules.rst is currently unused in the documentation
suppress_warnings = ['toc.not_included']

# sphinx-multiversion
smv_tag_whitelist = r'^v[0-9]+[.][0-9]+[.][0-9]+$'
smv_branch_whitelist = r'^main$'

# The latest version pointer is updated by the release script on each
# release.
smv_latest_version = 'v0.2.0'
