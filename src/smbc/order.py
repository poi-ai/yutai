import config
import requests
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

    def confirm(self, session, stock_code, num, order_price):
        '''
        一般信用売り注文確認画面へリクエストを送る

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            stock_code(str): 対象銘柄
            num(int): 注文数量
            order_price(float or int): 注文価格 ※成行の場合はNone

        Returns:
            result(bool): 実行結果
            soup(bs4.BeautifulSoup): レスポンスのHTML

        '''

        # 共通注文条件
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
            #'cnd11': '2',                 # 寄り成り
            #'cnd12': '3',                 # 引け成り
            'yukokikan': '1',              # 1: 当日中、9: 期間指定
            'yukokigenDate': '',           # 注文有効期間
            'kozaKbnSinyo': '1',           # 0: 一般口座、1: 特定口座
            'kozaKyakKbn': '1',
            'execUrl.x': '99',             # 押下したボタンのx軸
            'execUrl.y': '18'              # 押下したボタンのy軸
        }

        # 取引時間外の成行注文の場合
        if order_price == None:
            post_info['nariSasiKbn'] =  '2'     # 1: 指値、2: 成行
            post_info['cnd17'] = '0'            # 条件なし成行

        # 取引時間中の指値の場合
        else:
            post_info['nariSasiKbn'] =  '1'     # 1: 指値、2: 成行
            post_info['kakaku'] = order_price   # 指値注文価格

        # タイムアウト時間を設定
        # 5時のメンテ明けの場合はセッションが切れるため、早めに接続アウトとする
        now = datetime.now()
        if now.hour == 5 and now.minute < 2:
            connect_timeout, read_time_out = 0.5, 1 # 接続タイムアウト0.5秒、HTML読み込みタイムアウトは1秒 TODO ここシビア。readは緩和するかも
        else:
            connect_timeout, read_time_out = 1, 2 # 接続タイムアウト1秒、HTML読み込みタイムアウトは2秒

        # User-agent指定
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        }

        try:
            r = session.post(url = 'https://trade.smbcnikko.co.jp/OdrMng/000000000000/sinyo/tku_odr/siji',
                             data = post_info,
                             headers = headers,
                             timeout = (connect_timeout, read_time_out))
        except requests.exceptions.ConnectTimeout as e:
            self.log.error(f'タイムアウトエラー\n{e}')
            return False, 1
        except Exception as e:
            self.log.error(f'接続に失敗\n{e}')
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

    def order(self, session, stock_code, num, token_id, url_id, order_date):
        '''
        一般信用売り注文リクエストを送る

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            stock_code(str): 対象銘柄
            num(int): 発注数量
            token_id(str): トークンID(注文確認画面で発行)
            url_id(str): URL ID(注文確認画面で発行)
            order_date(str): 注文日(yyyymmdd形式)

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
            'odrExecYmd': order_date,                  # 注文日
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

        # User-agent指定
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        }

        try:
            r = session.post(f'https://trade.smbcnikko.co.jp/OdrMng/{url_id}/sinyo/tku_odr/exec',
                             data = post_info,
                             headers = headers,
                             timeout = (10, 10)) # 接続タイムアウト10秒
        except requests.exceptions.ConnectTimeout as e:
            self.log.error(f'タイムアウトエラー\n{e}')
            return False, 1
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