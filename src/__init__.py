from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
    loader=PackageLoader("src"),
    autoescape=select_autoescape()
)
