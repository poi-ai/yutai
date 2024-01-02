from . import login
from . import get

class Smbc():
    def __init__(self, branch_code, account_number, password):
        self.login = login.Login(branch_code, account_number, password)
        self.get = get.Get()