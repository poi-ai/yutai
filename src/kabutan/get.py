import re
import requests
from bs4 import BeautifulSoup

class Get():
    '''株探から株価データを取得する'''

    def __init__(self, log):
        self.log = log

    def get_closing_price(self, stock_code):
        '''
        終値を取得する

        Args:
            stock_code(str): 証券コード

        Returns:
            result(bool): 実行結果
            closing_price(list[str, str]): 終値データ[終値, 日付]
                ※エラー時はエラーメッセージ

        '''
        try:
            r = requests.get(f'https://kabutan.jp/stock/?code={stock_code}')
            soup = BeautifulSoup(r.content, 'lxml')

            owarine_text = soup.find('dd', class_='floatr').text
            owarine_info = re.sub(r'[,\(\)]', '', owarine_text).split('\xa0')
        except Exception as e:
            return False, e

        return True, owarine_info