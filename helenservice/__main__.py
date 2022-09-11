from datetime import date

from helenservice.client.api_client import HelenApiClient
from .client.helen_session import HelenSession
from getpass import getpass


def main():
    print("Log in to Oma Helen")
    username = input("Username: ")
    password = getpass()

    api_client = HelenApiClient()

    api_client.login(username, password)

    monthly_measurements = api_client.get_monthly_measurements()

    print(monthly_measurements)


if __name__ == "__main__":
    main()
