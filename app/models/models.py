import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TradeType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    telegram_link_token: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)

    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[list["Trade"]] = relationship(
        "Trade", back_populates="portfolio", cascade="all, delete-orphan"
    )


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("portfolio_id", "ticker", name="uq_portfolio_ticker"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    average_cost: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    realized_pnl: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_portfolio_ticker_executed", "portfolio_id", "ticker", "executed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_type: Mapped[TradeType] = mapped_column(Enum(TradeType), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    commission: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="trades")


class SignalAnalysis(Base):
    __tablename__ = "signal_analyses"
    __table_args__ = (
        Index("ix_signal_analyses_portfolio_ticker", "portfolio_id", "ticker"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    rsi_score: Mapped[int] = mapped_column(Integer, nullable=False)
    macd_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bollinger_score: Mapped[int] = mapped_column(Integer, nullable=False)
    stochastic_score: Mapped[int] = mapped_column(Integer, nullable=False)
    rsi_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    latest_close: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gemini_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio")
