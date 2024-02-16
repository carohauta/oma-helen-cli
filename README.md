# Oma Helen CLI

An interactive CLI that logs into [Oma Helen](https://www.helen.fi/kirjautuminen) and offers functions to get contract data or electricity measurement data in JSON format.

You can also retrieve your API `access-token` with the `get_access_token` function of the CLI in case you wish to make some other API calls that are not provided by the CLI tool (see the [Making a request](#making-a-request) example below). Note that the token is valid for only one hour from the login.

### What is Oma Helen?

Oma Helen is the user portal for a Finnish electricity company, Helen Oy.

### How to install and use

Install from [pypi](https://pypi.org/project/oma-helen-cli/) and run: 
```sh
pip install oma-helen-cli
oma-helen-cli
```

Then just enter you Oma Helen credentials and start entering commands. 

Tip: in order to list all the commands within the CLI, enter `?`

### Available functions

| Function name                 | What it does |
|-------------------------------|--------------|
| get_api_access_token          | Get the access token to the Oma Helen API. With the token, you can make queries to your own contracts and data in Oma Helen |
| get_contract_base_price       | Get the monthly base price of your current electricity contract |
| get_contract_data_json        | Returns the whole contract data as JSON. Will return all active contracts you have with Helen |
| get_daily_measurements_json   | Returns your daily energy consumption for the on-going month of the on-going year as JSON |
| get_market_prices_json        | Returns the prices for the Market Price Electricity contract as JSON. The JSON includes the price for last month, the current month and next month if available |
| get_monthly_measurements_json | Returns your monthly energy consumption for the on-going year as JSON |
| calculate_the_impact_of_usage_between_dates | Calculates your impact of usage (in c/kwh) between given dates for the Helen Smart Electricity Guarantee |
| calculate_spot_cost_between_dates | Calculates the total costs (eur) between given dates of a spot price contract in an hourly precision |
| get_exchange_margin_price_json | Get the margin price of the Exchange Electricity contract |
| get_contract_energy_unit_price | Get the energy unit price (c/kwh) from your contract data. Note that this only works for fixed price contracts. For spot electricity contract, this returns 0.0 |
| get_contract_transfer_fee      | Get the transfer fees (c/kwh) from your contract. Note that if Helen is not your transfer company, this returns 0.0 |
| calculate_transfer_fees_between_dates | Calculates total transfer fees (eur) based on your consumption between dates |
| get_contract_transfer_base_price | Get the monthly transfer base price (eur) from your contract. Note that if Helen is not your transfer company, this returns 0.0 |
| get_all_delivery_sites | Get all delivery sites across your active contracts |
| select_delivery_site | Selects a delivery site by id for the CLI to use. Useful if you have multiple contracts with Helen. Use `get_all_delivery_sites` to find out all your delivery sites. After selecting a delivery site, all measurements and other requested data will be about the selected delivery site. |

### Installing from sources and running the project for local development

First clone this repo.

Use virtual env to keep the project isolated. Developed using Python 3.9.9

1. In the project root folder run `python -m venv .venv`
2. Activate the venv with `source .venv/bin/activate`
3. Install requirements `pip install -r requirements.txt`
4. Launch the CLI as a python module `python -m helenservice.cli`
5. Enter your username and password as they are prompted
6. Type `?` into the CLI prompt to see all available functions

Deactivate venv when not needed: `deactivate`
