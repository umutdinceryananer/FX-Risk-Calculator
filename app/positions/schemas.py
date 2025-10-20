"""Marshmallow schemas for portfolio position endpoints."""

from __future__ import annotations

from decimal import Decimal

from marshmallow import Schema, ValidationError, fields, validates, validates_schema
from marshmallow.validate import Length, OneOf, Range

from app.models import PositionType


POSITION_SIDE_CHOICES = tuple(member.value for member in PositionType)


class PositionBaseSchema(Schema):
    """Common fields for position payloads."""

    currency_code = fields.String(required=True, validate=Length(equal=3), data_key="currency_code")
    amount = fields.Decimal(
        required=True,
        as_string=True,
        data_key="amount",
        allow_nan=False,
    )
    side = fields.String(
        load_default=PositionType.LONG.value,
        data_key="side",
    )

    @validates("side")
    def validate_side(self, value, **kwargs):
        if value is None:
            return
        if str(value).strip().upper() not in POSITION_SIDE_CHOICES:
            raise ValidationError("Invalid position side.", field_name="side")

    @validates_schema
    def validate_amount_positive(self, data, **kwargs):
        amount = data.get("amount")
        if amount is None:
            return

        if isinstance(amount, Decimal):
            numeric = amount
        else:
            try:
                numeric = Decimal(str(amount))
            except Exception as exc:  # pragma: no cover - marshmallow handles formatting errors
                raise ValidationError("Invalid amount value.", field_name="amount") from exc

        if numeric <= 0:
            raise ValidationError("Amount must be greater than zero.", field_name="amount")


class PositionCreateSchema(PositionBaseSchema):
    """Schema for creating a new position."""

    pass


class PositionUpdateSchema(Schema):
    """Schema for updating an existing position."""

    currency_code = fields.String(load_default=None, validate=Length(equal=3), data_key="currency_code")
    amount = fields.Decimal(
        load_default=None,
        as_string=True,
        allow_nan=False,
        data_key="amount",
    )
    side = fields.String(
        load_default=None,
        data_key="side",
    )

    @validates("side")
    def validate_side(self, value, **kwargs):
        if value is None:
            return
        if str(value).strip().upper() not in POSITION_SIDE_CHOICES:
            raise ValidationError("Invalid position side.", field_name="side")

    @validates_schema
    def validate_payload(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one field must be supplied.")

        amount = data.get("amount")
        if amount is not None:
            if isinstance(amount, Decimal):
                numeric = amount
            else:
                numeric = Decimal(str(amount))
            if numeric <= 0:
                raise ValidationError("Amount must be greater than zero.", field_name="amount")


class PositionResponseSchema(Schema):
    """Serialized representation of a position."""

    id = fields.Integer(required=True)
    currency_code = fields.String(required=True, data_key="currency_code")
    amount = fields.Decimal(required=True, as_string=True, data_key="amount")
    side = fields.String(required=True, data_key="side")
    created_at = fields.DateTime(required=True, data_key="created_at")


class PositionCollectionSchema(Schema):
    """Envelope for a paginated list of positions."""

    items = fields.List(fields.Nested(PositionResponseSchema), required=True)
    total = fields.Integer(required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True, data_key="page_size")


class PositionListQuerySchema(Schema):
    """Query parameters for listing positions."""

    page = fields.Integer(load_default=1, validate=Range(min=1))
    page_size = fields.Integer(load_default=25, data_key="page_size", validate=Range(min=1, max=200))
    currency = fields.String(load_default=None, validate=Length(equal=3))
    side = fields.String(load_default=None)
    sort = fields.String(
        load_default="created_at",
        validate=OneOf(["currency", "amount", "side", "created_at"]),
    )
    direction = fields.String(
        load_default="asc",
        validate=OneOf(["asc", "desc"]),
    )

    @validates("side")
    def validate_side(self, value, **kwargs):
        if value is None:
            return
        if str(value).strip().upper() not in POSITION_SIDE_CHOICES:
            raise ValidationError("Invalid position side.", field_name="side")


class PositionPathParamsSchema(Schema):
    """Path parameters for position operations."""

    portfolio_id = fields.Integer(required=True, validate=Range(min=1), data_key="portfolio_id")
    position_id = fields.Integer(required=True, validate=Range(min=1), data_key="position_id")
