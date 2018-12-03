#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# yarely documentation build configuration file, created by
# sphinx-quickstart.
#
# This file is execfile()d with the current directory set to its
# containing dir.

# Standard libary imports
import sys
import os

# Third party imports
from sphinx.ext.autodoc import ClassDocumenter
from unittest.mock import MagicMock

# Insert the project root dir as the first element in the PYTHONPATH.
# This lets us ensure that the source package is imported, and that its
# version is used.
cwd = os.getcwd()
project_root = os.path.dirname(cwd)
sys.path.insert(0, project_root)

# Local imports
import yarely  # NOQA -- flake8 [ignore module level import not at top of file]


# -- General configuration ---------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom ones.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = u"Yarely"
author = yarely.__author__
copyright = yarely.__copyright__
version = yarely.__version__  # The short X.Y version.
release = yarely.__version__  # The full version, including alpha/beta/rc tags.

# Ignore the common prefix that all Yarely packages have
modindex_common_prefix = ["yarely."]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

autoclass_content = 'both'


# -- Mock imports ------------------------------------------------------

class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

MOCK_MODULES = ['pyobjc']
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)


# -- Options for HTML output -------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
html_static_path = ["_static"]

# Output file base name for HTML help builder.
htmlhelp_basename = "yarelydoc"


# -- Options for LaTeX output ------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [(
  "index", "yarely.tex", u"Yarely Documentation", author, "manual"
)]


# -- Options for manual page output ------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [("index", "yarely", u"Yarely Documentation", [author], 1)]


# -- Options for Texinfo output ----------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [(
  "index", "yarely", u"Yarely Documentation", author, "yarely",
  yarely.__shortdescription__, "Miscellaneous"),
]


# -- Autodoc functions -------------------------------------------------

def skip(app, what, name, obj, skip, options):
    # This ensures that the following private classes get documented:
    #   yarely.core.config.parse_config._YarelyConfig
    #   yarely.core.scheduling.contextconstraintsparser.\
    #     _ContextConstraintsParser
    #   yarely.core.scheduling.schedulers.lottery.duration_based_allocator.\
    #     _DurationBasedAllocator
    #   yarely.core.scheduling.schedulers.lottery.equal_distribution_allocator.\
    #     _EqualDistributionAllocator
    #   yarely.core.scheduling.schedulers.lottery.random_allocator.\
    #     _RandomAllocator
    #   yarely.core.scheduling.schedulers.lottery.ratio_allocator.\
    #     _RatioAllocator
    #   yarely.core.scheduling.schedulers.lottery.recency_based_allocator.\
    #     _RecencyBasedAllocator
    # (See my stackoverflow question here for an explaination of what I'm
    # trying to achieve here:
    #   http://stackoverflow.com/questions/38765577/overriding-sphinx-autodoc-alias-of-for-import-of-private-class
    # )
    # TODO:
    #    yarely.core.content.constants._ARG_RENDER_NAMESPACE
    #    yarely.core.content.constants._MIME_TYPE_CONFIG_MAP
    if (
        what == "module" and
        name in (
          "_ContextConstraintsParser",
          "_DurationBasedAllocator", "_EqualDistributionAllocator",
          "_RandomAllocator", "_RatioAllocator", "_RecencyBasedAllocator",
          "_YarelyConfig"
        ) 
    ):
        #options['undoc-members'] = False
        return False
    return skip

def setup(app):
    app.connect('autodoc-skip-member', skip)
