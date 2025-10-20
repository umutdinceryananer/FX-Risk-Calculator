"""Route handlers for portfolio position endpoints."""

from __future__ import annotations

from flask import url_for
from flask.views import MethodView

from app.models import PositionType
from app.services import (
    PositionCreateData,
    PositionListParams,
    PositionUpdateData,
    create_position,
    delete_position,
    get_position,
    list_positions,
    update_position,
)

from . import blp
from .schemas import (
    PositionCollectionSchema,
    PositionCreateSchema,
    PositionListQuerySchema,
    PositionResponseSchema,
    PositionUpdateSchema,
)


def _serialize(dto):
    return {
        "id": dto.id,
        "currency_code": dto.currency_code,
        "amount": dto.amount,
        "side": dto.side.value if isinstance(dto.side, PositionType) else str(dto.side).upper(),
        "created_at": dto.created_at,
    }


@blp.route("/<int:portfolio_id>/positions")
class PositionCollection(MethodView):
    @blp.arguments(PositionListQuerySchema, location="query")
    @blp.response(200, PositionCollectionSchema())
    def get(self, query_params, portfolio_id: int):
        params = PositionListParams(
            portfolio_id=portfolio_id,
            page=query_params["page"],
            page_size=query_params["page_size"],
            currency=query_params.get("currency"),
            side=query_params.get("side"),
            sort=query_params.get("sort"),
            direction=query_params.get("direction"),
        )
        result = list_positions(params)
        return {
            "items": [_serialize(item) for item in result.items],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }

    @blp.arguments(PositionCreateSchema)
    @blp.response(201, PositionResponseSchema())
    def post(self, payload, portfolio_id: int):
        dto = create_position(
            PositionCreateData(
                portfolio_id=portfolio_id,
                currency_code=payload["currency_code"],
                amount=payload["amount"],
                side=payload.get("side"),
            )
        )
        headers = {
            "Location": url_for(
                "Positions.PositionItem",
                portfolio_id=portfolio_id,
                position_id=dto.id,
                _external=False,
            )
        }
        return _serialize(dto), 201, headers


@blp.route("/<int:portfolio_id>/positions/<int:position_id>")
class PositionItem(MethodView):
    @blp.response(200, PositionResponseSchema())
    def get(self, portfolio_id: int, position_id: int):
        dto = get_position(portfolio_id, position_id)
        return _serialize(dto)

    @blp.arguments(PositionUpdateSchema)
    @blp.response(200, PositionResponseSchema())
    def put(self, payload, portfolio_id: int, position_id: int):
        dto = update_position(
            portfolio_id,
            position_id,
            PositionUpdateData(
                currency_code=payload.get("currency_code"),
                amount=payload.get("amount"),
                side=payload.get("side"),
            ),
        )
        return _serialize(dto)

    @blp.response(204)
    def delete(self, portfolio_id: int, position_id: int):
        delete_position(portfolio_id, position_id)
        return None
