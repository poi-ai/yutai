from . import login
from . import get

class Kabucom():
    def __init__(self, account_number, password):
        self.login = login.Login(account_number, password)
        self.get = get.Get()