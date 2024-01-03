import requests
from bs4 import BeautifulSoup

class Login():
    '''auカブコム証券にログインを行う'''

    def __init__(self, log, account_number, password):
        '''
        Args:
            log(Log): カスタムログ
            account_number(int): 口座番号
            password(str): パスワード

        '''
        self.log = log
        self.account_number = account_number
        self.password = password

    def login(self):
        '''
        auカブコム証券にログインを行う

        Return:
            session(requests.sessions.Session): ログインを行った状態のセッション情報

        '''
        session = requests.session()

        login_info = {
            'SsLogonUser': self.account_number,
            'SsLogonPassword': self.password,
            'CookieOn': '1',
            'SsLoginPage': '/members' # リダイレクト先
        }

        try:
            r = session.post('https://s10.kabu.co.jp/_mem_bin/Members/verifpwd.asp', data = login_info)
        except:
            self.log.error('接続に失敗')
            return False

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        if not '前回ログイン日時' in BeautifulSoup(r.content, 'html.parser').text:
            self.log.error('ログイン失敗')
            return False

        return session



