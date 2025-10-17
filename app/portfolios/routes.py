"""Route handlers for portfolio CRUD operations."""

from __future__ import annotations

from flask import url_for
from flask.views import MethodView

from app.services import (
    PortfolioCreateData,
    PortfolioUpdateData,
    create_portfolio,
    delete_portfolio,
    get_portfolio,
    list_portfolios,
    update_portfolio,
)

from . import blp
from .schemas import (
    PortfolioCollectionSchema,
    PortfolioCreateSchema,
    PortfolioListQuerySchema,
    PortfolioResponseSchema,
    PortfolioUpdateSchema,
)


def _serialize_portfolio(dto) -> dict:
    return {
        "id": dto.id,
        "name": dto.name,
        "base_currency": dto.base_currency,
    }


@blp.route("")
class PortfolioCollection(MethodView):
    @blp.arguments(PortfolioListQuerySchema, location="query")
    @blp.response(200, PortfolioCollectionSchema())
    def get(self, query_args):
        result = list_portfolios(page=query_args["page"], page_size=query_args["page_size"])
        items = [_serialize_portfolio(item) for item in result.items]
        return {
            "items": items,
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }

    @blp.arguments(PortfolioCreateSchema)
    @blp.response(201, PortfolioResponseSchema())
    def post(self, payload):
        dto = create_portfolio(
            PortfolioCreateData(
                name=payload["name"],
                base_currency=payload["base_currency"],
            )
        )
        headers = {
            "Location": url_for("Portfolios.PortfolioItem", portfolio_id=dto.id, _external=False)
        }
        return _serialize_portfolio(dto), 201, headers


@blp.route("/<int:portfolio_id>")
class PortfolioItem(MethodView):
    @blp.response(200, PortfolioResponseSchema())
    def get(self, portfolio_id: int):
        dto = get_portfolio(portfolio_id)
        return _serialize_portfolio(dto)

    @blp.arguments(PortfolioUpdateSchema)
    @blp.response(200, PortfolioResponseSchema())
    def put(self, payload, portfolio_id: int):
        dto = update_portfolio(
            portfolio_id,
            PortfolioUpdateData(
                name=payload.get("name"),
                base_currency=payload.get("base_currency"),
            ),
        )
        return _serialize_portfolio(dto)

    @blp.response(204)
    def delete(self, portfolio_id: int):
        delete_portfolio(portfolio_id)
        return None
