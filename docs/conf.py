extensions = [
    'myst_parser',
    'sphinx.ext.githubpages',
    'sphinxcontrib.openapi',
    'sphinx_rtd_theme',
]

root_doc = 'index'
html_theme = 'sphinx_rtd_theme'

project = 'Event Workflow Management Service'
author = 'WIPAC Developers'
copyright = '%Y, WIPAC Developers'

version = '0.1'
release = '0.1.0'

html_title = 'Event Workflow Management Service'
html_short_title = 'EWMS'

exclude_patterns = [
    '_build',
]

html_static_path = ['_static']
html_css_files = ['ewms.css']

html_theme_options = {
    'collapse_navigation': False,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}
