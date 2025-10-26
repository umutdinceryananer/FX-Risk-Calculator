"""Schemas for API responses."""

from __future__ import annotations

from marshmallow import Schema, fields


class HealthStatusSchema(Schema):
    status = fields.String(required=True)
    app = fields.String()


class HealthRatesSchema(Schema):
    status = fields.String(required=True)
    source = fields.String(allow_none=True)
    base_currency = fields.String(allow_none=True)
    last_updated = fields.String(allow_none=True)
    stale = fields.Boolean(allow_none=True)


class CurrencyValidationRequestSchema(Schema):
    code = fields.String(load_default=None)


class CurrencyValidationResponseSchema(Schema):
    code = fields.String(required=True)
    message = fields.String(required=True)


class RefreshSuccessSchema(Schema):
    message = fields.String(required=True)
    source = fields.String(required=True)
    base_currency = fields.String(required=True)
    as_of = fields.String(required=True)


class RefreshThrottleSchema(Schema):
    message = fields.String(required=True)
    retry_after = fields.Integer(required=True)


class ErrorMessageSchema(Schema):
    message = fields.String(required=True)
