from .client.helen_session import HelenSession
from getpass import getpass


def main():
    print("Log in to Oma Helen")
    username = input("Username: ")
    password = getpass()

    helen_session = HelenSession()
    helen_session.login(username, password)

    print(helen_session.get_access_token())
    
    helen_session.close()

if __name__ == "__main__":
    main()
