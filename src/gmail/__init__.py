from . import auth
from . import mail

class Gmail():
    '''Gmail APIの操作を行うクラス'''
    def __init__(self, log):
        self.token = auth.Auth(log)
        self.mail = mail.Mail(log, self.token)