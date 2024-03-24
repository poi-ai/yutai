import config
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

class Order():
    '''SMBC日興証券で注文を行う'''

    def __init__(self, log):
        '''
        Args:
            log(Log): カスタムログ

        '''
        self.log = log

    def confirm(self, session, stock_code, num):
        '''
        一般信用売り注文確認画面へリクエストを送る

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            stock_code(str): 対象銘柄
            num(int): 発注数量

        Returns:
            result(bool): 実行結果
            soup(bs4.BeautifulSoup): レスポンスのHTML

        '''
        post_info = {
            'odrJoken': '1',               # 1: 通常注文、2: 逆指値注文
            'execCnd': '0',
            'ippanSinyoTriKanoFlg': '1',
            'kakunin': '1',
            #'odrExecYmd': '',
            'dispChk': '0',
            #'honjituIjiRitu': '100.00',   # 維持率(%)
            #'shintategaku': '1,000,000',  # 信用建可能額
            'specifyMeig': '',
            'meigCd': stock_code,          # 証券コード
            'sinkbShitei': '0',
            'sijyoKbn': '1',
            'sinyoToriKbn': '1',           # 0: 制度、1: 信用
            'suryo': num,                  # 株数
            #'kakaku': '',                 # 指値注文価格
            'nariSasiKbn': '2',            # 1: 指値、2: 成行
            #'cnd11': '2',                 # 寄り成り
            #'cnd12': '3',                 # 引け成り
            'cnd17': '0',                  # 条件なし成行
            'yukokikan': '1',              # 1: 当日中、9: 期間指定
            'yukokigenDate': '',           # 注文有効期間
            'kozaKbnSinyo': '1',           # 0: 一般口座、1: 特定口座
            'kozaKyakKbn': '1',
            'execUrl.x': '99',             # 押下したボタンのx軸
            'execUrl.y': '18'              # 押下したボタンのy軸
        }

        try:
            r = session.post('https://trade.smbcnikko.co.jp/OdrMng/000000000000/sinyo/tku_odr/siji', data = post_info)
        except:
            self.log.error('接続に失敗')
            return False, None

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False, None

        soup = BeautifulSoup(r.content, 'lxml')

        # セッション切れエラー
        if 'NOL11007E' in soup.text:
            self.log.error('セッション切れエラー')
            return False, None

        return True, soup

    def order(self, session, stock_code, num, token_id, url_id):
        '''
        一般信用売り注文リクエストを送る

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            stock_code(str): 対象銘柄
            num(int): 発注数量
            token_id(str): トークンID(注文確認画面で発行)
            url_id(str): URL ID(注文確認画面で発行)

        Returns:
            result(bool): 実行結果
            soup(bs4.BeautifulSoup): レスポンスのHTML

        '''
        post_info = {
            'specifyMeig': '1',
            'sinkbShitei': '0',
            'meigCd': stock_code,                      # 証券コード
            'bbaiKbn': '1',
            'sijyoKbn': '1',
            'execCnd': '0',
            'nariSasiKbn': '2',
            'kakaku': '',
            'suryo': num,
            'odrExecYmd': self.next_weekday(),         # 注文日
            'expcheck': '0',
            'yukoSiteDate': '1',
            'yukokigenDate': '',                       # 注文有効期間
            'nyuKeroKbn': '',
            'execCndKbn': '',
            'kanriKesaiKbn': '',
            'jreit': '',
            'etf': '',
            'kozaKbnSinyo': '1',                       # 0: 一般口座、1: 特定口座
            'kozaKyakKbn': '1',
            'tokenId': token_id,                       # 注文確認画面で取得したトークンID
            'toriPasswd': config.SMBC_TRADE_PASSWORD,  # 取引パスワード
            'funcId': '01',
            'x': '0',
            'y': '0',
            'shintategaku': '1,000,000',
            'odrJoken': '1',                           # 1: 通常注文、2: 逆指値注文
            'cnd11': '',
            'cnd12': '',
            'cnd13': '',
            'cnd14': '',
            'cnd15': '',
            'cnd16': '',
            'cnd17': 'checked',
            'dosokuKehai': '',
            'oya': '',
            'sinyoToriKbn': '1',                       # 0: 制度、1: 信用
            'ippanSinyoTriKanoFlg': '1',
            'trgKbn': '',
            'trgKBkakaku': '',
            'trgKbnHZ': '',
            'trgKbnPM': '',
            'trgHZkakaku': '',
            'trgKbnJouge': '',
            'nyuKeroKbn2': 'pcw00'
        }

        try:
            r = session.post(f'https://trade.smbcnikko.co.jp/OdrMng/{url_id}/sinyo/tku_odr/exec', data = post_info)
        except:
            self.log.error('接続に失敗')
            return False, None

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False, None

        soup = BeautifulSoup(r.content, 'lxml')

        # セッション切れエラー
        if 'NOL11007E' in soup.text:
            self.log.error('セッション切れエラー')
            return False, None

        return True, soup

    def next_weekday(self):
        '''
        次の営業日を返す(祝日非対応)

        Returns:
            date(str): 次の営業日(yyyymmdd)

        '''
        now = datetime.now()
        # 土曜
        if now.weekday == 4:
            next_weekday = now + timedelta(days = 3)
        # 金曜
        elif now.weekday == 5:
            next_weekday = now + timedelta(days = 2)
        # 平日/日曜
        else:
            next_weekday = now + timedelta(days = 1)

        return next_weekday.strftime("%Y%m%d")