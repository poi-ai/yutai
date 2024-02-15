import config, common
import kabucom, matsui, rakuten, sbi, smbc
import sys, time

class Main():
    def __init__(self):
        self.log = common.Log()
        self.line_token = ''
        self.first_stock_list = []
        self.second_stock_list = []
        self.third_stock_list = []
        try:
            self.output = common.Output(self.log)
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
                self.notice_check()

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

                # LINEでデータ送信
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

        self.log.info('auカブコム証券一般在庫取得開始')

        # 優待あり銘柄の在庫情報(+注文情報)をCSVのバイナリで取得する
        stock_csv = self.kabucom.get.stock_csv(session)
        if stock_csv == False:
            return False

        ''' CSVが出力がなくなった場合は下記を使用する
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

        # LINEで送信するメッセージの作成
        notice_message = ''
        # 通知対象の証券コード
        for code in code_list:
            exist_flag = False
            # 取得した一般在庫データ一覧
            for stock in stock_data:
                if stock['stock_code'] == str(code):
                    # 注文受付中の場合
                    if data_type == 'order':
                        notice_message += f'(\n{stock["stock_code"]}){stock["stock_name"][:10]}\n{stock["stock_num"]}株 {stock["premium"]}円'
                    # 抽選受付中の場合
                    else:
                        notice_message += f'(\n{stock["stock_code"]}){stock["stock_name"][:10]}\n{stock["order_num"]}/{stock["stock_num"]}株 {stock["premium_lower"]}~{stock["premium_upper"]}円'
                    exist_flag = True
                    break
            if not exist_flag:
                notice_message += f'証券コード:{str(code)}の一般在庫情報はありません\n'

        # LINEで送信
        result, error_message = self.output.line(notice_message, self.line_token)
        if result == False:
            self.log.error(error_message)

        self.log.info('auカブコム証券一般在庫データLINE送信処理終了')

    def smbc_record(self):
        '''SMBC日興証券の一般在庫情報の取得／CSV出力'''
        # ログイン
        self.log.info('SMBC日興証券ログイン開始')
        session = self.smbc.login.login()
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
            time.sleep(2)

        self.log.info('SMBC日興証券一般在庫取得／出力終了')

        return True

    def smbc_notice(self):
        '''SMBC日興証券の設定ファイルで指定した銘柄コードの一般在庫をLINEで通知する'''

        # 設定データのチェック
        self.notice_check()

        # TODO 取得処理

    def notice_check(self):
        '''対象銘柄の在庫情報をLINE通知に送る処理についてデータのチェックを行う'''
        try:
            if config.LINE_NOTIFY_API_KEY == '':
                self.log.warning('config.pyにLINE Notifyトークンの設定がされていません')
                exit()
            else:
                self.line_token = config.LINE_NOTIFY_API_KEY
        except AttributeError:
            self.log.error('config.pyにLINE Notifyトークン用の変数(LINE_NOTIFY_API_KEY)が定義されていません')
            exit()

        try:
            if len(config.FIRST_TARGET_STOCK_CODE_LIST) == 0\
                or len(config.SECOND_TARGET_STOCK_CODE_LIST) == 0\
                or len(config.THIRD_TARGET_STOCK_CODE_LIST) == 0:
                self.log.warning('config.pyに通知対象銘柄の設定がされていません')
                exit()
            else:
                self.first_stock_list = config.FIRST_TARGET_STOCK_CODE_LIST
                self.second_stock_list = config.SECOND_TARGET_STOCK_CODE_LIST
                self.third_stock_list = config.THIRD_TARGET_STOCK_CODE_LIST
        except AttributeError:
            self.log.error('config.pyに通知対象銘柄用の変数(FIRST_TARGET_STOCK_CODE_LIST or SECOND_TARGET_STOCK_CODE_LIST)が定義されていません')
            exit()

        return True

    def test(self):
        '''テスト用コード'''
        return True

if __name__ == '__main__':
    main = Main()
    main.main()

    #main.test()