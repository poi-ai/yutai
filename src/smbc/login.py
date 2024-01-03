import requests
from bs4 import BeautifulSoup

class Login():
    '''SMBC日興証券にログインを行う'''

    def __init__(self, log, branch_code, account_number, password):
        '''
        Args:
            log(Log): カスタムログ
            branch_code(int): 支店コード
            account_number(int): 口座番号
            password(str): パスワード

        '''
        self.log = log
        self.branch_code = branch_code
        self.account_number = account_number
        self.password = password

    def login(self):
        '''
        SMBC日興証券にログインを行う

        Return:
            session(requests.sessions.Session): ログインを行った状態のセッション情報

        '''
        session = requests.session()

        login_info = {
            "koza1": self.branch_code,
            "koza2": self.account_number,
            "passwd": self.password,
            "syokiGamen": "0",
            "logIn": "ログイン",
        }

        try:
            r = session.post('https://trade.smbcnikko.co.jp/Login/0/login/ipan_web/exec', data = login_info)
        except:
            self.log.error('接続に失敗')
            return False

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        soup = BeautifulSoup(r.content, 'lxml').text

        # 支店コード・口座番号・パスワードのどれかが違う
        if 'NOL11003E' in soup:
            self.log.error('ログイン認証エラー')
            return False

        if '前回ログイン' not in soup:
            self.log.error('ログインエラー')
            return False

        return session



