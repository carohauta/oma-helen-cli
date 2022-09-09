# Oma Helen login CLI

A CLI that logs into [Oma Helen](https://www.helen.fi/kirjautuminen) and prints the `access-token` used to authenticate to the Oma Helen API. With the `access-token` you can e.g. query your personal electricity consumption and contract data from the Oma Helen API. Note that the token is valid for only one hour from the login.

Oma Helen is the user portal for a Finnish electricity company, Helen Oy.

### How to use and develop

Use virtual env to keep the project isolated. Developed using Python 3.9.9

1. In the root folder run `python -m venv .venv`
2. Activate the venv with `source .venv/bin/activate`
3. Install requirements `pip install -r requirements.txt`
4. Launch the CLI as a python module `python -m helenservice`
5. Enter your username and password as they are prompted
6. The CLI will print your `access-token` to the Oma Helen API
7. Use the token to query the API

Deactivate venv when not needed: `deactivate`

### Oma Helen API example

You need your delivery site id (`Consumption` or `Käyttöpaikka`) from Oma Helen. You can get it from the `Electricity` tab (or `Sähkö` -välilehti) - right next to your home address - from your Oma Helen.

#### Making a request

A curl example
```bash
curl -iv 'https://api.omahelen.fi/v7/measurements/electricity?begin=2021-12-31T22:00:00.000Z&end=2022-12-31T21:59:59.999Z&resolution=month&delivery_site_id=<YOUR-DELIVERY-SITE-HERE>&allow_transfer=true' -H 'User-Agent: Mozilla/5.0' -H 'Accept: application/json' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Authorization: Bearer <YOUR-ACCESS-TOKEN-HERE>' -H 'Origin: https://web.omahelen.fi' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-site' -H 'TE: trailers'
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
