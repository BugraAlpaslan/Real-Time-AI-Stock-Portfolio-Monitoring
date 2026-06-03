import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_summary_displays_all_pnl_cards(ui: Page, unique_name: str) -> None:
    ui.get_by_test_id("portfolio-name-input").fill(unique_name)
    ui.get_by_test_id("create-portfolio-submit").click()
    ui.get_by_role("link", name=unique_name).click()
    portfolio_id = re.search(r"id=(\d+)", ui.url).group(1)

    ui.get_by_test_id("trade-ticker").fill("MSFT")
    ui.get_by_test_id("trade-type").select_option("BUY")
    ui.get_by_test_id("trade-quantity").fill("5")
    ui.get_by_test_id("trade-price").fill("200")
    ui.get_by_test_id("trade-submit").click()

    base = ui.url.split("/ui/")[0]
    ui.goto(f"{base}/ui/summary.html?id={portfolio_id}")

    expect(ui.get_by_test_id("realized-pnl")).to_be_visible()
    expect(ui.get_by_test_id("unrealized-pnl")).to_be_visible()
    expect(ui.get_by_test_id("total-pnl")).to_be_visible()

    realized = float(ui.get_by_test_id("realized-pnl").locator(".pnl-value").inner_text())
    unrealized = float(ui.get_by_test_id("unrealized-pnl").locator(".pnl-value").inner_text())
    total = float(ui.get_by_test_id("total-pnl").locator(".pnl-value").inner_text())
    assert abs(total - (realized + unrealized)) < 0.05

    rows = ui.locator("#summary-positions tbody tr")
    expect(rows).to_have_count(1)
