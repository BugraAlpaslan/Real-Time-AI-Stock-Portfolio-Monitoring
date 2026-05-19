import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_user_creates_portfolio_and_sees_it_in_list(ui: Page, unique_name: str) -> None:
    ui.get_by_test_id("portfolio-name-input").fill(unique_name)
    ui.get_by_test_id("portfolio-currency-select").select_option("USD")
    ui.get_by_test_id("create-portfolio-submit").click()

    expect(ui.get_by_test_id("success-toast")).to_be_visible()
    expect(ui.get_by_test_id("portfolio-list")).to_contain_text(unique_name)
