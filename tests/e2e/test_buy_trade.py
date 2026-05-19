import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_user_adds_buy_trade_and_position_appears(ui: Page, unique_name: str) -> None:
    ui.get_by_test_id("portfolio-name-input").fill(unique_name)
    ui.get_by_test_id("create-portfolio-submit").click()
    ui.get_by_role("link", name=unique_name).click()
    expect(ui).to_have_url(re.compile(r"/ui/portfolio\.html\?id=\d+"))

    ui.get_by_test_id("trade-ticker").fill("AAPL")
    ui.get_by_test_id("trade-type").select_option("BUY")
    ui.get_by_test_id("trade-quantity").fill("10")
    ui.get_by_test_id("trade-price").fill("150")
    ui.get_by_test_id("trade-commission").fill("0")
    ui.get_by_test_id("trade-submit").click()

    row = ui.get_by_test_id("position-row-AAPL")
    expect(row).to_be_visible()
    expect(ui.get_by_test_id("position-qty-AAPL")).to_have_text("10")
    expect(ui.get_by_test_id("position-avg-AAPL")).to_have_text("150")
