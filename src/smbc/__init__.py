from . import login
from . import get
from . import order

class Smbc():
    def __init__(self, log, branch_code, account_number, password):
        self.login = login.Login(log, branch_code, account_number, password)
        self.get = get.Get(log)
        self.order = order.Order(log)