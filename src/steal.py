import csv
import time
from main import Main
from datetime import datetime

# ころしてでもうばいとる
class Steal(Main):
    '''SMBC日興証券の空売り注文を入れる'''
    def __init__(self):
        super().__init__()
        self.smbc_session = False
        self.limiter = True

    def main(self):
        # 自動発注対象銘柄の取得
        target_list = []
        try:
            with open('steal_list.csv', 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)

                for row in reader:
                    target_list.append(row)
        except Exception as e:
            self.log.error(f'監視/自動注文対象銘柄CSVの取得に失敗\n{e}')
            exit()

        # 時間チェック
        now = datetime.now()
        # メンテナンス時間(2:00~4:59)なら5:00まで待つ
        if 2 <= now.hour <= 4:
            target_hour, target_minute = 5, 0
        # 大引け~注文再開(15:00~16:58)なら16:59まで待つ
        elif now.hour == 15 or (now.hour == 16 and now.minute < 59):
            target_hour, target_minute = 15, 59

        target_time = datetime(now.year, now.month, now.day, target_hour, target_minute)
        time.sleep((target_time - self.ntp()).total_seconds() * 1e6 / 1e6)

        # SMBCへログイン
        self.log.info('SMBC日興証券ログイン開始')
        self.smbc_session = self.smbc.login.login()
        if self.smbc_session == False:
            return False
        self.log.info('SMBC日興証券ログイン終了')

        # 時間再チェック
        now = datetime.now()
        # 16:59なら17:00まで待つ
        if now.hour == 16 and now.minute < 59:
            target_time = datetime(now.year, now.month, now.day, 17, 00)
            time.sleep((target_time - self.ntp()).total_seconds() * 1e6 / 1e6)
            self.limiter = False

        # 在庫チェック/注文処理
        while True:
            for target in target_list:
                # 在庫チェック
                pass


if __name__ == '__main__':
    s = Steal()
    s.main()