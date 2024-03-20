import re
import time
from main import Main
from datetime import datetime, timedelta

class Check(Main):
    '''在庫の復活タイミングをチェックするための処理'''
    def __init__(self):
        super().__init__()
        self.kabucom_session = False
        self.smbc_session = False
        self.kabucom_error_count = 0
        self.smbc_error_count = 0

    def main(self, stock_code):

        self.log.info('カブコム/SMBC在庫補充処理チェック処理開始')
        # 在庫残を取得する
        while True:
            # 現在時刻の取得/判定
            now = datetime.now()
            # if now.hour == 11 and now.minute >= 57:
            if now.hour == 8:
                self.log.info('カブコム/SMBC在庫補充処理チェック処理終了')
                exit()

            # ログイン/セッション取得
            if self.kabucom_session == False and self.kabucom_error_count < 3:
                self.kabucom_login()
                if self.kabucom_session == False:
                    self.kabucom_error_count += 1.0

            if self.smbc_session == False and self.smbc_error_count < 3 and not self.smbc_maintenance(now):
                self.smbc_login()
                if self.smbc_session == False:
                    self.smbc_error_count += 1.0

            # 次の0秒まで待つ
            time_difference = (now + timedelta(minutes = 1)).replace(second = 0, microsecond = 0) - now
            time.sleep((time_difference.total_seconds() * 10**6) / 10**6)

            # SMBCから一般信用残の取得
            if self.smbc_session != False and self.smbc_error_count < 3 and not self.smbc_maintenance(now):
                soup = self.smbc.get.order_input(self.smbc_session, stock_code)
                # 成功チェック
                if soup == False:
                    self.smbc_session = False
                    self.smbc_error_count += 1.0
                    if self.smbc_error_count >= 3:
                        self.log.info('SMBCエラーカウント超過のため終了します')
                else:
                    try:
                        stock_num_html = soup.find('td', id='iurikanosu').text
                        stock_num = re.sub(r'[株, ]|\r|\n', '', stock_num_html)
                        self.log.info(f'SMBC/({stock_code})在庫数: {stock_num}')
                        self.smbc_error_count -= 0.1
                    except Exception as e:
                        self.log.error('SMBC/在庫数HTML切り出し処理でエラー')
                        self.smbc_session = False
                        self.smbc_error_count += 1.0
                        if self.smbc_error_count >= 3:
                            self.log.info('SMBCエラーカウント超過のため終了します')

            # カブコムから一般信用残の取得
            if self.kabucom_session != False and self.kabucom_error_count < 3:
                soup = self.kabucom.get.order_input(self.kabucom_session, stock_code)
                # 成功チェック
                if soup == False:
                    self.kabucom_session == False
                    self.kabucom_error_count += 1.0
                    if self.kabucom_error_count >= 3:
                        self.log.info('カブコムエラーカウント超過のため終了します')
                else:
                    try:
                        table_max, table_soup = 2000, ''
                        for table in soup.find_all('table'):
                            if '一般信用売建可能数量(在庫株数量)' in table.text:
                                if table_max > len(str(table)):
                                    table_max = len(str(table))
                                    table_soup = table
                        self.log.info(f'カブコム/({stock_code})在庫数: {table_soup.find_all("td")[2].text}')
                        self.kabucom_error_count -= 0.1
                    except Exception as e:
                        self.log.error('カブコム/在庫数HTML切り出し処理でエラー')
                        self.kabucom_session == False
                        self.kabucom_error_count += 1.0
                        if self.kabucom_error_count >= 3:
                            self.log.info('カブコムエラーカウント超過のため終了します')

    def kabucom_login(self):
        self.log.info('auカブコム証券ログイン開始')
        self.kabucom_session = self.kabucom.login.login()
        if self.kabucom_session == False:
            return False
        self.log.info('auカブコム証券ログイン終了')

    def smbc_login(self):
        self.log.info('SMBC日興証券ログイン開始')
        self.smbc_session = self.smbc.login.login()
        if self.smbc_session == False:
            return False
        self.log.info('SMBC日興証券ログイン終了')

    def smbc_maintenance(self, now):
        if now.hour >= 2 and now.hour < 5:
            return True
        return False

if __name__ == '__main__':
    target_stock_code = 2730
    c = Check()
    c.main(str(target_stock_code))