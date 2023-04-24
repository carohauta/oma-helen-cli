from datetime import date, datetime, timedelta
from .const import HTTP_READ_TIMEOUT
from requests import get
from bs4 import BeautifulSoup


class VattenfallPriceClient:
    HOURLY_PRICES_URL = "https://www.vattenfall.fi/api/price/spot/{date}/{date}?lang=fi"
    DAILY_AVERAGE_PRICES_URL = "https://www.vattenfall.fi/api/price/spot/average/{start_date}/{end_date}?lang=fi"
    HEADERS = { 'User-Agent': 'Mozilla/5.0' }
    
    def get_hourly_prices_for_day(self, day: date):
        url = self.HOURLY_PRICES_URL.format(date=day)
        response = get(url, headers=self.HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            print("Could not fetch prices. Response code was: " + str(response.status_code))

    def get_daily_average_prices_between_dates(self, start_date: date, end_date: date):
        url = self.DAILY_AVERAGE_PRICES_URL.format(start_date=start_date, end_date=end_date)
        response = get(url, headers=self.HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            print("Could not fetch prices. Response code was: " + str(response.status_code))


class HelenPrices:
    def __init__(self):
        self.timestamp = datetime.now()


class HelenMarketPrices(HelenPrices):
    def __init__(self, last_month, current_month, next_month):
        super().__init__()
        self.last_month: float = last_month
        self.current_month: float = current_month
        self.next_month: float = next_month


class HelenExchangePrices(HelenPrices):
    def __init__(self, margin):
        super().__init__()
        self.margin: float = margin


class HelenPriceClient:
    MARKET_PRICE_ELECTRICITY_URL = "https://www.helen.fi/sahko/sahkosopimus/markkinahinta"
    EXCHANGE_ELECTRICITY_URL = "https://www.helen.fi/sahko/sahkosopimus/porssisahko"

    _helen_market_price_prices: HelenMarketPrices = None
    _helen_exchange_prices: HelenExchangePrices = None
        

    def _are_market_price_prices_valid(self):
        return self._is_helen_prices_valid(self._helen_market_price_prices)


    def _are_exchange_prices_valid(self):
        return self._is_helen_prices_valid(self._helen_exchange_prices)

    
    def _is_helen_prices_valid(self, helen_prices: HelenPrices):
        """If the latest price scrape has happened within the last hour, then use cache"""

        now = datetime.now()
        if helen_prices is None:
            return False
        were_market_prices_scraped_within_hour = now-timedelta(hours=1) <= helen_prices.timestamp <= now
        return were_market_prices_scraped_within_hour


    def _scrape_market_price_prices(self):
        kwh_substring = " c/kWh"

        price_site_response = get(self.MARKET_PRICE_ELECTRICITY_URL, timeout=HTTP_READ_TIMEOUT)
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


    def get_market_price_prices(self) -> HelenMarketPrices:
        """Get the prices for last month, current month and next month for the Market Price contract"""
        if self._are_market_price_prices_valid():
            return self._helen_market_price_prices
        last_month_price, current_month_price, next_month_price = self._scrape_market_price_prices()

        self._helen_market_price_prices = HelenMarketPrices(last_month_price, current_month_price, next_month_price)
        return self._helen_market_price_prices


    def _scrape_exchange_prices(self):
        price_site_response = get(self.EXCHANGE_ELECTRICITY_URL, timeout=HTTP_READ_TIMEOUT)
        price_site_soup = BeautifulSoup(price_site_response.text, "html.parser")

        element = price_site_soup.select_one(f'span.product-info-block__data--price')
        margin = element.text

        return float(margin.replace(",", "."))


    def get_exchange_prices(self) -> HelenExchangePrices:
        """Get the margin price for the Exchange Electricity contract"""
        if self._are_exchange_prices_valid():
            return self._helen_exchange_prices
        margin = self._scrape_exchange_prices()

        self._helen_exchange_prices = HelenExchangePrices(margin)
        return self._helen_exchange_prices