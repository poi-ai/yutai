import config
import csv
import ntplib
import os
import time
import re
import subprocess
import sys
import holiday
from main import Main
from datetime import datetime

# ころしてでもうばいとる
class Steal(Main):
    '''SMBC日興証券の空売り注文を入れる'''
    def __init__(self):
        super().__init__()
        # SMBC日興証券のセッションを持っているか
        self.smbc_session = False
        # アクセス間隔
        self.limiter = True
        # ザラ場の取引か時間外の取引か
        self.zaraba = False
        # 過剰アクセスエラー数
        self.excessive_access_count = 0
        # 同一プロセスが起動しているか
        self.multi_process = False
        # priority_steal_list.csvから取得するか(1: する、0: しない(=steal_list.csvから取得))
        self.get_priority_flag = False

        # LINE通知用トークンのチェック/設定
        self.line_token_check()

        # 単一銘柄狙い撃ちチェック
        if len(sys.argv) == 3:
            _, self.uni_stock_code, self.uni_stock_num = sys.argv
            self.uni_flag = True
        else:
            self.uni_stock_code, self.uni_stock_num = None, None
            self.uni_flag = False

        # 稼働中同一プロセスチェック
        if self.check_steal_file_exists():
            self.log.info('同一プロセスが起動しているため処理を終わります')
            self.multi_process = True
            exit()

    def __del__(self):
        # 多重プロセス起動以外の場合のみ使用したファイルを削除する
        if self.multi_process == False:
            self.delete_steal_file()
            self.output.delete_csv('./priority_steal_list.csv')

    def line_token_check(self):
        '''LINE通知で使用するトークンのチェックを行う'''

        try:
            # LINE Messaging APIのトークンを設定
            if config.LINE_MESSAGING_API_TOKEN != '':
                self.output.set_messaging_api_token(config.LINE_MESSAGING_API_TOKEN)
            # ない場合はLINE Notifyのトークンを設定(~25/3まで)
            elif config.LINE_NOTIFY_API_KEY != '':
                self.output.set_notify_token(config.LINE_NOTIFY_API_KEY)
            else:
                self.log.warning('config.pyにLINE Messaging APIあるいはNotifyのトークンが設定がされていません')
                exit()
        except AttributeError as e:
            self.log.error('config.pyにLINE Notifyトークン用の変数(LINE_NOTIFY_API_KEY)かMessaging APIトークン用の変数(LINE_MESSAGING_API_TOKEN)が定義されていません')
            self.log.error(str(e))
            exit()

    def main(self):
        '''メイン処理'''

        # 単一銘柄狙い撃ちの場合はsteal_listでなくコマンドライン引数から取得
        if self.uni_flag:
            steal_list = [[str(self.uni_stock_code), str(self.uni_stock_num), 'hoge']]
            # リミッターを外す
            self.limiter = True
            self.log.info(f'単一銘柄狙い撃ち処理を開始します 証券コード: {self.uni_stock_code}、株数: {self.uni_stock_num}株')
        else:
            # 空売り監視/自動注文対象銘柄の取得
            result, steal_list = self.get_steal_list()
            if result == False:
                self.log.error(f'監視/自動注文対象銘柄CSVの取得に失敗\n{steal_list}')
                return False

            # TODO 今は在庫が補充された銘柄のみpriority_steal_listにあるが、
            # いずれは在庫ないのも入れて、リミッター解除後にはそっちも処理するようにしたい

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

        # リミッター制御用カウンター
        counter = 0

        # エラー制御用
        error_check_time = datetime.now()

        # 在庫チェック/注文処理
        while True:
            # 10回アクセスエラーが出ると処理を終了するが間を空いたエラーなら止めないようにする
            check_now_time = datetime.now()
            if check_now_time != error_check_time:
                # 10分ごとにエラーカウントを1減らす
                if check_now_time.minute % 10 == 0:
                    self.excessive_access_count = max(0, self.excessive_access_count - 1)
                    error_check_time = check_now_time

            # 単一銘柄狙い撃ちの場合、リミッターがかかったら(50アクセスしたら)処理終了
            if self.uni_flag and self.limiter:
                self.log.info('単一銘柄狙い撃ち処理を終了します')
                return True

            # 監視/注文対象の銘柄がない場合は終了
            if len(steal_list) == 0: return True

            # 除外銘柄管理用の一時リスト作成
            tmp_list = steal_list

            # 時間再チェック
            result = self.time_manage()
            if result == False:
                return False

            # 1回でも在庫チェックを行った銘柄の証券コード
            checked_list = set()
            request_count = 0

            for target in steal_list:
                request_count += 1

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

                # チェックした銘柄を監視対象から外す(余力不足/非取扱銘柄/注文成功の場合)
                elif result == 1:
                    # 処理対象リストから外す
                    tmp_list = [sublist for sublist in tmp_list if sublist[0] != target[0]]

                # 再ログイン(セッション取得)した方がいいエラー(接続エラー/不明なエラー)
                elif result == 2:
                    self.smbc_session = False
                    time.sleep(1)

                    # 最大3回セッションを取り直す
                    for _ in range(3):
                        self.log.info('SMBC日興証券再ログイン開始')
                        self.smbc_session = self.smbc.login.login()
                        self.log.info('SMBC日興証券再ログイン終了')
                        time.sleep(1)
                        if self.smbc_session != False:
                            break

                    if self.smbc_session == False:
                        self.log.error('セッション取得に3度失敗したため処理を終了します')
                        return False

                    # TODO 不明なエラーが続いた場合の処理も必要

                # メンテナンス時間中か取引時間外のエラー
                elif result == 3 or result == 5:
                    now = datetime.now()
                    # ただしメンテナンスが明けているはずの時間の場合は再チェックする
                    if (now.hour in [5, 17] and now.minute <= 1) or (now.hour == 20 and 20 <= now.minute <= 21):
                        time.sleep(0.5)
                        login_flag = False
                        now = datetime.now()
                        # メンテ時間エラーか取引時間外エラーの表示が出るまでループチェック
                        while (now.hour in [5, 17] and now.minute <= 1) or (now.hour == 20 and 20 <= now.minute <= 21):
                            self.log.info(f'在庫チェック/注文を行います 証券コード: {target[0]}, 株数: {target[1]}')
                            result = self.order_exec(target)

                            # 売り禁か注文成功の場合は対象銘柄から除外後ループから抜ける
                            if result == 1:
                                tmp_list = [sublist for sublist in tmp_list if sublist[0] != target[0]]
                                checked_list.add(target[0])
                                break

                            # ログイン情報関係エラーの場合ログインしなおし
                            if result == 2:
                                time.sleep(1)
                                self.log.info('SMBC日興証券再ログイン開始')
                                self.smbc_session = self.smbc.login.login()
                                self.log.info('SMBC日興証券再ログイン終了')

                            # メンテ中なら0.5秒待機
                            elif result == 3:
                                continue

                            # 在庫不足なら正常に接続はできているのでループから抜ける
                            elif result == 4:
                                checked_list.add(target[0])
                                break

                            # メンテ明けは強制的にセッションが切られるので再ログイン処理が必要
                            elif result == 5 and login_flag == False:
                                self.log.info('SMBC日興証券再ログイン開始')
                                self.smbc_session = self.smbc.login.login()
                                self.log.info('SMBC日興証券再ログイン終了')
                                login_flag = True

                            # 過剰アクセスエラーの場合は0.5秒待機
                            elif result == 6:
                                # 過剰アクセスするとSMBCに怒られるので監視しとく
                                self.excessive_access_count += 1
                                if self.excessive_access_count == 1 or self.excessive_access_count == 5 or self.excessive_access_count >= 10:
                                    self.output.line([f'steal.pyで過剰アクセスエラーが出ています {self.excessive_access_count}回目'])
                                    if self.excessive_access_count >= 10:
                                        self.log.error(f'10回以上過剰アクセスエラーが出ているため処理を強制終了します')
                                        self.output.line([f'10回以上過剰アクセスエラーが出ているため処理を強制終了します'])
                                        exit()
                                continue

                            # 他,続行不可能エラー(-1)の場合などは一旦ループを抜けてループ外で処理させる
                            else:
                                break

                # 過剰アクセスエラーの場合は0.2秒待機(=リミッターなしでも+0.5秒で最小でも0.7秒の間隔)
                elif result == 6:
                    # 過剰アクセスするとSMBCに怒られるので監視しとく
                    self.excessive_access_count += 1
                    if self.excessive_access_count == 1 or self.excessive_access_count == 5 or self.excessive_access_count >= 10:
                        self.output.line([f'steal.pyで過剰アクセスエラーが出ています {self.excessive_access_count}回目'])
                        if self.excessive_access_count >= 10:
                            self.log.error(f'10回以上過剰アクセスエラーが出ているため処理を強制終了します')
                            self.output.line([f'10回以上過剰アクセスエラーが出ているため処理を強制終了します'])
                            exit()
                    time.sleep(0.2)

                # 在庫をチェックできないエラー(メンテ時間/ログイン関連/過剰アクセスエラー)以外は1度以上リクエストを投げたとみなす / 重複の場合は追加されない
                if result not in [2, 3, 5, 6]:
                    checked_list.add(target[0])

                # リミッターチェック
                if self.limiter:
                    time.sleep(3)
                # リミットがかかっていない場合
                else:
                    # それでも1.5秒のマージンを取っておかないと過剰エラーになるので待つ
                    time.sleep(1.5)
                    # 全銘柄で1度以上リクエストを投げたらリミッターをかける
                    if len(checked_list) == len(steal_list):
                        self.log.info('全銘柄で1度以上リクエストを投げたためリミッターをかけます')
                        self.limiter = True
                    # バグのリカバリとして全銘柄2周した場合もリミッターをかける
                    if request_count >= len(steal_list) * 2:
                        self.log.info('全銘柄2周したためリミッターをかけます')
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
        order_price = None

        # ザラ場/お昼休み中か取引時間外か
        if self.zaraba == True:
            # ザラ場時間中はS高で指値 TODO 既にS高(付近)の場合などクロスできない場合のチェック追加
            order_price = self.get_sdaka(stock_code, datetime.now().strftime("%Y/%m/%d"))

            # 取得できなかった場合は対象銘柄から外すエラーとして返す
            if order_price == None:
                self.log.warning('CSVからS高価格が取得できませんでした')
                return 1

        # 一般売注文確認画面へリクエストを送る
        result, soup = self.smbc.order.confirm(self.smbc_session, stock_code, num, order_price)
        if result == False:
            # タイムアウトエラーの場合は在庫不足と同じ扱いにする
            if soup == 1:
                return 4
            return 2

        if result == None:
            self.line_send('steal.pyで異常な頻度のアクセスを検知したため強制終了します')
            exit()

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
            return 1

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

        # 過剰アクセスエラー2
        if 'NOL75998E' in soup_text:
            self.log.warning('過剰アクセスのため注文できません2')
            return 6

        # 仮想売買チェックエラー
        if 'NOL77178E' in soup_text:
            self.log.warning('既に信用買注文が入っているため注文できません')
            return 1

        # 注文用のトークンID/URL IDの取得
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
        result, soup = self.smbc.order.order(self.smbc_session, stock_code, num, token_id, url_id, order_date, order_price)
        if result == False:
            # タイムアウトエラーの場合は在庫不足と同じ扱いにする
            if soup == 1:
                return 4
            return 2

        soup_text = soup.text

        # パスワードチェック
        if 'NOL76511E' in soup_text:
            self.log.error('パスワードが正しくありません(注文確認画面)')
            return -1

        # 注文執行日エラー
        if 'NOL21018E' in soup_text:
            self.log.error('注文執行日が正しくありません(注文確認画面)')
            return -1

        # 過剰アクセスエラー
        if 'NOL76980E' in soup_text:
            self.log.warning('過剰アクセスのため注文できません(注文確認画面)')
            return 6

        # 過剰アクセスエラー2
        if 'NOL75998E' in soup_text:
            self.log.warning('過剰アクセスのため注文できません2(注文確認画面)')
            return 6

        # 在庫チェック
        if 'NOL75401E' in soup_text or 'NOL75400E' in soup_text:
            self.log.info('一般信用在庫が足りないため注文できません(注文確認画面)')
            return 4

        # 仮想売買チェックエラー
        if 'NOL77178E' in soup_text:
            self.log.warning('既に信用買注文が入っているため注文できません')
            return 1

        # 注文完了チェック
        if not '売り注文を受付ました' in soup_text:
            self.log.error('不明なエラーです')
            ### デバッグ用
            current_time = datetime.now().strftime("%Y%m%d%H%M%S%f")
            file_name = f"{current_time}.text"
            with open(file_name, "w", encoding='utf-8') as file:
                file.write(str(soup))
            ### デバッグ用ここまで
            return 2

        # 注文価格がない(=成行)の場合
        if order_price == None:
            self.log.info(f'注文が完了しました 証券コード: {stock_code} 株数: {num}株 注文価格: 成行')
            # LINEで通知
            result, error_message = self.output.line([f'注文が完了しました 証券コード: {stock_code} 株数: {num}株 注文価格: 成行'])
            if result == False:
                self.log.error(error_message)
        # 注文価格がある場合
        else:
            self.log.info(f'注文が完了しました 証券コード: {stock_code} 株数: {num}株 注文価格: {order_price}円')
            result, error_message = self.output.line([f'注文が完了しました 証券コード: {stock_code} 株数: {num}株 注文価格: {order_price}円'])
            if result == False:
                self.log.error(error_message)

        # steal_listから削除し、ordered_listに追加する
        result, error_message = self.ordered_csv_operate(stock_code, num, None)
        if result == False:
            # 既にエラーログを出している(Noneの)場合は出さない
            if error_message is not None:
                self.log.error(error_message)

        return 1

    def time_manage(self):
        '''時間調整を行う'''
        # 時間取得
        now = datetime.now()
        target_time = False

        #############################################
        ###     処理を停止させる時間帯のチェック    ###
        #############################################

        # 非営業日は恐らく在庫補充されなさそうなので、監視をやめる
        if not holiday.is_exchange_workday(now):
            self.log.info('非営業日なので処理を終了します\n')
            return False

        # メンテナンス時間(2:00~3:59)なら処理を終了させる
        # 2:00まで動いていたcronを止めるための処理
        # ただし、5:00争奪戦処理は止めないようにするために、メンテ中でも4時台に起動した処理は止めない
        if 2 <= now.hour <= 3:
            self.log.info('メンテナンス時間中なので処理を終了します\n')
            return False
        ## 22~24時はほぼ補充されないので監視対象から外す TODO 一旦様子見で外す
        #elif 22 <= now.hour <= 24:
        #    self.log.info('在庫のほぼ出ない時間帯(22~24時)なので処理を終了します')
        #    return False
        # 6:30~7:55まではシステム上在庫が補充されないため処理を終了させる
        # ※7:55~7:59も補充されないが、8:00取得のプログラムの動作を止めないようにする
        elif (now.hour == 6 and now.minute >= 30) or (now.hour == 7 and now.minute <= 55):
            self.log.info('在庫が補充されない時間帯(6:30~8:00)なので処理を終了します')
            return False
        # クロージング・オークションから大引け(15:25~15:30)の場合は処理を停止する
        elif now.hour == 15 and (25 <= now.minute <= 30):
            self.log.info('取引終了時間直前のため監視/注文処理を終了します')
            return False

        #############################################
        ###      処理を待機する時間帯のチェック     ###
        #############################################

        # ~~5時のメンテ明けでは必ずセッションが切れるので、セッション接続(ログイン)処理の前に5時まで待機する~~
        # メンテナンス時間(4:00~4:59)なら5:00:42まで待つ
        if now.hour == 4:
            target_time = datetime(now.year, now.month, now.day, 5, 0, 42)
            # 争奪戦用にリミッター解除
            self.limiter = False

        # ~~17:30の取引再開ではセッションが切れないため、17:29まで待機→セッション接続(ログイン)→17:30:03まで待機とする~~
        # 大引け後注文中断時間(15:30~17:28)なら17:29まで待つ
        if (now.hour == 15 and now.minute >= 30) or now.hour == 16 or (now.hour == 17 and now.minute < 29):
            target_time = datetime(now.year, now.month, now.day, 17, 29)

        # 17:29なら17:30:03まで待つ
        elif now.hour == 17 and now.minute == 29:
            target_time = datetime(now.year, now.month, now.day, 17, 30, 3)
            # priority_listから取得した(=在庫補充)銘柄がある場合のみ争奪戦用にリミッター解除
            if self.get_priority_flag:
                self.log.info('priority_steal_list.csvから取得した銘柄があるためリミッターを解除します')
                self.limiter = False
            else:
                self.log.info('priority_steal_list.csvから取得した銘柄がないためリミッターを解除しません')

        # ~~20:20の取引再開でもセッションは切れないため、20:19まで待機→セッション接続(ログイン)→20:20:00まで待機とする~~
        # 注文中断時間(20:15~20:18)なら20:19まで待つ
        elif now.hour == 20 and (15 <= now.minute < 19):
            target_time = datetime(now.year, now.month, now.day, 20, 19)

        # 20:19なら20:20まで待つ
        elif now.hour == 20 and now.minute == 19:
            target_time = datetime(now.year, now.month, now.day, 20, 20)

        #############################################
        ###   注文価格を切り換える時間帯のチェック  ###
        #############################################

        # ザラ場直前から大引け直前(8:00~15:25)まではS高価格で注文を入れる ※それ以外の時間(ザラ場外)では成行で注文
        if (8 <= now.hour <= 14) or (now.hour == 15 and now.minute <= 25):
            if self.zaraba == False:
                self.log.info('ザラ場モードで実行します')
            self.zaraba = True
        else:
            if self.zaraba == True:
                self.log.info('取引時間外モードで実行します')
            self.zaraba = False


        # 待機時間が設定されていないならそのまま返す
        if target_time == False:
            return True

        wait_time = (target_time - self.ntp()).total_seconds()

        self.log.info(f'wait {wait_time}s...')
        time.sleep(wait_time)

        return True

    def get_steal_list(self, get_priority_steal_list = True):
        '''
        一般売対象銘柄のリストをCSVから取得する

        Args:
            get_priority_steal_list(bool): priority_steal_list.csvを取得対象とするか

        Returns:
            result(bool): 実行結果
            steal_list(list) or error_message: 対象銘柄リスト or エラーメッセージ

        '''
        steal_list = []

        # priority_steal_listを取得するか
        if get_priority_steal_list:
            # 在庫状態に応じた優先度順に並び変えたCSVがあればそこから取得
            try:
                with open('priority_steal_list.csv', 'r', newline = '', encoding = 'UTF-8') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        steal_list.append(row)
            except Exception as e:
                self.log.warning(f'監視/自動注文対象銘柄CSVの取得に失敗(優先度ソート)\n{e}')
                steal_list = []

            # 取得できた場合はこれを返す
            if len(steal_list) != 0:
                self.get_priority_flag = True
                return True, steal_list

        # 優先度順のCSVが取れなかった場合は、在庫状態関係なく列挙したlistについて取得する
        try:
            with open('steal_list.csv', 'r', newline = '', encoding = 'UTF-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    steal_list.append(row)
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
                # どっちのサーバーとも取得失敗した場合は標準ライブラリから取得を行う
                return datetime.now()

    def get_sdaka(self, stock_code, date):
        '''
        S高の価格をCSVから取得する

        Args:
            stock_code(str): 証券コード
            date(str): 対象の日付(yyyy/mm/ddフォーマット)

        Returns:
            price(float): S高価格
                ※CSVがない場合やCSV内に記載がない場合はNone
        '''
        file_path = './owarine.csv'
        if not os.path.exists(file_path):
            return None

        with open(file_path, mode='r', encoding = 'utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['stock_code'] == str(stock_code) and row['yoku_date'] == date:
                    return row['yoku_sdaka']

        return None

    def ordered_csv_operate(self, stock_code, num, price = None):
        '''
        空売り注文に成功した銘柄をsteal_list.csvから削除し、recorded_list.csvに追記する

        Args:
            stock_code(str): 証券コード
            num(int): 発注数量
            price(float or None): 発注価格 ※成行の場合はNone

        Returns:
            result(bool): 実行結果
            error_message(str or None): エラーメッセージ ※成功の場合はNone
        '''
        # steal_list.csvを取得 同一プロセスで2回以上削除する可能性があるためインスタンス変数からは取らない
        result, steal_list = self.get_steal_list(False)
        if result == False:
            return result, steal_list

        # 優待補足情報
        yutai_detail = None

        # リストから証券コード・株数が合致する上位1件のみを削除する
        for i, row in enumerate(steal_list):
            if str(row[0]) == str(stock_code) and str(row[1]) == str(num):
                yutai_detail = str(row[2])
                del steal_list[i]
                break

        # 成行の場合は価格が入っていないので設定
        if price == None:
            price = '成行'

        # 削除したレコードの情報をordered_list.csvに記録する
        delete_info = [[datetime.now().strftime('%Y/%m/%d %H:%M:%S'), str(stock_code), str(num), str(price), str(yutai_detail)]]
        result = self.output.output_csv(data = delete_info, file_name = 'ordered_list.csv', add_time = False, data_folder = False, mode = 'a')
        if result == False:
            return result, None # 既にoutput_csv()でエラーログ出しているので出さない

        # 削除後のデータをsteal_listに上書きする
        result = self.output.output_csv(data = steal_list, file_name = 'steal_list.csv', add_time = False, data_folder = False, mode = 'w')
        if result == False:
            return result, None

        return True, None

    def create_steal_file(self):
        '''プロセス使用中のファイルを作成する'''
        file_path = '../tmp/steal'
        with open(file_path, "w"):
            pass
        return True

    def check_steal_file_exists(self):
        '''他に起動しているプロセスがあるかチェックする'''
        file_path = '../tmp/steal'
        # ロックファイルのチェック
        if os.path.exists(file_path):
            try:
                result = subprocess.run(
                    ["ps", "aux"], text=True, capture_output=True, check=True
                )
                count = sum(1 for line in result.stdout.splitlines() if f'python3 steal.py' in line)

                # この実行処理も引っかかるので、2つ以上あれば二重起動とみなす
                if count >= 2:
                    return True
                # プロセスがないのにロックファイルが残っているのはおかしいのでFalseを返し処理を継続させる
                # 削除はデストラクタで削除されるためここでは消さない
                else:
                    self.log.warning('他プロセスで動いてはいませんがロックファイルが残っています')
                    return False
            except Exception as e:
                self.log.error('プロセスチェック処理でエラー')
                return True
        # ロックファイルがない場合
        else:
            self.create_steal_file()
            return False

    def delete_steal_file(self):
        '''プロセス使用中のファイルを削除する'''
        file_path = '../tmp/steal'
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    s = Steal()
    s.main()