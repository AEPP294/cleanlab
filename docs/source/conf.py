# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import sys
import datetime

sys.path.insert(0, "..")
# sys.path.insert(1, "./cleanlab/models")

# -- Project information -----------------------------------------------------

project = "Cleanlab"
copyright = f"{datetime.datetime.now().year}, Cleanlab Inc."
author = "Cleanlab Inc."


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "nbsphinx",
    # 'sphinxcontrib.bibtex',  # for bibliographic references
    # 'sphinxcontrib.rsvgconverter',  # for SVG->PDF conversion in LaTeX output
    # "sphinx_gallery.load_style",  # load CSS for gallery (needs SG >= 0.6)
    # 'sphinx_codeautolink',  # automatic links from code to documentation
    # "sphinx.ext.intersphinx",  # links to other Sphinx projects (e.g. NumPy)
    "sphinx.ext.autodoc",
    "autodocsumm",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx_tabs.tabs",
    # "sphinxcontrib.apidoc",
]

numpy_show_class_members = True

# Don't add .txt suffix to source files:
html_sourcelink_suffix = ""

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build"]

autosummary_generate = True

# -- Options for apidoc extension ----------------------------------------------

# apidoc_module_dir = "cleanlab/cleanlab"

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for Nnapoleon extension -------------------------------------------

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for autodoc extension -------------------------------------------

# This value selects what content will be inserted into the main body of an autoclass
# directive
#
# http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#directive-autoclass
autoclass_content = "class"


# Default options to an ..autoXXX directive.
autodoc_default_options = {
    "autosummary": True,
    "members": None,
    "inherited-members": None,
    "show-inheritance": None,
    "special-members": "__call__",
}

# Subclasses should show parent classes docstrings if they don't override them.
autodoc_inherit_docstrings = True

# -- nbsphinx Configuration ---------------------------------------------------

# This is processed by Jinja2 and inserted before each notebook
nbsphinx_prolog = """
{% set docname = env.doc2path(env.docname, base=None) %}

.. raw:: html

    <style>
        .nbinput .prompt,
        .nboutput .prompt {
            display: none;
        }
    </style>

    <p>
        <a style= "background-color:white;color:black;padding:4px 12px;text-decoration:none;display:inline-block;border-radius:8px;box-shadow:0 2px 4px 0 rgba(0, 0, 0, 0.2), 0 3px 10px 0 rgba(0, 0, 0, 0.19)" href="https://colab.research.google.com/github/cleanlab/docs/blob/master/source/{{ docname|e }}" target="_blank">
            <img src="https://colab.research.google.com/img/colab_favicon_256px.png" alt="Google Colab Logo" style="width:40px;height:40px;vertical-align:middle">   
            <span style="vertical-align:middle">Run in Google Colab</span>
        </a>
    </p>
"""

# Uncomment this before running in the doc's CI/CD server
nbsphinx_execute = "never"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_favicon = "logo.png"
html_title = "Cleanlab Docs"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
