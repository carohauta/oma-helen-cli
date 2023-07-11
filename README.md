# Oma Helen CLI

An interactive CLI that logs into [Oma Helen](https://www.helen.fi/kirjautuminen) and offers functions to get contract data or electricity measurement data in JSON format.

You can also retrieve your API `access-token` with the `get_access_token` function of the CLI in case you wish to make some other API calls that are not provided by the CLI tool (see the [Making a request](#making-a-request) example below). Note that the token is valid for only one hour from the login.

### What is Oma Helen?

Oma Helen is the user portal for a Finnish electricity company, Helen Oy.

### How to use and develop

Install from [pypi](https://pypi.org/project/oma-helen-cli/): 
```sh
pip install oma-helen-cli
```

#### Installing from sources and running the project

First clone this repo.

Use virtual env to keep the project isolated. Developed using Python 3.9.9

1. In the project root folder run `python -m venv .venv`
2. Activate the venv with `source .venv/bin/activate`
3. Install requirements `pip install -r requirements.txt`
4. Launch the CLI as a python module `python -m helenservice.cli`
5. Enter your username and password as they are prompted
6. Type `?` into the CLI prompt to see all available functions

Deactivate venv when not needed: `deactivate`

#### Available functions

| Function name                 | What it does |
|-------------------------------|--------------|
| get_api_access_token          | Get the access token to the Oma Helen API. With the token, you can make queries to your own contracts and data in Oma Helen |
| get_contract_base_price       | Get the monthly base price of your current electricity contract |
| get_contract_data_json        | Returns the whole contract data as JSON. Will return all active contracts you have with Helen |
| get_contract_delivery_site_id | Get the delivery site id from the contract data |
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

### Oma Helen API example

In this example, in addition to the `access-token`, you are going to need your delivery site id (`Consumption` or `Käyttöpaikka`) from Oma Helen. You can get it with the CLI tool's `get_contract_delivery_site_id` function.

#### Making a request

A curl example for making a request to get the energy consumption for the on-going year. **Note that the functionality of this example is already provided by the CLI tool itself**
```bash
curl -iv 'https://api.omahelen.fi/v7/measurements/electricity?begin=2021-12-31T22:00:00.000Z&end=2022-12-31T21:59:59.999Z&resolution=month&delivery_site_id=<YOUR-DELIVERY-SITE-ID>&allow_transfer=true' -H 'User-Agent: Mozilla/5.0' -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Authorization: Bearer <YOUR-ACCESS-TOKEN>' -H 'Origin: https://web.omahelen.fi' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-site' -H 'TE: trailers'
```

The response will look something like this
```json
{
    "intervals":
    {
        "electricity":
        [
            {
                "start": "2021-12-31T22:00:00+00:00",
                "stop": "2022-12-31T21:59:59+00:00",
                "resolution_s": null,
                "resolution": "month",
                "unit": "kWh",
                "measurements":
                [
                    {
                        "value": 954.11,
                        "status": "valid"
                    },
                    {
                        "value": 896.8380000000009,
                        "status": "valid"
                    },
                    {
                        "value": 842.1109999999994,
                        "status": "valid"
                    },
                    {
                        "value": 739.8199999999983,
                        "status": "valid"
                    },
                    {
                        "value": 710.8099999999996,
                        "status": "valid"
                    },
                    {
                        "value": 398.8100000000003,
                        "status": "valid"
                    },
                    {
                        "value": 231.7999999999997,
                        "status": "valid"
                    },
                    {
                        "value": 287.5999999999998,
                        "status": "valid"
                    },
                    {
                        "value": 290.88,
                        "status": "valid"
                    },
                    {
                        "value": 0.0,
                        "status": "invalid"
                    },
                    {
                        "value": 0.0,
                        "status": "invalid"
                    },
                    {
                        "value": 0.0,
                        "status": "invalid"
                    }
                ]
            }
        ]
    }
}
```
