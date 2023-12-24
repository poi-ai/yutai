import requests
from bs4 import BeautifulSoup

class Login():
    def __init__(self, account_number, password):
        self.account_number = account_number
        self.password = password

    def login(self):
        session = requests.session()

        login_info = {
            "SsLogonUser": self.account_number,
            "SsLogonPassword": self.password,
            "CookieOn": "1",
            "SsLoginPage": "/members",
            "submit1": "  ログイン  ",
            "MenuOption": "1",
            "SsLogonHost": "100",
        }
        # action
        url_login = "https://s10.kabu.co.jp/_mem_bin/Members/verifpwd.asp"
        r = session.post(url_login, data=login_info)
        soup = BeautifulSoup(r.content, 'html.parser')
        #print(soup.text)
        print(f'status_code : {r.status_code}')

        return session



