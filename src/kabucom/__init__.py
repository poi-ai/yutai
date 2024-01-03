from . import login
from . import get

class Kabucom():
    def __init__(self, log, account_number, password):
        self.login = login.Login(log, account_number, password)
        self.get = get.Get(log)