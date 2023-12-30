import requests
from bs4 import BeautifulSoup

class Login():
    '''auカブコム証券にログインを行う'''

    def __init__(self, account_number, password):
        '''
        Args:
            account_number(int): 口座番号
            password(str): パスワード

        '''
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
            print('接続に失敗')
            return False

        if r.status_code != 200:
            print(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        if '前回ログイン日時' in BeautifulSoup(r.content, 'html.parser').text:
            print('ログイン成功')
        else:
            print('ログイン失敗')
            return False

        return session



