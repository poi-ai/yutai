import config
import csv
import ntplib
import os
import time
import re
import holiday
from main import Main
from datetime import datetime

# ころしてでもうばいとる
class Steal(Main):
    '''SMBC日興証券の空売り注文を入れる'''
    def __init__(self):
        super().__init__()
        self.smbc_session = False
        self.limiter = True
        # 稼働中同一プロセスチェック
        if self.check_steal_file_exists: return
        self.create_steal_file()

    def __del__(self):
        self.delete_steal_file()

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

                # メンテナンス時間中のエラー
                elif result == 3:
                    now = datetime.now()
                    # ただしメンテナンスが明けているはずの時間の場合は再チェックする
                    if (now.hour in [5, 17] and now.minute <= 1) or (now.hour == 20 and 20 <= now.minute <= 21):
                        login_flag = False
                        now = datetime.now()
                        # メンテ時間エラーか取引時間外エラーの表示が出るまでループチェック
                        while (now.hour in [5, 17] and now.minute <= 1) or (now.hour == 20 and 20 <= now.minute <= 21):
                            self.log.info(f'在庫チェック/注文を行います 証券コード: {target[0]}, 株数: {target[1]}')
                            result = self.order_exec(target)

                            # 売り禁か注文成功の場合は対象銘柄から除外後ループから抜ける
                            if result == 1:
                                tmp_list = [sublist for sublist in tmp_list if sublist[0] != target[0]]
                                break

                            # ログイン情報関係エラーの場合ログインしなおし
                            if result == 2:
                                self.log.info('SMBC日興証券再ログイン開始')
                                self.smbc_session = self.smbc.login.login()
                                self.log.info('SMBC日興証券再ログイン終了')

                            # メンテ中なら0.5秒待機
                            elif result == 3:
                                time.sleep(0.5)

                            # 在庫不足なら正常に接続はできているのでループから抜ける
                            elif result == 4:
                                break

                            # メンテ明けは強制的にセッションが切られるので再ログイン処理が必要
                            elif result == 5 and login_flag == False:
                                self.log.info('SMBC日興証券再ログイン開始')
                                self.smbc_session = self.smbc.login.login()
                                self.log.info('SMBC日興証券再ログイン終了')
                                login_flag = True

                            # 他,続行不可能エラー(-1)の場合などは一旦ループを抜けてループ外で処理させる
                            else:
                                break

                if self.limiter:
                    time.sleep(10)

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
                2: 再ログイン(セッション取得)が必要なエラー、3: メンテナンス中エラー、4: 在庫不足エラー、
                5: 取引時間外エラー、6: 過剰アクセスエラー
                ### TODO 不明なエラーを再ログインとして処理していいかは要検討

        '''
        stock_code = target[0]
        num = target[1]

        # 一般売注文確認画面へリクエストを送る
        result, soup = self.smbc.order.confirm(self.smbc_session, stock_code, num)
        if result == False:
            return 2

        soup_text = soup.text

        # 余力チェック
        if 'NOL51015E' in soup_text:
            self.log.warning('余力が足りないため注文できません')
            return 1

        # 空売り規制チェック
        if 'NOL51163E' in soup_text:
            self.log.info('取引規制中のため注文できません')
            return 1

        # メンテナンスチェック
        if 'NOL11001E' in soup_text:
            self.log.warning('メンテナンス中のため注文できません')
            return 3

        # 取扱チェック ここでの非取扱は東証ではなくSMBC側が指定したものなので、貸借銘柄でも出る
        if 'NOL51305E' in soup_text:
            self.log.warning('一般信用非取扱銘柄のため注文できません')
            return 4

        # 在庫チェック
        if 'NOL75401E' in soup_text or 'NOL75400E' in soup_text:
            self.log.info('一般信用在庫が足りないため注文できません')
            return 4

        # 取引時間外チェック
        if 'NOL20001E' in soup_text:
            self.log.info('取引時間外のため注文できません')
            return 5

        # 過剰アクセスエラー
        if 'NOL76980E' in soup_text:
            self.log.warning('過剰アクセスのため注文できません')
            return 6

        # 注文用のトークンID/URLIDの取得
        try:
            token_id = soup.find('input', {'name': 'tokenId'}).get('value')
            url_match = re.search(r'OdrMng/(.+)/sinyo/tku_odr/exec', str(soup))
            url_id = url_match.groups()[0]
        except Exception as e:
            self.log.error(f'不明なエラーです\n{e}')
            ### デバッグ用
            current_time = datetime.now().strftime("%Y%m%d%H%M%S%f")
            file_name = f"{current_time}.text"
            with open(file_name, "w", encoding='utf-8') as file:
                file.write(str(soup))
            ### デバッグ用ここまで
            return 2

        # 注文日を設定
        now = datetime.now()

        # 15時前なら当日注文、以降なら翌営業日注文
        if now.hour < 15:
            order_date = now.strftime("%Y%m%d")
        else:
            # TODO エラー時の対応
            order_date = holiday.next_exchange_workday(now).strftime("%Y%m%d")

        # 注文リクエストを送る
        result, soup = self.smbc.order.order(self.smbc_session, stock_code, num, token_id, url_id, order_date)
        if result == False:
            return 2

        soup_text = soup.text

        # パスワードチェック
        if 'NOL76511E' in soup_text:
            self.log.error('パスワードが正しくありません')
            return -1

        # 注文執行日エラー
        if 'NOL21018E' in soup_text:
            self.log.error('注文執行日が正しくありません')
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
        # 調整用秒数(SMBCは0秒ぴったりで動かないことが多い)
        add_time = 0

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
            # 5;00の場合は5:00:45くらいまでメンテが明けないので30秒まで待機
            add_time = 30
            # 争奪戦用にリミッター解除
            self.limiter = False

        ## 非営業日ならこれ以上チェックはしない
        if not holiday.is_exchange_workday(now):
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

        wait_time = (target_time - self.ntp()).total_seconds() + add_time

        self.log.info(f'wait {wait_time}s...')
        time.sleep(wait_time)

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
        try:
            c = ntplib.NTPClient()
            server = 'ntp.jst.mfeed.ad.jp' # stratum2
            response = c.request(server, version = 3)
            return datetime.fromtimestamp(response.tx_time)
        except Exception as e:
            self.log.error(f'NTPサーバーからの時刻取得処理に失敗しました サーバー: {server}\n{e}')
            self.log.error(f'別のNTPサーバーから時刻取得を行います')

            try:
                c = ntplib.NTPClient()
                server = 'time.cloudflare.com' # stratum3
                response = c.request(server, version = 3)
                return datetime.fromtimestamp(response.tx_time)
            except Exception as e:
                self.log.error(f'NTPサーバーからの時刻取得処理に失敗しました サーバー: {server}\n{e}')
                raise # TODO ここの対応どうするか考える 今は一旦エラーとして落とす

    def create_steal_file(self):
        '''プロセス使用中のファイルを作成する'''
        file_path = "/tmp/steal"
        with open(file_path, "w"):
            pass
        return True

    def check_steal_file_exists(self):
        '''他に起動しているプロセスがあるかチェックする'''
        file_path = "/tmp/steal"
        return os.path.exists(file_path)

    def delete_steal_file(self):
        '''プロセス使用中のファイルを削除する'''
        file_path = "/tmp/steal"
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    s = Steal()
    s.main()