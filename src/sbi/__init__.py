from . import login
#from . import get

class Sbi():
    def __init__(self, log, user_name, password):
        self.login = login.Login(log, user_name, password)
        #self.get = get.Get(log)