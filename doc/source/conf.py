# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
import importlib.metadata



project = 'autel-logger'
_meta = importlib.metadata.metadata(project)
author = _meta.get('Author', _meta['Author-email'].split('<')[0].strip())
copyright = f'2025, {author}'
version = _meta['Version']
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_click',
]


autodoc_typehints = 'both'
autodoc_typehints_description_target = 'documented'
autodoc_docstring_signature = True

autodoc_default_options = {
    'member-order': 'bysource',
    'show-inheritance': True,
    # 'special-members': '__call__',
    # 'ignore-module-all': True,
}

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']


intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'bpy': ('https://docs.blender.org/api/current/', None),
}
