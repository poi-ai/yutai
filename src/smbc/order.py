from bs4 import BeautifulSoup

class Order():
    '''SMBC日興証券で注文を行う'''

    def __init__(self, log):
        '''
        Args:
            log(Log): カスタムログ

        '''
        self.log = log

    def confirm(self, session, stock_code):
        '''確認画面へリクエストを送る'''
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
            'suryo': '100',
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

    def order(self, session, stock_code):
        '''注文を行う'''
        pass