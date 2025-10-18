from marshmallow import Schema, fields


class PortfolioValueQuerySchema(Schema):
    base = fields.String(load_default=None, data_key="base")


class PortfolioValueResponseSchema(Schema):
    portfolio_id = fields.Integer(required=True, data_key="portfolio_id")
    portfolio_base = fields.String(required=True, data_key="portfolio_base")
    view_base = fields.String(required=True, data_key="view_base")
    value = fields.Decimal(required=True, as_string=True)
    priced = fields.Integer(required=True)
    unpriced = fields.Integer(required=True)
    as_of = fields.DateTime(allow_none=True, data_key="as_of")


class PortfolioExposureQuerySchema(Schema):
    base = fields.String(load_default=None, data_key="base")
    top_n = fields.Integer(load_default=None, data_key="top_n")


class PortfolioExposureItemSchema(Schema):
    currency_code = fields.String(required=True, data_key="currency_code")
    net_native = fields.Decimal(required=True, as_string=True, data_key="net_native")
    base_equivalent = fields.Decimal(required=True, as_string=True, data_key="base_equivalent")


class PortfolioExposureResponseSchema(Schema):
    portfolio_id = fields.Integer(required=True, data_key="portfolio_id")
    portfolio_base = fields.String(required=True, data_key="portfolio_base")
    view_base = fields.String(required=True, data_key="view_base")
    exposures = fields.List(fields.Nested(PortfolioExposureItemSchema), required=True)
    priced = fields.Integer(required=True)
    unpriced = fields.Integer(required=True)
    as_of = fields.DateTime(allow_none=True, data_key="as_of")


class PortfolioDailyPnLQuerySchema(Schema):
    base = fields.String(load_default=None, data_key="base")


class PortfolioDailyPnLResponseSchema(Schema):
    portfolio_id = fields.Integer(required=True, data_key="portfolio_id")
    portfolio_base = fields.String(required=True, data_key="portfolio_base")
    view_base = fields.String(required=True, data_key="view_base")
    pnl = fields.Decimal(required=True, as_string=True)
    value_current = fields.Decimal(required=True, as_string=True, data_key="value_current")
    value_previous = fields.Decimal(allow_none=True, as_string=True, data_key="value_previous")
    as_of = fields.DateTime(allow_none=True, data_key="as_of")
    prev_date = fields.DateTime(allow_none=True, data_key="prev_date")
    positions_changed = fields.Boolean(required=True, data_key="positions_changed")
    priced_current = fields.Integer(required=True, data_key="priced_current")
    unpriced_current = fields.Integer(required=True, data_key="unpriced_current")
    priced_previous = fields.Integer(required=True, data_key="priced_previous")
    unpriced_previous = fields.Integer(required=True, data_key="unpriced_previous")

