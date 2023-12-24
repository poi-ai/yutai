from . import login

class Kabucom():
    def __init__(self, account_number, password):
        self.login = login.Login(account_number, password)