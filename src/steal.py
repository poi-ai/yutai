import config
import csv
import ntplib
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
            return False

        # 時間チェック
        result = self.time_manage()
        if result == False:
            return False

        # SMBCへログイン
        self.log.info('SMBC日興証券ログイン開始')
        self.smbc_session = self.smbc.login.login()
        self.log.info('SMBC日興証券ログイン終了')
        # 処理失敗
        if self.smbc_session == False:
            # 5:00ジャストの場合のみ5:01までログインを試す
            while self.smbc_session == False:
                now = datetime.now()
                if now.hour == 5 and now.minute == 0:
                    time.sleep(1)
                    self.log.info('SMBC日興証券再ログイン開始')
                    self.smbc_session = self.smbc.login.login()
                    self.log.info('SMBC日興証券再ログイン終了')
                else:
                    break
            # ログインできなかったら処理終了
            if self.smbc_session == False:
                return False


        # 在庫チェック/注文処理
        while True:
            # 監視/注文対象の銘柄がない場合は終了
            if len(steal_list) == 0: return True

            # 除外銘柄管理用の一時リスト作成
            tmp_list = steal_list

            # 時間再チェック
            result = self.time_manage()
            if result == False:
                return False

            # リミッター制御用カウンター
            counter = 0

            for target in steal_list:
                counter += 1
                # セッションが切れている場合は再ログイン
                if self.smbc_session == False:
                    self.log.info('SMBC日興証券再ログイン開始')
                    self.smbc_session = self.smbc.login.login()
                    self.log.info('SMBC日興証券再ログイン終了')
                    if self.smbc_session == False:
                        return False

                # 在庫チェック/注文発注
                self.log.info(f'在庫チェック/注文を行います 証券コード: {target[0]}, 株数: {target[1]}')
                result = self.order_exec(target)
                self.log.info(f'在庫チェック/注文処理終了 証券コード: {target[0]}, 株数: {target[1]}')

                # 結果チェック
                # 続行不可能なエラー(パスワード誤り)
                if result == -1:
                    self.log.error('パスワードが誤っているため処理を終了します')
                    return False

                # チェックした銘柄を監視対象から外す(余力不足/非取扱銘柄/注文成功)
                elif result == 1:
                    # 処理対象リストから外す
                    tmp_list = [sublist for sublist in tmp_list if sublist[0] != target[0]]

                # 再ログイン(セッション取得)した方がいいエラー(接続エラー/不明なエラー)
                elif result == 2:
                    self.smbc_session = False

                    # 最大3回セッションを取り直す
                    for _ in range(3):
                        self.log.info('SMBC日興証券再ログイン開始')
                        self.smbc_session = self.smbc.login.login()
                        self.log.info('SMBC日興証券再ログイン終了')
                        if self.smbc_session != False:
                            break

                    if self.smbc_session == False:
                        self.log.error('セッション取得に3度失敗したため処理を終了します')
                        return False

                    # TODO 不明なエラーが続いた場合の処理も必要

                # 時間調整が必要なエラー(メンテナンス時間中エラー)
                elif result == 3:
                    now = datetime.now()
                    # メンテナンス/取引再開直後の場合は再チェックする
                    if (now.hour in [5, 17] and now.minute <= 1) or (now.hour == 20 and 20 <= now.minute <= 21):
                        now = datetime.now()
                        # メンテ時間か不明なエラー(混雑)以外の表示が出るまでループチェック
                        while (now.hour in [5, 17] and now.minute <= 1) or (now.hour == 20 and 20 <= now.minute <= 21):
                            time.sleep(0.5)
                            self.log.info(f'在庫チェック/注文を行います 証券コード: {target[0]}, 株数: {target[1]}')
                            result = self.order_exec(target)
                            self.log.info(f'在庫チェック/注文処理終了 証券コード: {target[0]}, 株数: {target[1]}')
                            time.sleep(0.5)
                            # ログイン情報関係のエラーならログインしなおし
                            if result == 2:
                                self.log.info('SMBC日興証券再ログイン開始')
                                self.smbc_session = self.smbc.login.login()
                                self.log.info('SMBC日興証券再ログイン終了')
                            # エラーが出なくなったらループ終了
                            if result != 2 and result != 3:
                                # 最低限の対処として注文成功時に複数回注文されないようにはしておく
                                if result == 1:
                                    tmp_list = [sublist for sublist in tmp_list if sublist[0] != target[0]]
                                break

                if self.limiter:
                    time.sleep(3)

                # 2周以上した場合はリミッターをかける
                elif counter >= 2:
                    self.limiter = True

            # 除外した銘柄情報をメインリストに反映
            steal_list = tmp_list

    def order_exec(self, target):
        '''
        指定した銘柄の一般売在庫取得/売注文を行う

        Args:
            target(list[str, int, str]): 対象銘柄情報
                ※銘柄コード、発注数、備考

        Returns:
            error_type(str): エラータイプ
                -1: 続行不可能なエラー、1: 監視対象から外すことが必要なエラー/注文成功
                2: 再ログイン(セッション取得)が必要なエラー、3: メンテナンス中エラー、4: 何もしない

        '''
        stock_code = target[0]
        num = target[1]

        # 一般売注文確認画面へリクエストを送る
        result, soup = self.smbc.order.confirm(self.smbc_session, stock_code, num)
        if result == False:
            return 2

        soup_text = soup.text

        # メンテナンスチェック
        if 'NOL11001E' in soup_text:
            self.log.warning('メンテナンス中のため注文できません')
            return 3

        # 取扱チェック TODO 制度でも在庫入るっぽい?要検証
        if 'NOL51305E' in soup_text:
            self.log.warning('一般信用非取扱銘柄のため注文できません')
            return 4

        # 余力チェック
        if 'NOL51015E' in soup_text:
            self.log.warning('余力が足りないため注文できません')
            return 1

        # 在庫チェック
        if 'NOL75401E' in soup_text or 'NOL75400E' in soup_text:
            self.log.info('一般信用在庫が足りないため注文できません')
            return 4

        # 空売り規制チェック
        if 'NOL51163E' in soup_text:
            self.log.info('取引規制中のため注文できません')
            return 1

        # 注文用のトークンID/URLIDの取得
        try:
            token_id = soup.find('input', {'name': 'tokenId'}).get('value')
            url_match = re.search(r'OdrMng/(.+)/sinyo/tku_odr/exec', str(soup))
            url_id = url_match.groups()[0]
        except Exception as e:
            self.log.error(f'不明なエラーです\n{e}')
            return 2

        # 注文リクエストを送る
        result, soup = self.smbc.order.order(self.smbc_session, stock_code, num, token_id, url_id)
        if result == False:
            return 2

        soup_text = soup.text

        # パスワードチェック
        if 'NOL76511E' in soup_text:
            self.log.error('パスワードが正しくありません')
            return -1

        # 注文完了チェック
        if not '売り注文を受付ました' in soup_text:
            self.log.error('不明なエラーです')
            return 2

        self.log.info(f'注文が完了しました 証券コード: {stock_code} 株数: {num}')
        self.output.line(f'注文が完了しました 証券コード: {stock_code} 株数: {num}', config.LINE_NOTIFY_API_KEY)

        return 1


    def time_manage(self):
        '''時間調整を行う'''
        # 時間取得
        now = datetime.now()
        target_time = False

        ## 全日共通時間判定

        # メンテナンス時間(2:00~3:59)なら処理を終了させる
        # 2:00まで動いていたcronを止めるための処理、
        # 5:00争奪戦処理は止めないようにするために、4時台に起動した処理は止めない
        if 2 <= now.hour <= 3:
            self.log.info('メンテナンス時間中なので処理を終了します\n')
            return False

        # メンテナンス時間(4:00~4:59)なら5:00まで待つ
        if now.hour == 4:
            target_time = datetime(now.year, now.month, now.day, 5, 0)
            # 争奪戦用にリミッター解除
            self.limiter = False

        ## 非営業日判定
        if now.weekday() in [5, 6] and target_time == False:
            return True

        # 大引け後注文中断時間(15:00~16:58)なら16:59まで待つ
        if now.hour == 15 or (now.hour == 16 and now.minute < 59):
            target_time = datetime(now.year, now.month, now.day, 16, 59)

        # 16:59なら17:00まで待つ
        elif now.hour == 16 and now.minute == 59:
            target_time = datetime(now.year, now.month, now.day, 17, 00)
            # 争奪戦用にリミッター解除
            self.limiter = False

        # 注文中断時間(20:15~20:18)なら20:19まで待つ
        elif now.hour == 20 and (15 <= now.minute < 19):
            target_time = datetime(now.year, now.month, now.day, 20, 19)

        # 20:19なら20:20まで待つ
        elif now.hour == 20 and now.minute == 19:
            target_time = datetime(now.year, now.month, now.day, 20, 20)
            # 争奪戦用にリミッター解除
            self.limiter = False

        # ザラ場直前・場中・昼休みは処理を行わない TODO いずれ場中でも注文できるように修正する
        elif (now.hour == 8 and now.minute > 50) or 9 <= now.hour <= 15:
            self.log.info('取引時間中のため監視/注文処理は行いません')
            return False

        elif target_time == False:
            return True

        self.log.info(f'wait {(target_time - self.ntp()).total_seconds() * 1e6 / 1e6}s...')
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

    def ntp(self):
        '''NTPサーバーから現在の時刻を取得する'''
        c = ntplib.NTPClient()
        response = c.request('ntp.jst.mfeed.ad.jp', version=3)
        return datetime.fromtimestamp(response.tx_time)

if __name__ == '__main__':
    s = Steal()
    s.main()