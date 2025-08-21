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

# Suppress toc not included warning
# Because modules.rst is currently unused in the documentation
suppress_warnings = ['toc.not_included']
