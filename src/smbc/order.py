from bs4 import BeautifulSoup

class Order():
    '''SMBC日興証券で注文を行う'''

    def __init__(self, log):
        '''
        Args:
            log(Log): カスタムログ

        '''
        self.log = log

    def confirm(self, stock_code):
        '''確認画面へリクエストを送る'''
        pass

    def order(self, stock_code):
        '''注文を行う'''
        pass