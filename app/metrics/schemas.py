"""Schema definitions for metrics endpoints."""

from __future__ import annotations

from decimal import Decimal

from marshmallow import Schema, fields


class PortfolioValueQuerySchema(Schema):
    """Query parameters for portfolio value metrics."""

    base = fields.String(load_default=None, data_key="base")


class PortfolioValueResponseSchema(Schema):
    """Serialized portfolio value response."""

    portfolio_id = fields.Integer(required=True, data_key="portfolio_id")
    portfolio_base = fields.String(required=True, data_key="portfolio_base")
    view_base = fields.String(required=True, data_key="view_base")
    value = fields.Decimal(required=True, as_string=True)
    priced = fields.Integer(required=True)
    unpriced = fields.Integer(required=True)
    as_of = fields.DateTime(allow_none=True, data_key="as_of")

