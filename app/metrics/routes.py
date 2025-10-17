"""Metrics endpoints for portfolio analytics."""

from __future__ import annotations

from flask.views import MethodView

from app.services import calculate_portfolio_value

from . import blp
from .schemas import PortfolioValueQuerySchema, PortfolioValueResponseSchema


@blp.route("/portfolio/<int:portfolio_id>/value")
class PortfolioValue(MethodView):
    @blp.arguments(PortfolioValueQuerySchema, location="query")
    @blp.response(200, PortfolioValueResponseSchema())
    def get(self, query_params, portfolio_id: int):
        result = calculate_portfolio_value(
            portfolio_id,
            view_base=query_params.get("base"),
        )

        return {
            "portfolio_id": result.portfolio_id,
            "portfolio_base": result.portfolio_base,
            "view_base": result.view_base,
            "value": result.value,
            "priced": result.priced,
            "unpriced": result.unpriced,
            "as_of": result.as_of,
        }

