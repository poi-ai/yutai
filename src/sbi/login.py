import requests
from bs4 import BeautifulSoup

class Login():
    '''SBI証券にログインを行う'''

    def __init__(self, log, user_name, password):
        '''
        Args:
            log(Log): カスタムログ
            user_name(str): 口座番号
            password(str): パスワード

        '''
        self.log = log
        self.use_name = user_name
        self.password = password

    def login(self):
        '''
        SBI証券にログインを行う

        Return:
            session(requests.sessions.Session): ログインを行った状態のセッション情報

        '''
        session = requests.session()

        login_info = {
            'JS_FLG': '0',
            'BW_FLG': '0',
            '_ControlID': 'WPLETlgR001Control',
            '_DataStoreID': 'DSWPLETlgR001Control',
            '_PageID': 'WPLETlgR001Rlgn20',
            '_ActionID': 'login',
            'getFlg': 'on',
            'allPrmFlg': 'on',
            '_ReturnPageInfo': 'WPLEThmR001Control/DefaultPID/DefaultAID/DSWPLEThmR001Control',
            'user_id': self.use_name,
            'user_password': self.password,
            'ACT_login': 'ログイン'
        }

        try:
            r = session.post('https://site1.sbisec.co.jp/ETGate/', data = login_info)
        except:
            self.log.error('接続に失敗')
            return False

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        soup = BeautifulSoup(r.content, 'lxml')

        if 'https://search.sbisec.co.jp/attention/maintenance.html' in str(soup):
            self.log.error('メンテナンス中')
            return False

        return session



