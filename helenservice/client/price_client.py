from enum import Enum, auto
from requests import get
from bs4 import BeautifulSoup


class HelenMarketPrices:
    def __init__(self, last_month, current_month, next_month):
        self.last_month: float = last_month
        self.current_month: float = current_month
        self.next_month: float = next_month


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

        element = price_site_soup.select_one(f'td:-soup-contains("{kwh_substring}")')
        last_month_price = element.text # td -> <text>
        if kwh_substring in last_month_price:
            last_month_price = last_month_price[:last_month_price.index(kwh_substring)]
            last_month_price = float(last_month_price.replace(",", "."))

        element = element.find_next_sibling()
        current_month_price = element.next_element.text # td -> strong -> <text>
        if kwh_substring in current_month_price:
            current_month_price = current_month_price[:current_month_price.index(kwh_substring)]
            current_month_price = float(current_month_price.replace(",", "."))

        element = element.find_next_sibling()
        next_month_price = element.text # td -> <text>
        if kwh_substring in next_month_price:
            next_month_price = next_month_price[:next_month_price.index(kwh_substring):]
            next_month_price = float(next_month_price.replace(",", "."))
        else: 
            next_month_price = None

        return last_month_price, current_month_price, next_month_price