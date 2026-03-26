extensions = [
    "myst_parser",
    "sphinx.ext.githubpages",
    "sphinxcontrib.openapi",
    "sphinx_rtd_theme",
]

root_doc = "getting-started"
html_theme = "sphinx_rtd_theme"

project = "Event Workflow Management Service"
author = "WIPAC Developers"
html_show_copyright = False

html_title = "Event Workflow Management Service"
html_short_title = "EWMS"

html_last_updated_fmt = "%Y-%m-%d %H:%M UTC"
html_last_updated_use_utc = True

exclude_patterns = [
    "_build",
]

html_static_path = ["_static"]
html_css_files = [
    "ewms.css",
    "ewms-banner.css",
    "ewms-nav.css",
]

html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}
