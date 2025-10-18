from flask_smorest import Blueprint

blp = Blueprint("Metrics", __name__, description="Portfolio metrics endpoints")

from . import routes  # noqa: E402,F401
