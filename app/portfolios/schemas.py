"""Marshmallow schemas for portfolio CRUD endpoints."""

from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validates_schema
from marshmallow.validate import Length, Range


class PortfolioBaseSchema(Schema):
    """Shared fields for portfolio payloads."""

    name = fields.String(required=True, validate=Length(min=1, max=100))
    base_currency = fields.String(
        required=True,
        data_key="base_currency",
        validate=Length(min=3, max=3),
    )


class PortfolioCreateSchema(PortfolioBaseSchema):
    """Schema for portfolio creation payloads."""

    pass


class PortfolioUpdateSchema(Schema):
    """Schema for partial portfolio updates."""

    name = fields.String(load_default=None, validate=Length(min=1, max=100))
    base_currency = fields.String(
        load_default=None,
        data_key="base_currency",
        validate=Length(min=3, max=3),
    )

    @validates_schema
    def validate_non_empty(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one field must be supplied for update.")


class PortfolioResponseSchema(Schema):
    """Serialized portfolio representation."""

    id = fields.Integer(required=True)
    name = fields.String(required=True)
    base_currency = fields.String(required=True, data_key="base_currency")


class PortfolioCollectionSchema(Schema):
    """Envelope for paginated portfolio responses."""

    items = fields.List(fields.Nested(PortfolioResponseSchema), required=True)
    total = fields.Integer(required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True, data_key="page_size")


class PortfolioListQuerySchema(Schema):
    """Query parameters for portfolio listings."""

    page = fields.Integer(load_default=1, validate=Range(min=1))
    page_size = fields.Integer(
        load_default=20,
        data_key="page_size",
        validate=Range(min=1, max=100),
    )
