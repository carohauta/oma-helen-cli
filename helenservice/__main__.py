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

    json_response = api_client.get_contract_data()

    print(json_response)


if __name__ == "__main__":
    main()
