"""Metrics endpoints for portfolio analytics."""

from __future__ import annotations

from flask.views import MethodView

from app.services import calculate_currency_exposure, calculate_daily_pnl, calculate_portfolio_value

from . import blp
from .schemas import (
    PortfolioExposureQuerySchema,
    PortfolioExposureResponseSchema,
    PortfolioDailyPnLQuerySchema,
    PortfolioDailyPnLResponseSchema,
    PortfolioValueQuerySchema,
    PortfolioValueResponseSchema,
)


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


@blp.route("/portfolio/<int:portfolio_id>/exposure")
class PortfolioExposure(MethodView):
    @blp.arguments(PortfolioExposureQuerySchema, location="query")
    @blp.response(200, PortfolioExposureResponseSchema())
    def get(self, query_params, portfolio_id: int):
        result = calculate_currency_exposure(
            portfolio_id,
            top_n=query_params.get("top_n"),
            view_base=query_params.get("base"),
        )

        exposures = [
            {
                "currency_code": item.currency_code,
                "net_native": item.net_native,
                "base_equivalent": item.base_equivalent,
            }
            for item in result.exposures
        ]

        return {
            "portfolio_id": result.portfolio_id,
            "portfolio_base": result.portfolio_base,
            "view_base": result.view_base,
            "exposures": exposures,
            "priced": result.priced,
            "unpriced": result.unpriced,
            "as_of": result.as_of,
        }


@blp.route("/portfolio/<int:portfolio_id>/pnl/daily")
class PortfolioDailyPnL(MethodView):
    @blp.arguments(PortfolioDailyPnLQuerySchema, location="query")
    @blp.response(200, PortfolioDailyPnLResponseSchema())
    def get(self, query_params, portfolio_id: int):
        result = calculate_daily_pnl(
            portfolio_id,
            view_base=query_params.get("base"),
        )

        return {
            "portfolio_id": result.portfolio_id,
            "portfolio_base": result.portfolio_base,
            "view_base": result.view_base,
            "pnl": result.pnl,
            "value_current": result.value_current,
            "value_previous": result.value_previous,
            "as_of": result.as_of,
            "prev_date": result.prev_date,
            "positions_changed": result.positions_changed,
            "priced_current": result.priced_current,
            "unpriced_current": result.unpriced_current,
            "priced_previous": result.priced_previous,
            "unpriced_previous": result.unpriced_previous,
        }
