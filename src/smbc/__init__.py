from . import login
from . import get

class Smbc():
    def __init__(self, log, branch_code, account_number, password):
        self.login = login.Login(log, branch_code, account_number, password)
        self.get = get.Get(log)