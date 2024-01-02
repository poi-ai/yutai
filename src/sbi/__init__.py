from . import login
#from . import get

class Sbi():
    def __init__(self, user_name, password):
        self.login = login.Login(user_name, password)
        #self.get = get.Get()