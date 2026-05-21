"""E2E: trade history page."""

import pytest


@pytest.mark.e2e
def test_history_shows_trade_after_buy(page, base_url, require_backend, unique_name):
    page.context.add_init_script(
        "localStorage.setItem('spt_auth', JSON.stringify({user:'admin'}))"
    )
    page.goto(f"{base_url}/ui/")

    # Create portfolio
    page.fill('[data-testid="portfolio-name-input"]', unique_name)
    page.select_option('[data-testid="portfolio-currency-select"]', "USD")
    page.click('[data-testid="create-portfolio-submit"]')
    page.wait_for_selector('[data-testid="success-toast"]', state="visible")

    # Navigate to portfolio
    page.click(f'text={unique_name}')
    page.wait_for_selector('[data-testid="trade-form"]')

    # Add BUY trade
    page.fill('[data-testid="trade-ticker"]', "AAPL")
    page.select_option('[data-testid="trade-type"]', "BUY")
    page.fill('[data-testid="trade-quantity"]', "5")
    page.fill('[data-testid="trade-price"]', "150")
    page.click('[data-testid="trade-submit"]')
    page.wait_for_selector('[data-testid="position-row-AAPL"]')

    # Navigate to history page
    page.click('[data-testid="nav-history"]')
    page.wait_for_selector('[data-testid="history-table"]')

    # Verify trade row exists
    rows = page.locator("#history-table tbody tr")
    assert rows.count() >= 1

    # First row should contain AAPL
    first_row = rows.first.inner_text()
    assert "AAPL" in first_row


@pytest.mark.e2e
def test_history_ticker_filter(page, base_url, require_backend, unique_name):
    page.context.add_init_script(
        "localStorage.setItem('spt_auth', JSON.stringify({user:'admin'}))"
    )
    page.goto(f"{base_url}/ui/")

    # Create portfolio
    page.fill('[data-testid="portfolio-name-input"]', unique_name)
    page.click('[data-testid="create-portfolio-submit"]')
    page.wait_for_selector('[data-testid="success-toast"]', state="visible")
    page.click(f'text={unique_name}')
    page.wait_for_selector('[data-testid="trade-form"]')

    # Add two trades with different tickers
    for ticker, qty in [("AAPL", "3"), ("TSLA", "2")]:
        page.fill('[data-testid="trade-ticker"]', ticker)
        page.select_option('[data-testid="trade-type"]', "BUY")
        page.fill('[data-testid="trade-quantity"]', qty)
        page.fill('[data-testid="trade-price"]', "100")
        page.click('[data-testid="trade-submit"]')
        page.wait_for_selector(f'[data-testid="position-row-{ticker}"]')

    # Go to history
    page.click('[data-testid="nav-history"]')
    page.wait_for_selector('[data-testid="history-table"]')

    # Filter by AAPL
    page.fill('[data-testid="ticker-filter"]', "AAPL")
    page.click('[data-testid="filter-btn"]')
    page.wait_for_timeout(500)

    rows = page.locator("#history-table tbody tr")
    assert rows.count() >= 1
    for i in range(rows.count()):
        assert "AAPL" in rows.nth(i).inner_text()
        assert "TSLA" not in rows.nth(i).inner_text()
