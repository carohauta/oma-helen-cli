from datetime import datetime, timedelta
from enum import Enum, auto
from .const import HTTP_READ_TIMEOUT
from requests import get
from bs4 import BeautifulSoup


class HelenMarketPrices:
    def __init__(self, last_month, current_month, next_month):
        self.last_month: float = last_month
        self.current_month: float = current_month
        self.next_month: float = next_month
        self.timestamp = datetime.now()


class HelenContractType(Enum):
    MARKET_PRICE = auto()


class HelenPriceClient:
    MARKET_PRICE_ELECTRICITY_URL = "https://www.helen.fi/sahko/sahkosopimus/markkinahinta"

    _helen_market_price_prices: HelenMarketPrices = None

    def __init__(self, contract_type: HelenContractType):
        self._contract_type = contract_type
        if contract_type == HelenContractType.MARKET_PRICE:
            self.url = self.MARKET_PRICE_ELECTRICITY_URL

    def get_electricity_prices(self):
        """Get the pricing for the current contract type"""

        if self._contract_type == HelenContractType.MARKET_PRICE:
            if self._are_market_price_prices_valid():
                return self._helen_market_price_prices
            return self._get_market_price_prices()
        return None

    def _are_market_price_prices_valid(self):
        """If the latest price scrape has happened within the last hour, then use cache"""

        now = datetime.now()
        if self._helen_market_price_prices is None:
            return False
        were_market_prices_scraped_within_hour = now-timedelta(hours=1) <= self._helen_market_price_prices.timestamp <= now
        return were_market_prices_scraped_within_hour

    def _get_market_price_prices(self) -> HelenMarketPrices:
        last_month_price, current_month_price, next_month_price = self._scrape_market_price_prices()

        self._helen_market_price_prices = HelenMarketPrices(last_month_price, current_month_price, next_month_price)
        return self._helen_market_price_prices

    def _scrape_market_price_prices(self):
        kwh_substring = " c/kWh"

        price_site_response = get(self.url, timeout=HTTP_READ_TIMEOUT)
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