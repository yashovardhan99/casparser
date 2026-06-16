from datetime import date
from decimal import Decimal
from typing import Any, List, Optional, Union

from attrs import define, field, frozen
from attrs.converters import optional

from .enums import CASFileType, FileType, TransactionType


@frozen
class StatementPeriod:
    from_: str
    to: str


@frozen
class InvestorInfo:
    """Investor Info data structure."""

    name: str
    email: str
    address: str
    mobile: str


@define(kw_only=True)
class TransactionData:
    """Mutual fund scheme transaction."""

    date: Union[date, str]
    description: str
    amount: Union[Decimal, float, None] = None
    units: Union[Decimal, float, None] = None
    nav: Union[Decimal, float, None] = None
    balance: Union[Decimal, float, None] = None
    type: TransactionType
    dividend_rate: Union[Decimal, float, None] = None
    # For GIFT_IN / GIFT_OUT transfers: the *counterparty* folio named in
    # the description (the destination for a gift-out, the source for a
    # gift-in). Lets a donor's statement be linked to the donee's across
    # two CAS files. None for all other transaction types.
    gift_folio: Optional[str] = None


@define(kw_only=True)
class SchemeValuation:
    """Scheme valuation as of a given date."""

    date: Union[date, str]
    nav: Union[Decimal, float]
    cost: Union[Decimal, float, None] = None
    value: Union[Decimal, float]


@define(kw_only=True)
class Scheme:
    """Mutual Fund Scheme data structure."""

    scheme: str
    advisor: Optional[str] = None
    rta_code: str
    rta: str
    type: Optional[str] = None
    isin: Optional[str] = None
    amfi: Optional[str] = None
    nominees: List[str] = field(default_factory=list)
    open: Union[Decimal, float]
    close: Union[Decimal, float]
    close_calculated: Union[Decimal, float]
    valuation: SchemeValuation
    transactions: List[TransactionData]


@frozen(kw_only=True)
class Folio:
    """Mutual Fund Folio data structure."""

    folio: str
    amc: str
    PAN: Optional[str] = None
    KYC: Optional[str] = None
    PANKYC: Optional[str] = None
    schemes: List[Scheme]


@frozen(kw_only=True)
class CASData:
    """CAS Parser return data type."""

    statement_period: StatementPeriod
    folios: List[Folio]
    investor_info: InvestorInfo
    cas_type: CASFileType
    file_type: FileType
    # Non-fatal data-quality warnings raised during parsing. Currently
    # populated by the CAMS/KFin DETAILED parser, which reconciles each
    # scheme's transactions against the printed running Unit Balance
    # column (the statement's own checksum). A non-empty list means a
    # transaction row was likely dropped or mis-parsed — the parse still
    # returns, but the data for that scheme should not be trusted blindly.
    parse_warnings: List[str] = field(default_factory=list)


@frozen
class DematOwner:
    name: str
    PAN: str


def convert_to_decimal(value: Any) -> Decimal:
    """Convert a value to Decimal, handling int, float, and str types."""
    if isinstance(value, Decimal):
        return value
    elif isinstance(value, (int, float)):
        return Decimal(str(value))
    elif isinstance(value, str):
        return Decimal(value.replace(",", ""))
    else:
        raise ValueError(f"Cannot convert {value} of type {type(value)} to Decimal")


@define(kw_only=True)
class Equity:
    name: Optional[str] = None
    isin: str
    num_shares: Decimal = field(converter=convert_to_decimal)
    price: Decimal = field(converter=convert_to_decimal)
    value: Decimal = field(converter=convert_to_decimal)
    # Depository (NSDL/CDSL) statements identify an equity holding only by
    # ISIN. The exchange trading symbol (and exchange) are backfilled from the
    # ISIN database after parsing (see parsers._isin.batch_equity_symbols) so
    # downstream consumers can price the holding via a symbol-keyed feed.
    symbol: Optional[str] = None
    exchange: Optional[str] = None


@define(kw_only=True)
class Bond:
    """Corporate / government bond holding.

    Two source layouts feed this model — both are present in the same
    NSDL CAS, one per demat-account flavour:

    - **NSDL-account summary form** (8 data cells):
      `ISIN | name | frequency | coupon_rate | maturity | num_bonds |
      face_value | value`. All optional fields populated.
    - **CDSL-account detailed form** (13 data cells, identical layout to
      detailed equity rows): we only get `num_bonds`, `market_price`,
      `value`. `coupon_rate`/`frequency`/`maturity`/`face_value` are
      `None` here — the detailed table doesn't include them.
    """

    name: Optional[str] = None
    isin: str
    num_bonds: Decimal = field(converter=convert_to_decimal)
    value: Decimal = field(converter=convert_to_decimal)
    face_value: Optional[Decimal] = field(
        converter=optional(convert_to_decimal), default=None
    )
    coupon_rate: Optional[Decimal] = field(
        converter=optional(convert_to_decimal), default=None
    )
    coupon_frequency: Optional[str] = None
    maturity_date: Optional[str] = None
    market_price: Optional[Decimal] = field(
        converter=optional(convert_to_decimal), default=None
    )


@define(kw_only=True)
class MutualFund:
    name: Optional[str] = None
    isin: str
    # Depository (NSDL/CDSL) statements identify an MF holding only by
    # ISIN — unlike RTA (CAMS/KFin) `Scheme` rows they carry no AMFI code
    # or scheme type. These are backfilled from the ISIN database after
    # parsing (see parsers._isin.batch_isin_metadata) so a demat holding
    # lines up with the same scheme from an RTA CAS on `amfi` / `type`.
    amfi: Optional[str] = None
    type: Optional[str] = None
    balance: Decimal = field(converter=convert_to_decimal)
    nav: Decimal = field(converter=convert_to_decimal)
    value: Decimal = field(converter=convert_to_decimal)
    avg_cost: Optional[Decimal] = field(
        converter=optional(convert_to_decimal), default=None
    )
    total_cost: Optional[Decimal] = field(
        converter=optional(convert_to_decimal), default=None
    )
    ucc: Optional[str] = None
    folio: Optional[str] = None
    pnl: Optional[Decimal] = field(converter=optional(convert_to_decimal), default=None)
    return_: Optional[Decimal] = field(
        converter=optional(convert_to_decimal), default=None
    )


@define(kw_only=True)
class DematAccount:
    name: str
    type: str
    dp_id: Optional[str] = ""
    client_id: Optional[str] = ""
    folios: int
    balance: Decimal = field(converter=convert_to_decimal)
    owners: List[DematOwner]
    equities: List[Equity]
    mutual_funds: List[MutualFund]
    bonds: List[Bond] = field(default_factory=list)


@define(kw_only=True)
class NSDLCASData:
    accounts: List[DematAccount]
    statement_period: StatementPeriod
    investor_info: InvestorInfo
    file_type: FileType
