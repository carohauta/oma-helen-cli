from cmd import Cmd
from datetime import date, datetime
from .api_client import HelenApiClient
from getpass import getpass
from .price_client import HelenPriceClient
from .utils import get_month_date_range_by_date
import json

def _json_serializer(value):
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d%H%M%S")
    else:
        return value.__dict__

class HelenCLIPrompt(Cmd):
    prompt = "helen-cli> "
    intro = "Type ? to list commands"

    helen_price_client = HelenPriceClient()

    tax = 0.1 # 10%
    margin = helen_price_client.get_exchange_prices().margin
    api_client = HelenApiClient(tax, margin)


    def __init__(self, username, password):
        super(HelenCLIPrompt, self).__init__()
        self.api_client.login(username, password)

    def do_exit(self, input=None):
        """Exit the CLI"""

        self.api_client.close()
        print("Bye")
        return True

    def do_calculate_transfer_fees_between_dates(self, input=None):
        """Calculate the transfer fees between a start date and an end date
        The provided dates should be presented in format 'YYYY-mm-dd'

        Usage example:
        calculate_transfer_fee_between_dates 2022-12-01 2022-12-31
        """

        if input is None:
            print("Please provide proper start and end dates in format 'YYYY-mm-dd'")
        else:
            try:
                start_date_str, end_date_str = str(input).split(' ')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                if start_date > end_date: 
                    print("Start date must be before end date")
                    raise ValueError()
                price = self.api_client.calculate_transfer_fees_between_dates(start_date, end_date)
                print(price)
            except ValueError:
                print("Please provide proper start and end dates in format 'YYYY-mm-dd'")

    def do_calculate_spot_cost_between_dates(self, input=None):
        """Calculate the price of your Exchange Electricity (spot) contract between a start date and an end date
        The provided dates should be presented in format 'YYYY-mm-dd'

        Includes 10% tax. The price returned is in euros.

        Usage example:
        calculate_spot_cost_between_dates 2022-12-01 2022-12-31
        """

        if input is None:
            print("Please provide proper start and end dates in format 'YYYY-mm-dd'")
        else:
            try:
                start_date_str, end_date_str = str(input).split(' ')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                if start_date > end_date: 
                    print("Start date must be before end date")
                    raise ValueError()
                price = self.api_client.calculate_total_costs_by_spot_prices_between_dates(start_date, end_date)
                print(price)
            except ValueError:
                print("Please provide proper start and end dates in format 'YYYY-mm-dd'")

    def do_calculate_the_impact_of_usage_between_dates(self, input=None):
        """Calculate the impact of usage for Helen Smart Electricity Guarantee contract between a start date and an end date
        The provided dates should be presented in format 'YYYY-mm-dd'

        Usage example:
        calculate_the_impact_of_usage_between_dates 2022-12-01 2022-12-31
        """

        if input is None:
            print("Please provide proper start and end dates in format 'YYYY-mm-dd'")
        else:
            try:
                start_date_str, end_date_str = str(input).split(' ')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                if start_date > end_date: 
                    print("Start date must be before end date")
                    raise ValueError()
                impact = self.api_client.calculate_impact_of_usage_between_dates(start_date, end_date)
                print(impact)
            except ValueError:
                print("Please provide proper start and end dates in format 'YYYY-mm-dd'")

    def do_get_monthly_measurements_json(self, input=None):
        """Get the monthly electricity measurements of the on-going year as JSON"""

        year = date.today().year
        monthly_measurements = self.api_client.get_monthly_measurements_by_year(year)
        monthly_measurements_json = json.dumps(monthly_measurements, default=lambda o: o.__dict__, indent=2)
        print(monthly_measurements_json)

    def do_get_daily_measurements_json(self, input=None):
        """Get the daily electricity measurements of the on-going month of the on-going year as JSON"""

        previous_month_last_day_date, wanted_month_last_day_date = get_month_date_range_by_date(date.today())

        daily_measurements = self.api_client.get_daily_measurements_between_dates(previous_month_last_day_date, wanted_month_last_day_date)
        daily_measurements_json = json.dumps(daily_measurements, default=lambda o: o.__dict__, indent=2)
        print(daily_measurements_json)

    def do_get_contract_data_json(self, input=None):
        """Get the whole contract data as JSON"""

        contract_data_json = self.api_client.get_contract_data_json()
        contract_data_json_pretty = json.dumps(contract_data_json, default=lambda o: o.__dict__, indent=2)
        print(contract_data_json_pretty)

    def do_get_market_prices_json(self, input=None):
        """Get prices for the Market Price contract type as JSON"""

        price = self.helen_price_client.get_market_price_prices()
        price_json = json.dumps(price, default=_json_serializer, indent=2)
        print(price_json)

    def do_get_exchange_margin_price_json(self, input=None):
        """Get margin price for the Exchange Electricity contract type as JSON"""

        price = self.helen_price_client.get_exchange_prices()
        price_json = json.dumps(price, default=_json_serializer, indent=2)
        print(price_json)

    def do_get_contract_delivery_site_id(self, input=None):
        """Helper to get the delivery site id from your contract data. To see the whole contract data as JSON, use get_contract_data_json"""
        
        site_id = self.api_client.get_delivery_site_id()
        print(site_id)

    def do_get_contract_base_price(self, input=None):
        """Helper to get the contract base price from your contract data. To see the whole contract data as JSON, use get_contract_data_json"""
        
        base_price = self.api_client.get_contract_base_price()
        print(base_price)

    def do_get_contract_transfer_fee(self, input=None):
        """Helper to get the transfer fee price from your contract data. To see the whole contract data as JSON, use get_contract_data_json"""
        
        base_price = self.api_client.get_transfer_fee()
        print(base_price)

    def do_get_contract_transfer_base_price(self, input=None):
        """Helper to get the transfer base price from your contract data. To see the whole contract data as JSON, use get_contract_data_json"""
        
        base_price = self.api_client.get_transfer_base_price()
        print(base_price)

    def do_get_api_access_token(self, input=None):
        """Get your access token for the Oma Helen API."""
        
        access_token = self.api_client.get_api_access_token()
        print(access_token)

    def do_get_contract_energy_unit_price(self, input=None):
        """Helper to get the energy unit price from your contract data. To see the whole contract data as JSON, use get_contract_data_json"""

        contract_energy_unit_price = self.api_client.get_contract_energy_unit_price()
        print(contract_energy_unit_price)

def main():
    print("Log in to Oma Helen")
    username = input("Username: ")
    password = getpass()
    HelenCLIPrompt(username, password).cmdloop()


if __name__ == "__main__":
    main()
