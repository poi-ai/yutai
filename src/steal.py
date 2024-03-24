import csv
import time
import re
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


        # 在庫チェック/注文処理
        #while True:

        # 除外銘柄管理用のリスト作成
        tmp_list = steal_list

        # 時間再チェック
        result = self.time_manage()
        if result == False:
            self.log.info('取引時間中なので監視/注文処理は行いません')
            exit()

        for target in steal_list:
            # セッションが切れている場合は再ログイン
            if self.smbc_session == False:
                self.log.info('SMBC日興証券再ログイン開始')
                self.smbc_session = self.smbc.login.login()
                if self.smbc_session == False:
                    return False
                self.log.info('SMBC日興証券再ログイン終了')

            # 在庫チェック/注文発注
            self.log.info(f'在庫チェック/注文を行います 証券コード: {target[0]}, 株数: {target[1]}')
            result = self.order_exec(target)
            self.log.info(f'在庫チェック/注文処理終了 証券コード: {target[0]}, 株数: {target[1]}')

            # 結果チェック
            # 続行不可能なエラー
            if result == 'mistake password':
                self.log.error('パスワードが誤っているため処理を終了します')
                exit()

            # 再ログインした方がいいエラー(接続エラー/不明なエラー)
            elif result == 'confirm connect' or 'order connect' or 'confirm unknown' or 'order unknown':
                self.smbc_session == False

            # チェックした銘柄を監視対象から外す(余力不足/非取扱銘柄/注文成功)
            elif result == 'lacking money' or 'not handle' or 'success':

                # 処理対象リストから外す
                tmp_list = [sublist for sublist in tmp_list if sublist[0] != 20]


            # TODO メンテナンス中の処遇

            if self.limiter:
                time.sleep(2)

        # 除外した銘柄情報をメインリストに反映
        steal_list = tmp_list

    def order_exec(self, target):
        '''
        指定した銘柄の一般売在庫取得/売注文を行う

        Args:
            target(list[str, int, str]): 対象銘柄情報
                ※銘柄コード、発注数、備考

        Returns:
            error_reason(str): 処理失敗原因

        '''
        stock_code = target[0]
        num = target[1]

        # 一般売注文確認画面へリクエストを送る
        result, soup = self.smbc.order.confirm(self.smbc_session, stock_code, num)
        if result == False:
            return 'confirm connect'

        # メンテナンスチェック
        # 時間制御しているから定期メンテではここは引っかからない
        if 'NOL11001E' in soup.text:
            self.log.warning('メンテナンス中のため注文できません')
            return 'maintenance'

        # 取扱チェック
        if 'NOL51305E' in soup.text:
            self.log.warning('一般信用非取扱銘柄のため注文できません')
            return 'not handle'

        # 余力チェック
        if 'NOL51015E' in soup.text:
            self.log.warning('余力が足りないため注文できません')
            return 'lacking money'

        # 在庫チェック
        if 'NOL75401E' or 'NOL75400E' in soup.text:
            self.log.info('一般信用在庫が足りないため注文できません')
            return 'lacking stock'

        # 注文用のトークンID/URLIDの取得
        try:
            token_id = soup.find('input', {'name': 'tokenId'}).get('value')
            url_match = re.search(r'OdrMng/(.+)/sinyo/tku_odr/exec', str(soup))
            url_id = url_match.groups()[0]
        except Exception as e:
            #print(soup)
            self.log.error(f'不明なエラーです\n{e}')
            return 'confirm unknown'

        # 注文リクエストを送る
        result, soup = self.smbc.order.order(self.smbc_session, stock_code, num, token_id, url_id)
        if result == False:
            return 'order connect'

        # パスワードチェック
        if 'NOL76511E' in soup.text:
            self.log.error('パスワードが正しくありません')
            return 'mistake password'

        # 注文完了チェック
        if not '売り注文を受付ました' in soup.text:
            self.log.error('不明なエラーです')
            return 'order unknown'

        self.log.info(f'注文が完了しました 証券コード: {stock_code}')

        return 'success'


    def time_manage(self):
        '''時間調整を行う'''
        # 時間取得
        now = datetime.now()

        ## 全日共通時間判定

        # メンテナンス時間(2:00~4:59)なら5:00まで待つ
        if 2 <= now.hour <= 4:
            target_hour, target_minute = 5, 0

        ## 営業日の時間判定
        if now.weekday == 5 or 6:
            return True

        # 大引け後注文中断時間(15:00~16:58)なら16:59まで待つ
        if now.hour == 15 or (now.hour == 16 and now.minute < 59):
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
            with open('steal_list.csv', 'r', newline = '', encoding = 'UTF-8') as csvfile:
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