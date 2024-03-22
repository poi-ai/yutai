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
            session(): ログイン状態のセッション
            stock_code(str): 対象銘柄
            num(int): 発注数量

        Returns:
            result(bool): 実行結果
            soup(bs4.BeautifulSoup): レスポンスのHTML

        '''
        post_info = {
            'odrJoken': '1',
            'execCnd': '0',
            'ippanSinyoTriKanoFlg': '1',
            'kakunin': '1',
            'odrExecYmd': '',
            'dispChk': '0',
            'honjituIjiRitu': '--.--',
            'shintategaku': '1,000,000',
            'specifyMeig': '1',
            'meigCd': stock_code, # 証券コード
            'sinkbShitei': '0',
            'sijyoKbn': '1',
            'sinyoToriKbn': '1',
            'suryo': num,
            'kakaku': '',
            'nariSasiKbn': '2',
            'cnd17': '0',
            'yukokikan': '1',
            'yukokigenDate': '',
            'kozaKbnSinyo': '1',
            'kozaKyakKbn': '1',
            'execUrl.x': '0',
            'execUrl.y': '0'
        }

        try:
            r = session.post('https://trade.smbcnikko.co.jp/OdrMng/21ABM0679964/sinyo/tku_odr/siji', json = post_info)
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

    def order(self, session, stock_code):
        '''注文を行う'''
        pass