from helenservice.client.api_client import HelenApiClient
from getpass import getpass

from helenservice.client.price_client import HelenContractType, HelenPriceClient


def main():
#    print("Log in to Oma Helen")
#    username = input("Username: ")
#    password = getpass()
#
#    api_client = HelenApiClient()
#
#    api_client.login(username, password)
#
#    monthly_measurements = api_client.get_monthly_measurements()
#    did = api_client.get_delivery_site_id()
#    bp = api_client.get_contract_base_price()
#
#    print(monthly_measurements)

    price_client = HelenPriceClient(HelenContractType.MARKET_PRICE)
    price = price_client.get_electricity_prices()
    print(price)


if __name__ == "__main__":
    main()
