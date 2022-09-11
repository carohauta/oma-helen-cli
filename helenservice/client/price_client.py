from enum import Enum, auto
from requests import get
from bs4 import BeautifulSoup


class HelenMarketPrices:
    def __init__(self, last_month, current_month, next_month):
        self.last_month = last_month
        self.current_month = current_month
        self.next_month = next_month


class HelenContractType(Enum):
    MARKET_PRICE = auto()


class HelenPriceClient:
    MARKET_PRICE_ELECTRICITY_URL = "https://www.helen.fi/sahko/sahkosopimus/markkinahinta"

    def __init__(self, contract_type: HelenContractType):
        self.contract_type = contract_type
        if contract_type == HelenContractType.MARKET_PRICE:
            self.url = self.MARKET_PRICE_ELECTRICITY_URL

    def get_electricity_prices(self):
        """Get the pricing for the current contract type"""

        if self.contract_type == HelenContractType.MARKET_PRICE:
            return self._get_market_price_prices()

    def _get_market_price_prices(self) -> HelenMarketPrices:
        last_month_price, current_month_price, next_month_price = self._scrape_market_price_prices()

        return HelenMarketPrices(last_month_price, current_month_price, next_month_price)

    def _scrape_market_price_prices(self):
        kwh_substring = " c/kWh"

        price_site_response = get(self.url)
        price_site_soup = BeautifulSoup(price_site_response.text, "html.parser")

        element = price_site_soup.select_one('td:-soup-contains("kWh")')
        last_month_price_text = element.text # td -> <text>
        if kwh_substring in last_month_price_text:
            last_month_price_text = last_month_price_text[:last_month_price_text.index(kwh_substring)]

        element = element.find_next_sibling()
        current_month_price_text = element.next_element.text # td -> strong -> <text>
        if kwh_substring in current_month_price_text:
            current_month_price_text = current_month_price_text[:current_month_price_text.index(kwh_substring)]

        element = element.find_next_sibling()
        next_month_price_text = element.text # td -> <text>
        if kwh_substring in next_month_price_text:
            next_month_price_text = next_month_price_text[:next_month_price_text.index(kwh_substring):]
        else: 
            next_month_price_text = None

        # TODO parse float
        return last_month_price_text, current_month_price_text, next_month_price_text