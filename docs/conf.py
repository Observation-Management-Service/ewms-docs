extensions = [
    'myst_parser',
    'sphinx.ext.githubpages',
    'sphinxcontrib.openapi',
    'sphinx_rtd_theme',
]

redoc = [
    {
        "name": "WMS API Schemas",
        "page": "apis/wms-schemas",
        "spec": "../sources/wms/wms/schema/openapi.json",
        "embed": True,
        "opts": {
            "hide-hostname": True,
            "required-props-first": True,
        },
    }
]

root_doc = 'index'
html_theme = 'sphinx_rtd_theme'

project = 'Event Workflow Management Service'
author = 'WIPAC Developers'
html_show_copyright = False

html_title = 'Event Workflow Management Service'
html_short_title = 'EWMS'

html_last_updated_fmt = '%Y-%m-%d %H:%M UTC'
html_last_updated_use_utc = True

exclude_patterns = [
    '_build',
]

html_static_path = ['_static']
html_css_files = ['ewms-banner.css', 'ewms-nav.css']
html_js_files = ['ewms-nav.js']

html_theme_options = {
    'collapse_navigation': False,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
}
