import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_sell_without_position_shows_error_banner(ui: Page, unique_name: str) -> None:
    ui.get_by_test_id("portfolio-name-input").fill(unique_name)
    ui.get_by_test_id("create-portfolio-submit").click()
    ui.get_by_role("link", name=unique_name).click()
    expect(ui).to_have_url(re.compile(r"/ui/portfolio\.html\?id=\d+"))

    ui.get_by_test_id("trade-ticker").fill("TSLA")
    ui.get_by_test_id("trade-type").select_option("SELL")
    ui.get_by_test_id("trade-quantity").fill("5")
    ui.get_by_test_id("trade-price").fill("200")
    ui.get_by_test_id("trade-submit").click()

    banner = ui.get_by_test_id("error-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("INSUFFICIENT_POSITION")
