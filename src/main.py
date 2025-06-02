import config, common
import gmail, kabucom, matsui, rakuten, sbi, smbc
import csv, sys, time, pandas as pd, re, requests, traceback

class Main():
    def __init__(self):
        self.log = common.Log()
        self.first_stock_list = []
        self.second_stock_list = []
        self.third_stock_list = []
        self.steal_list = []
        try:
            self.output = common.Output(self.log)
            self.culc = common.Culc()
            self.kabucom = kabucom.Kabucom(self.log,
                                        config.KABUCOM_ACCOUNT_NUMBER,
                                        config.KABUCOM_PASSWORD)
            self.matsui = matsui.Matsui()
            self.rakuten = rakuten.Rakuten()
            self.sbi = sbi.Sbi(self.log,
                            config.SBI_USER_NAME,
                            config.SBI_LOGIN_PASSWORD)
            self.smbc = smbc.Smbc(self.log,
                                config.SMBC_BRANCH_CODE,
                                config.SMBC_ACCOUNT_NUMBER,
                                config.SMBC_LOGIN_PASSWORD)
            self.gmail = gmail.Gmail(self.log)
        except AttributeError:
            self.log.error('config.pyの証券会社のID・パスワード設定が正常に行われていません')
            exit()

    def main(self):
        '''主処理'''
        if len(sys.argv) < 3:
            self.log.error('コマンドライン引数が足りません')
            return False

        # 対象となる証券会社・の判別
        shoken, exec_type = sys.argv[1], sys.argv[2]

        # auカブコム証券
        if shoken == 'kabucom':
            # 全銘柄の一般在庫をCSVに記録
            if exec_type == 'record':
                # auカブコム証券のWebサイトから一般在庫データの取得
                csv_data = self.kabucom_get_csv()
                if csv_data == False:
                    return False

                # 注文受付時間チェック
                if '翌営業日分の一般信用売建可能数量' in csv_data:
                    self.log.warning('auカブコム証券の注文受付時間外です')
                    return True

                # 一般在庫データの成型
                mold_data, data_type = self.kabucom_mold_csv(csv_data)

                # CSV出力
                self.log.info(f'auカブコム証券一般在庫CSV出力開始')
                try:
                    self.output.output_csv(mold_data, f'{self.log.now().strftime("%Y")}_kabucom_stock_{data_type}')
                except Exception as e:
                    self.log.error('auカブコム証券一般在庫CSV出力失敗')
                    self.log.error(e)
                self.log.info('auカブコム証券一般在庫CSV出力終了')

                return True

            # configファイルで設定した銘柄の一般在庫をLINEで通知
            elif exec_type == 'notice':
                # 設定値チェック
                self.notice_check(shoken = 1)

                # auカブコム証券のWebサイトから一般在庫データの取得
                csv_data = self.kabucom_get_csv()
                if csv_data == False:
                    return False

                # 注文受付時間チェック
                if '翌営業日分の一般信用売建可能数量' in csv_data:
                    self.log.warning('auカブコム証券の注文受付時間外です')
                    return True

                # 一般在庫データの成型
                mold_data, data_type = self.kabucom_mold_csv(csv_data)

                # 取得対象リストの結合
                all_codes = [str(code) for code in config.FIRST_TARGET_STOCK_CODE_LIST] +\
                            [str(code) for code in config.SECOND_TARGET_STOCK_CODE_LIST] +\
                            [str(code) for code in config.THIRD_TARGET_STOCK_CODE_LIST]

                # CSVファイルに出力
                for stock in mold_data:
                    # 抽選受付中(19:30~20:30)の場合
                    if data_type == 'lottery':
                        result, error_message = self.output.zaiko_csv(company = 'kabucom_all',
                                                                      stock_code = stock['stock_code'],
                                                                      stock_num = f"{stock['order_num']}/{stock['stock_num']}",
                                                                      csv_name = config.CSV_NAME)

                        # 通知対象の銘柄コードのリストに含まれている場合
                        if str(stock['stock_code']) in all_codes:
                            result, error_message = self.output.zaiko_csv(company = 'kabucom',
                                                                          stock_code = stock['stock_code'],
                                                                          stock_num = f"{stock['order_num']}/{stock['stock_num']}",
                                                                          csv_name = config.CSV_NAME)
                    else:
                        result, error_message = self.output.zaiko_csv(company = 'kabucom_all',
                                                                      stock_code = stock['stock_code'],
                                                                      stock_num = stock['stock_num'],
                                                                      csv_name = config.CSV_NAME)

                        # 通知対象の銘柄コードのリストに含まれている場合
                        if str(stock['stock_code']) in all_codes:
                            result, error_message = self.output.zaiko_csv(company = 'kabucom',
                                                                          stock_code = stock['stock_code'],
                                                                          stock_num = stock['stock_num'],
                                                                          csv_name = config.CSV_NAME)

                    if result == False:
                        self.log.error(error_message)

                # LINEで送信する設定になっている場合のみでデータ送信
                if config.LINE_STOCK_NOTICE:
                    # 1群目
                    self.kabucom_line_send(mold_data, data_type, self.first_stock_list)
                    # 2群目
                    self.kabucom_line_send(mold_data, data_type, self.second_stock_list)
                    # 3群目
                    self.kabucom_line_send(mold_data, data_type, self.third_stock_list)
                exit()

            # 実行処理の設定が不正
            else:
                self.log.error('第二引数が無効です')
                exit()

        # SMBC日興証券
        elif shoken == 'smbc':
            # 一般在庫をCSVに記録
            if exec_type == 'record':
                self.smbc_record()
                exit()

            # configファイルで設定した銘柄の一般在庫をLINEで通知
            elif exec_type == 'notice':
                self.smbc_notice()
                exit()

            # コマンドライン引数で指定した銘柄コードの注文を行う
            elif exec_type == 'order':
                # コマンドライン引数チェック
                if len(sys.argv) < 4:
                    self.log.error('コマンドライン引数が足りません')
                    return False
                if len(sys.argv[3]) != 4:
                    self.log.error('銘柄コードが正しくありません')

                # 注文処理
                #self.smbc_order(sys.argv[3])
                exit()

            # 空売り注文が可能かをチェックする
            elif exec_type == 'check':
                self.smbc_check()
                exit()

            # 実行処理の設定が不正
            else:
                self.log.error('第二引数が無効です')
                exit()

        # 証券会社名不正
        else:
            self.log.error('第一引数が無効です')

    def kabucom_get_csv(self):
        '''
        auカブコム証券の一般在庫情報のCSVを取得

        Returns:
            stock_csv.decode(str): strにデコードされた在庫情報のCSV

        '''
        # ログイン
        self.log.info('auカブコム証券ログイン開始')
        session = self.kabucom.login.login()
        if session == False:
            return False
        self.log.info('auカブコム証券ログイン終了')

        if config.SLOW_PROCESS:
            time.sleep(5)

        self.log.info('auカブコム証券一般在庫取得開始')

        # 優待あり銘柄の在庫情報(+注文情報)をCSVのバイナリで取得する
        stock_csv = self.kabucom.get.stock_csv(session)
        if stock_csv == False:
            return False

        ''' CSVが出力ができなくなった場合は下記のページ送りでのチェック方法を使用する
        # 対象件数取得
        self.log.info(f'対象件数取得開始')
        total_num, pages = self.kabucom.get.subject_num(session)
        if total_num == False:
            return False
        self.log.info(f'対象件数取得終了 対象件数: {total_num}件／全{pages}ページ')

        for page in range(1, pages + 1):
            # 一般在庫情報取得
            self.log.info(f'{page}ページ目取得開始')
            stock_list = self.kabucom.get.stock_num(session, page)

            # 取得失敗
            if stock_list == False or len(stock_list) == 0:
                return False

            self.log.info(f'{page}ページ目取得終了')

            # 取得情報がない(=取得するデータがこれ以上ない)
            if stock_list == []:
                break

            # CSV出力
            self.log.info(f'{page}ページ目CSV出力開始')
            result = self.output.output_csv(stock_list, f'kabucom_stock{self.log.now().strftime("%Y")}')
            if result == False:
                return False
            self.log.info(f'{page}ページ目CSV出力終了')
            time.sleep(2)
        '''

        self.log.info('auカブコム証券一般在庫取得終了')

        # バイナリを文字列に変換して返す
        return stock_csv.decode()

    def kabucom_mold_csv(self, stock_data):
        '''auカブコム証券から取得した一般在庫データを加工する

        Args:
            stock_data(str): 取得した一般在庫データをデコードしたもの

        Returns:
            rows(list[dict[], dict[]]): 成型後の一般在庫データ
            data_type(str): データの種別
                order: 注文受付中、lottery: 抽選受付中

        '''
        self.log.info('auカブコム証券一般在庫データ成型開始')

        # 在庫補充後の抽選受付時間(営業日19:30~20:30)かそれ以外か
        if '申込数量' in stock_data:
            data_type = 'lottery'
        else:
            data_type = 'order'

        # 行ごとに分割してリスト化
        rows = stock_data.strip().split('\r\n')

        # ヘッダー行を書き換え
        if data_type == 'lottery':
            header = ['stock_code', 'stock_name', 'order_num', 'stock_num', 'premium_lower', 'premium_upper']
        else:
            header = ['stock_code', 'stock_name', 'stock_num', 'premium']

        # 各行(=銘柄ごとのデータ)を操作
        for i in range(1, len(rows)):
            # 前方空白/信用種別の削除
            rows[i] = rows[i].lstrip().replace('長期,', '')
            # 連想配列に変換
            rows[i] = dict(zip(header, rows[i].split(',')))

            # プレミアム料なしを0.0円として追加
            if data_type == 'lottery':
                if rows[i]['premium_lower'] == '':
                    rows[i]['premium_lower'] = '0.0'
                if rows[i]['premium_upper'] == '':
                    rows[i]['premium_upper'] = '0.0'
            else:
                if rows[i]['premium'] == '':
                    rows[i]['premium'] = '0.0'

        # ヘッダー行削除
        rows.pop(0)
        self.log.info('auカブコム証券一般在庫データ成型終了')

        return rows, data_type

    def kabucom_line_send(self, stock_data, data_type, code_list):
        '''auカブコム証券で取得した一般在庫データをLINEで送る

        Args:
            stock_data(list[dict{},dict{}...]): 成型済み一般在庫データ
            data_type(str): データの種別
                order: 注文受付中、lottery: 抽選受付中
            code_list(list): 通知対象の銘柄コードのリスト

        '''
        if len(code_list) == 0: return

        self.log.info('auカブコム証券一般在庫データLINE送信処理開始')

        # 優待の補完情報を持つCSVの読み込み(存在しなかったら使わない)
        df = self.get_stock_info_csv()

        # LINEで送信するメッセージの作成
        notice_message = ''
        # 通知対象の証券コード
        for code in code_list:
            zaiko_exist_flag = False
            # 取得した一般在庫データ一覧
            for stock in stock_data:
                if stock['stock_code'] == str(code):
                    # 注文受付中の場合
                    if data_type == 'order':
                        notice_message += f'【({stock["stock_code"]}){stock["stock_name"][:10]}】\n在庫: {stock["stock_num"]}株 プレ料: {stock["premium"]}円\n'
                    # 抽選受付中の場合
                    else:
                        notice_message += f'【({stock["stock_code"]}){stock["stock_name"][:10]}】\n在庫: {stock["order_num"]}/{stock["stock_num"]}株 プレ料: {stock["premium_lower"]}~{stock["premium_upper"]}円\n'

                    # 補完情報がある場合追加挿入する
                    # 補完情報は毎月人力で作らないといけないので一旦凍結
                    #if not df is False:
                    #    notice_message += self.create_stock_info_message(stock["stock_code"], df)

                    zaiko_exist_flag = True
                    break

            # 在庫切れ云々でなくそもそも取り扱いをしていない場合
            if not zaiko_exist_flag:
                # 補完情報を持つCSVに銘柄名があればそっから引っ張る
                if not df is False:
                    try:
                        notice_message += f"\n({str(code)}){str(df[df['銘柄コード'] == int(code)]['企業名'].iloc[0])[:10]}の一般在庫情報はありません\n"  # TODO int判定だといずれ死ぬのでそのうち直す
                    except:
                        notice_message += f'\n証券コード:{str(code)}の一般在庫情報はありません\n'
                else:
                    notice_message += f'\n証券コード:{str(code)}の一般在庫情報はありません\n'

        self.line_send(notice_message)

        self.log.info('auカブコム証券一般在庫データLINE送信処理終了')

    def smbc_record(self):
        '''SMBC日興証券の一般在庫情報の取得／CSV出力'''

        # ログイン
        self.log.info('SMBC日興証券ログイン開始')
        session = self.smbc_login()
        if session == False:
            return False
        self.log.info('SMBC日興証券ログイン終了')

        # 一般在庫情報取得
        self.log.info('SMBC日興証券一般在庫取得開始')

        # 対象件数取得
        self.log.info(f'対象件数取得開始')
        total_num, pages = self.smbc.get.subject_num(session)
        if total_num == False:
            return False
        self.log.info(f'対象件数取得終了 対象件数: {total_num}件／全{pages}ページ')

        for page in range(1, pages + 1):
            # 一般在庫情報取得
            self.log.info(f'{page}ページ目取得開始')
            stock_list = self.smbc.get.stock_num(session, page)

            # 取得失敗
            if stock_list == False or len(stock_list) == 0:
                return False

            self.log.info(f'{page}ページ目取得終了')

            # 取得情報がない(=取得するデータがこれ以上ない)
            if stock_list == []:
                break

            # CSV出力
            self.log.info(f'{page}ページ目CSV出力開始')
            result = self.output.output_csv(stock_list, f'smbc_stock{self.log.now().strftime("%Y")}')
            if result == False:
                return False
            self.log.info(f'{page}ページ目CSV出力終了')

            if config.SLOW_PROCESS:
                time.sleep(5)
            else:
                time.sleep(3)

        self.log.info('SMBC日興証券一般在庫取得／出力終了')

        return True

    def smbc_notice(self):
        '''SMBC日興証券の設定ファイルで指定した銘柄コードの一般在庫をLINEで通知する'''

        # 設定データのチェック
        self.notice_check(shoken = 2)

        # steal_dataのリストから証券コードのみを取り出す
        steal_list = [data[0] for data in self.steal_list]

        # 証券コードの結合を行う
        all_codes = config.FIRST_TARGET_STOCK_CODE_LIST +\
                    config.SECOND_TARGET_STOCK_CODE_LIST +\
                    config.THIRD_TARGET_STOCK_CODE_LIST +\
                    steal_list

        # 重複を削除
        unique_codes = set(all_codes)

        # 在庫数と合わせて保持できるように連想配列に書き換える
        mix_code_list = {code: None for code in unique_codes}

        # ログイン
        self.log.info('SMBC日興証券ログイン開始')
        session = self.smbc_login()
        if session == False:
            return False
        self.log.info('SMBC日興証券ログイン終了')

        if config.SLOW_PROCESS:
            time.sleep(5)
        else:
            time.sleep(2)

        self.log.info('SMBC日興証券一般在庫取得開始')

        # 証券コードの上1桁の値ごとに処理を行う
        for top_num in range(1, 10):
            # 取得対象の中に上1桁がtop_numのものが何個存在するか
            target_count = sum(1 for item in [str(code)[0] for code in list(mix_code_list.keys())] if str(item) == str(top_num))

            # なければチェックの必要がないのでスキップ
            if target_count == 0:
                continue

            # 上1桁が一致する取得対象のコードで辞書順で一番最後値を取得する
            max_code = str(sorted([str(code) for code in list(mix_code_list.keys()) if str(code)[0] == str(top_num)])[-1])

            # ページ数取得
            self.log.info(f'ページ数取得開始')
            total_num, pages = self.smbc.get.subject_num(session, output_type = str(top_num))
            if total_num == False:
                return False
            self.log.info(f'ページ数取得終了 証券コードの上1桁: {top_num} 、全{pages}ページ')

            if config.SLOW_PROCESS:
                time.sleep(5)
            else:
                time.sleep(2)

            # ページことに処理
            for page in range(1, pages + 1):
                # 一般在庫情報取得
                self.log.info(f'{page}ページ目取得開始')
                stock_list = self.smbc.get.stock_num(session, page_no = page, output_type = top_num)

                # 取得失敗
                if stock_list == False or len(stock_list) == 0:
                    self.log.info(f'{page}ページ目取得失敗')
                    continue

                self.log.info(f'{page}ページ目取得終了')

                # 取得情報がない(=取得するデータがこれ以上ない)
                if stock_list == []:
                    continue

                # 取得対象の銘柄コードの情報が含まれているかチェックし、含まれていたら連想配列の値として設定
                for code in mix_code_list.keys():
                    result = [stock for stock in stock_list if stock['stock_code'] == str(code)]
                    if len(result) != 0:
                        mix_code_list[code] = result[0]

                if config.SLOW_PROCESS:
                    time.sleep(5)
                else:
                    time.sleep(2)

                # ページの最後の銘柄が対象銘柄の値よりも大きいか(=これ以降のページに取得対象は存在しないか)
                if stock_list[-1]['stock_code'] >= max_code:
                    break

        self.log.info('SMBC日興証券一般在庫取得終了')

        # 在庫情報のLINE通知
        self.log.info('SMBC日興証券一般在庫出力処理開始')
        message = ''
        for code in mix_code_list.keys():
            if mix_code_list[code] == None:
                message += f'証券コード: {(code)} の在庫データがありません\n'
                stock_num = -1
            else:
                stock = mix_code_list[code]
                message += f"({stock['stock_code']}){stock['stock_name']} 在庫数: {stock['stock_num']}株\n"
                stock_num = stock['stock_num']

            # 記録用CSV出力
            result, error_message = self.output.zaiko_csv(company = 'smbc',
                                                          stock_code = str(code),
                                                          stock_num = stock_num,
                                                          csv_name = config.CSV_NAME)
            if result == False:
                self.log.error(error_message)

        # LINE送信がオンの場合は送る
        if config.LINE_STOCK_NOTICE:
            self.log.info('SMBC日興証券一般在庫LINE通知処理開始')
            self.line_send(message)
            self.log.info('SMBC日興証券一般在庫LINE通知処理終了')

        self.log.info('SMBC日興証券一般在庫出力処理終了')

        # 在庫確保の優先順を決めてCSVに保存
        self.log.info('SMBC日興証券の在庫順ソートCSV出力処理開始')

        # 銘柄取得の優先順を決定するCSVを作成する
        result = self.create_priority(mix_code_list)
        if result == False:
            self.log.info('SMBC日興証券の在庫順ソートCSV出力処理に失敗')
            return False

        self.log.info('SMBC日興証券の在庫順ソートCSV出力処理終了')

    def smbc_order(self, stock_code):
        '''SMBC日興証券で一般空売りの注文を行う'''
        # ログイン
        self.log.info('SMBC日興証券ログイン開始')
        session = self.smbc_login()
        if session == False:
            return False
        self.log.info('SMBC日興証券ログイン終了')

        self.log.info('SMBC日興証券一般空売り注文開始')

        # TODO いろいろ足りてないのでそのままは使えない 呼び出し先のメソッドは使えるのでそれに合わせた形に
        session = self.smbc.order.confirm(session, stock_code)
        if session == False:
            return False
        #self.log.info('SMBC日興証券ログイン終了')

        # TODO 注文リクエスト処理 こっちもいろいろ足りてない
        session = self.smbc.order.order(session, stock_code)
        if session == False:
            return False
        self.log.info('SMBC日興証券一般空売り注文終了')

    def notice_check(self, shoken):
        '''
        対象銘柄の在庫情報をLINE通知に送る処理についてデータのチェックを行う

        Args:
            shoken(int): 証券会社
                1: auカブコム、2: SMBC日興
        '''

        # config.pyかsteal_list.csvのどちらかに対象の銘柄の記載があるか
        target_flag = False

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

        # 在庫数取得銘柄(=注文を行う銘柄ではない)を設定ファイルから取得する
        try:
            if len(config.FIRST_TARGET_STOCK_CODE_LIST) == 0\
                and len(config.SECOND_TARGET_STOCK_CODE_LIST) == 0\
                and len(config.THIRD_TARGET_STOCK_CODE_LIST) == 0:
                self.log.warning('config.pyに通知対象銘柄の設定がされていません')
            else:
                self.first_stock_list = config.FIRST_TARGET_STOCK_CODE_LIST
                self.second_stock_list = config.SECOND_TARGET_STOCK_CODE_LIST
                self.third_stock_list = config.THIRD_TARGET_STOCK_CODE_LIST
                target_flag = True
        except AttributeError:
            self.log.warning('config.pyに通知対象銘柄用の変数(FIRST_TARGET_STOCK_CODE_LIST or SECOND_TARGET_STOCK_CODE_LIST)が定義されていません')

        # 在庫があれば自動発注も行う銘柄についてsteal.pyから取得を行う(自動発注はSMBCのみ)
        if shoken == 2:
            result, steal_list = self.get_steal_list()
            if result == False:
                self.log.error(f'steal_list.csvの取得処理に失敗しました\n{steal_list}')
                self.steal_list = []
            else:
                # 銘柄コードのみ取得
                self.steal_list = steal_list
                target_flag = True

        if target_flag:
            return True

        self.log.warning('取得対象の銘柄がないため処理を終了します')
        exit()

    def smbc_check(self):
        '''SMBC日興証券で空売り注文が行える状態かチェックする'''
        # 配当落調整金の支払期日が近づいた際などにSMBCから重要なお知らせとしてログイン直後の画面に表示がされる
        # この表示がされると確認ボタンを押すまで一切他の画面へ遷移できなくなり、注文や在庫チェックが行えなくなる
        # この場合に仕様上確認ボタンを押すのは難しいので、LINEでログインができない旨の通知を行う

        # LINE Messaging APIのトークンを設定
        try:
            if config.LINE_MESSAGING_API_TOKEN != '':
                self.output.set_messaging_api_token(config.LINE_MESSAGING_API_TOKEN)
            else:
                self.log.warning('config.pyにLINE Messaging APIあるいはNotifyのトークンが設定がされていません')
                exit()
        except AttributeError as e:
            self.log.error('config.pyにLINE Notifyトークン用の変数(LINE_NOTIFY_API_KEY)が定義されていません')
            self.log.error(str(e))
            exit()

        session = None

        # ログイン処理を行う
        for retry_count in range(3):
            self.log.info(f'SMBC日興証券ログイン開始 {retry_count + 1}回目')
            session = self.smbc_login()
            if session == False:
                self.log.error(f'SMBC日興証券ログインに失敗 {retry_count + 1}回目')
                time.sleep(3)
                continue
            self.log.info(f'SMBC日興証券ログイン終了 {retry_count + 1}回目')
            break

        # ログインに3回失敗したらLINEで送信
        if session == False:
            self.line_send('SMBC日興証券にログインができません。重要なお知らせが出ている可能性があります')

        return

    def get_stock_info_csv(self):
        '''
        優待情報補完用CSVをデータフレームとして設定する

        Returns:
            df(pandas.DataFrame): 優待情報補完データ
                ※未配置の場合はFalse
        '''

        try:
            df = pd.read_csv('stock_info.csv')
        except Exception as e:
            return False
        return df

    def create_stock_info_message(self, stock_code, df):
        '''
        指定した証券コードの銘柄の優待情報メッセージを作成する

        Args:
            stock_code(str): 証券コード
            df(pandas.DataFrame): 優待情報

        Returns:
            yutai_message(str): 指定した証券コードの銘柄の優待情報

        '''
        yutai_message = ''
        try:
            stock_row = df[df['銘柄コード'] == int(stock_code)] # TODO int判定だといずれ死ぬのでそのうち直す

            if not pd.isna(stock_row['通常最低保有株数'].iloc[0]):
                yutai_message += f"通常優待:\n 優待商品/{stock_row['通常優待商品'].iloc[0]}\n 必要株数/{int(stock_row['通常最低保有株数'].iloc[0])}株 必要額/{stock_row['最低必要額'].iloc[0]}万円 利回り/{stock_row['通常利回り'].iloc[0]}\n"
            else:
                yutai_message += '通常優待: なし\n'

            if not pd.isna(stock_row['長期最低保有株数'].iloc[0]):
                # 長期で必要な最低必要額の計算
                if pd.isna(stock_row['通常最低保有株数'].iloc[0]):
                    min_money = stock_row['最低必要額'].iloc[0]
                else:
                    min_money = round(float(stock_row['最低必要額'].iloc[0]) / float(stock_row['通常最低保有株数'].iloc[0]) * float(stock_row['長期最低保有株数'].iloc[0]), 2)

                yutai_message += f"長期優待:\n 優待商品/{stock_row['長期優待商品'].iloc[0]}\n 年数/{stock_row['最低保有年数'].iloc[0]}年 必要株数/{int(stock_row['長期最低保有株数'].iloc[0])}株 必要額/{min_money}万円 利回り/{stock_row['長期利回り'].iloc[0]}\n"
            else:
                yutai_message += '長期優待: なし\n'

            if not pd.isna(stock_row['備考'].iloc[0]):
                yutai_message += f"備考:\n{stock_row['備考'].iloc[0]}\n"
        except Exception as e:
            self.log.error(f'優待補完情報メッセージ作成処理でエラー 証券コード: {stock_code}\n{e}\n{traceback.format_exc()}')

        return yutai_message

    def get_steal_list(self):
        '''
        一般売対象銘柄のリストをCSVから取得する

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
        except Exception as e:
            return False, e

        return True, steal_list

    def create_priority(self, zaiko_info):
        '''
        在庫状態から在庫の優先順を決定してCSVへ出力する

        Args:
            zaiko_info(dict{str: int,...}): 在庫情報
                キー名: 証券コード、値: 在庫数

        '''
        # 発注対象リストの取得
        steal_list = self.steal_list

        # 発注対象が存在しない場合は処理なし
        if len(steal_list) == 0:
            return True

        zaiko_exist_list = []
        zaiko_exist_history_list = []
        no_zaiko_list = []

        # 在庫の有無で別のリストに追加 TODO いずれ優先フラグを立てる
        for steal in steal_list:
            try:
                zaiko = zaiko_info[steal[0]]['stock_num']
            except Exception as e:
                self.log.error(f'在庫情報抽出処理でエラー\n{e}')
                continue

            if zaiko != None:
                # 在庫があり、在庫数がsteal_listに記載した確保したい数以上の場合
                if zaiko > 0 and int(zaiko) >= int(steal[1]):
                    #steal[4] = 1
                    zaiko_exist_list.append(steal)
                    zaiko_exist_history_list.append(steal + [self.log.today])
                else:
                    #steal[4] = 0
                    no_zaiko_list.append(steal)
            else:
                #steal[4] = 0
                no_zaiko_list.append(steal)

        # 在庫のある銘柄のみ出力対象とする
        sort_zaiko_list = zaiko_exist_list
        ### 在庫のある銘柄が先頭に来るように結合
        ### sort_zaiko_list = zaiko_exist_list + no_zaiko_list

        # CSVで出力を行い、実行結果を返り値として返す
        # まずはsteal.pyで拾うためのCSVを出力
        result = self.output.output_csv(data = sort_zaiko_list,
                                        file_name = 'priority_steal_list.csv',
                                        add_header = True,
                                        add_time = False,
                                        data_folder = False,
                                        mode = 'w')
        # 次に履歴用のCSVを出力
        result2 = self.output.output_csv(data = sort_zaiko_list,
                                        file_name = f'priority_steal_list_history_{self.log.today_ym}.csv',
                                        add_header = True,
                                        add_time = False,
                                        data_folder = False,
                                        mode = 'a')

        if result == False or result2 == False:
            return False
        return True

    def line_send(self, notice_message):
        '''
        LINEでメッセージ送信をする

        Args:
            notice_message(str): メッセージ内容
        '''

        # LINE Messaging APIを使う場合
        if config.LINE_MESSAGING_API_TOKEN != '':
            # 5000字を超える場合は分割(念のため4950字数ごと)
            notice_message_list = [notice_message[i:i + 4950] for i in range(0, len(notice_message), 4950)]

            # 1度のリクエストで5000文字x5吹き出しまで送信可能なので5吹き出しずつ送信する
            fukidashi_list = []
            for index, message in enumerate(notice_message_list):
                fukidashi_list.append(message)

                if index % 5 == 4:
                    result, error_message = self.output.send_messaging_api(fukidashi_list)
                    if result == False:
                        self.log.error(error_message)
                    fukidashi_list = []

            # 余った部分を送信
            if fukidashi_list != []:
                result, error_message = self.output.send_messaging_api(fukidashi_list)
                if result == False:
                    self.log.error(error_message)

        # LINE Notifyを使う場合
        elif config.LINE_NOTIFY_API_KEY != '':
            # 1000文字を超える場合は分割(念のため990文字ごとに)
            notice_message_list = [notice_message[i:i + 990] for i in range(0, len(notice_message), 990)]

            # 分割したものを一つずつ送信
            for message in notice_message_list:
                # LINEで送信
                result, error_message = self.output.send_notify(message)
                if result == False:
                    self.log.error(error_message)
        else:
            self.log.error(f'LINE Messaging API、Notifyどちらのトークンも設定されていないためメッセージが送信できません\n送信メッセージ: {notice_message}')

    def smbc_login(self):
        '''
        SMBC日興証券のログイン処理を行う
        二段階認証対応が必要な場合があるのでSMBCへのログインは必ずこのメソッドを通す

        Returns:
            session(request.Session): ログインセッション
        '''

        '''
        # ログイン(requests)
        self.log.info('SMBC日興証券ログイン開始')
        session, display_type = self.smbc.login.login()
        if session == False:
            return False

        time.sleep(2)
        '''

        # 二段階認証が必要な場合はSeleniumでログイン画面からやり直す
        self.log.info('SMBC日興証券ログイン(Selenium)開始')
        driver, result = self.smbc.login.login_selenium()
        if result == False:
            self.log.error('SMBC日興証券ログイン(Selenium)に失敗しました')
            self.line_send('SMBC日興証券ログイン(Selenium)に失敗しました') #16 認証確認後削除
            return False
        self.log.info('SMBC日興証券ログイン(Selenium)終了')

        # 二段階認証が必要な場合
        if result == 'otp confirm':
            self.log.info('ワンタイムパスワード発行処理開始')
            driver = self.smbc.login.create_otp(driver)
            if driver == False:
                self.log.error('ワンタイムパスワード発行処理に失敗しました')
                self.line_send('ワンタイムパスワード発行処理に失敗しました') #16 認証確認後削除
                return False
            self.log.info('ワンタイムパスワード発行処理終了')

        # 二段階認証が必要で既にワンタイムパスワードが発行されている場合
        # Gmailから発行したワンタイムパスワードの取得を行う
        # トークンの有効性チェック/期限切れの場合は再発行
        if result == 'otp confirm' or result == 'otp input':
            self.log.info('アクセストークン有効性チェック開始')
            result = self.gmail.token.token_check()
            if result == False:
                return False
            self.log.info('アクセストークン有効性チェック終了')

            otp_value = None
            # Gmailからワンタイムパスワードの取得
            # 送信元アドレスを絞って固有のメールIDを取得
            self.log.info('Gmailからワンタイムパスワード取得開始')
            message_ids = self.gmail.mail.get_message_ids(query = 'from:ez_info@mail.smbcnikko.co.jp')

            # メールIDからワンタイムパスワードを取得
            for message_id in message_ids:
                message = self.gmail.mail.get_message_content(message_id)
                if message:
                    # 件名チェック
                    if 'ワンタイムパスワードのご連絡' in message['subject']:
                        # 本文チェック
                        re.match = re.search(r'ワンタイムパスワードは 「(\d{6})」 です', message['body'])
                        if re.match:
                            otp_value = re.match.group(1)
                            break
                    else:
                        self.log.error('ワンタイムパスワードのメールが取得できませんでした')
                        return False
                else:
                    self.log.error('メールの取得に失敗しました')
                    return False

            if otp_value == None:
                self.log.error('ワンタイムパスワードの取得に失敗しました')
                return False
            self.log.info('Gmailからワンタイムパスワード取得終了')

            # ワンタイムパスワードの送信
            self.log.info('ワンタイムパスワード送信処理開始')
            driver = self.smbc.login.send_otp(driver, otp_value)
            if driver == False:
                self.log.error('ワンタイムパスワード送信処理に失敗しました')
                self.line_send('ワンタイムパスワード送信処理に失敗しました') #16 認証確認後削除
                return False
            self.log.info('ワンタイムパスワード送信処理終了')

        self.log.info('SMBC日興証券ログイン終了')

        # seleniumのセッションをrequestsのセッションに変換する
        session = self.selenium_to_requests(driver)
        if session == False:
            self.log.error('SMBC日興証券のセッション変換に失敗しました')
            return False

        return session

    def selenium_to_requests(self, driver):
        '''
        SeleniumのWebDriverセッションをrequestsのセッションに変換する

        Args:
            driver(selenium.webdriver): SeleniumのWebDriverオブジェクト

        Returns:
            session(requests.Session): 変換後のrequestsのセッション
        '''

        try:
            # Seleniumのクッキーを取得
            cookies = driver.get_cookies()

            # requestsのセッションを作成
            session = requests.Session()

            # Seleniumのクッキーをrequestsのセッションに追加
            for cookie in cookies:
                # requestsのCookieJarにクッキーを追加
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'], expires=cookie.get('expiry'))

            # セッションのUser-AgentをSeleniumのものに設定
            session.headers.update({'User-Agent': driver.execute_script("return navigator.userAgent;")})

            # driverを閉じる
            driver.quit()
        except Exception as e:
            self.log.error(f'Seleniumからrequestsへのセッション変換に失敗しました: {e}')
            return False

        return session

    def test(self):
        '''テスト用コード'''
        return True

if __name__ == '__main__':
    main = Main()
    main.main()

    #main.test()