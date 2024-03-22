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
        '''メイン処理'''
        # 空売り監視/自動注文対象銘柄の取得
        result, steal_list = self.get_steal_list()
        if result == False:
            self.log.error(f'監視/自動注文対象銘柄CSVの取得に失敗\n{steal_list}')
            exit()

        # 時間チェック
        result = self.time_manage()
        if result == False:
            self.log.info('取引時間中なので監視/注文処理は行いません')
            exit()

        # SMBCへログイン
        self.log.info('SMBC日興証券ログイン開始')
        self.smbc_session = self.smbc.login.login()
        if self.smbc_session == False:
            return False
        self.log.info('SMBC日興証券ログイン終了')

        # 時間再チェック
        result = self.time_manage()
        if result == False:
            self.log.info('取引時間中なので監視/注文処理は行いません')
            exit()

        # 在庫チェック/注文処理
        while True:
            for target in steal_list:
                # 在庫チェック/注文発注
                self.order_exec(target)

    def order_exec(self, target):
        '''
        指定した銘柄の一般売在庫取得/売注文を行う

        Args:
            target(list[str, int, str]): 対象銘柄情報
                ※銘柄コード、発注数、備考

        Returns:
            result(bool): 実行結果

        '''
        stock_code = target[0]
        num = target[1]

        # 一般売注文確認画面へリクエストを送る
        result, html = self.smbc.order.confirm(target, num)
        if result == False:
            self.smbc_session = False

        # レスポンスチェック、在庫があれば正常の確認画面へ遷移するはず

        # TODO 注文パラメータおかしいよチェック

        # TODO 在庫足りんよチェック

        # TODO 余力足りんよチェック

        # TODO 注文リクエスト


    def time_manage(self):
        '''時間調整を行う'''
        # 時間取得
        now = datetime.now()

        # メンテナンス時間(2:00~4:59)なら5:00まで待つ
        if 2 <= now.hour <= 4:
            target_hour, target_minute = 5, 0

        # 大引け後注文中断時間(15:00~16:58)なら16:59まで待つ
        elif now.hour == 15 or (now.hour == 16 and now.minute < 59):
            target_hour, target_minute = 15, 59

        # 16:59なら17:00まで待つ
        elif now.hour == 16 and now.minute == 59:
            target_time = datetime(now.year, now.month, now.day, 17, 00)

        # 注文中断時間(20:15~20:18)なら20:19まで待つ
        elif now.hour == 20 and (15 <= now.minute < 19):
            target_time = datetime(now.year, now.month, now.day, 20, 19)

        # 20:19なら20:20まで待つ
        elif now.hour == 20 and now.minute == 19:
            target_time = datetime(now.year, now.month, now.day, 20, 20)

        # ザラ場中(昼休み含む)なら(一旦)処理を行わない
        elif 9 <= now.hour <= 15:
            return False

        target_time = datetime(now.year, now.month, now.day, target_hour, target_minute)
        time.sleep((target_time - self.ntp()).total_seconds() * 1e6 / 1e6)

        return True

    def get_steal_list(self):
        '''
        一般売対象銘柄のリストをCSVから取得する]

        Returns:
            result(bool): 実行結果
            steal_list(list) or error_message: 対象銘柄リスト or エラーメッセージ

        '''
        steal_list = []

        try:
            with open('steal_list.csv', 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    steal_list.append(row)

            self.steal_list = steal_list
        except Exception as e:
            return False, e

        return True, steal_list

if __name__ == '__main__':
    s = Steal()
    s.main()