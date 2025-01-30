import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

class Get():
    '''株探から株価データを取得する'''

    def __init__(self, log):
        self.log = log

    def get_closing_price(self, stock_code, time_type):
        '''
        終値を取得する

        Args:
            stock_code(str): 証券コード
            time_type(int): 取得対象時間帯

        Returns:
            result(bool): 実行結果
            closing_price(list[str, str]): 終値データ[終値, 日付]
                ※エラー時はエラーメッセージ

        '''
        try:
            r = requests.get(f'https://kabutan.jp/stock/?code={stock_code}')
            soup = BeautifulSoup(r.content, 'lxml')

            owarine_info = ''

            # 営業日のザラ場時間中の場合は、前営業日の終値欄から取得
            if time_type in [1, 2, 4, 6]:
                owarine_text = soup.find('dd', class_='floatr').text
                owarine_info = re.sub(r'[,\(\)]', '', owarine_text).split('\xa0')
            # その他は四本値の終値欄から取得
            else:
                # テーブルをいったん全部取得
                owarine_table = soup.find_all('table')
                owarine = -1
                for table in owarine_table:
                    # 終値の記載チェック
                    if '終値' in table.text:
                        owarine = table.find_all('tr')[3].find_all('td')[1].text
                        break

                now = datetime.now()
                # 記載されている終値がいつのものかを現在の時間から判定
                # 非営業日か大引け後は今日の日付を設定(値幅計算対象が翌営業日になる)
                if time_type in [0, 5]:
                    owarine_info = [owarine, now.strftime('%Y/%m/%d')]
                # 営業日の寄り付き前は前日の日付を設定(値幅計算対象が今日になる)
                else:
                    owarine_info = [owarine, (now - timedelta(days = 1).strftime('%Y/%m/%d'))]
        except Exception as e:
            return False, e

        return True, owarine_info