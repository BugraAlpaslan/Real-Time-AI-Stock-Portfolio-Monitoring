import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_sell_after_buy_creates_realized_pnl(ui: Page, unique_name: str) -> None:
    ui.get_by_test_id("portfolio-name-input").fill(unique_name)
    ui.get_by_test_id("create-portfolio-submit").click()
    ui.get_by_role("link", name=unique_name).click()
    expect(ui).to_have_url(re.compile(r"/ui/portfolio\.html\?id=\d+"))

    portfolio_url = ui.url
    portfolio_id = re.search(r"id=(\d+)", portfolio_url).group(1)

    def add_trade(trade_type: str, qty: str, price: str) -> None:
        ui.get_by_test_id("trade-ticker").fill("AAPL")
        ui.get_by_test_id("trade-type").select_option(trade_type)
        ui.get_by_test_id("trade-quantity").fill(qty)
        ui.get_by_test_id("trade-price").fill(price)
        ui.get_by_test_id("trade-submit").click()

    add_trade("BUY", "10", "100")
    expect(ui.get_by_test_id("position-row-AAPL")).to_be_visible()
    add_trade("SELL", "5", "130")
    expect(ui.get_by_test_id("position-qty-AAPL")).to_have_text("5")

    ui.goto(
        f"{ui.url.split('/ui/')[0]}/ui/summary.html?id={portfolio_id}",
        wait_until="networkidle",
    )
    realized = ui.get_by_test_id("realized-pnl").locator(".pnl-value")
    expect(realized).to_be_visible()
    value = float(realized.inner_text())
    assert abs(value - 150.0) < 1.0, f"expected realized ~150, got {value}"
