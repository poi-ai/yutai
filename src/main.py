import config, common
import kabucom, matsui, rakuten, sbi, smbc
import sys, time

class Main():
    def __init__(self):
        self.log = common.Log()
        self.line_token = ''
        self.stock_list = []
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
            exit()

        # 対象となる証券会社・の判別
        shoken, exec_type = sys.argv[1], sys.argv[2]

        # auカブコム証券
        if shoken == 'kabucom':
            # 全銘柄の一般在庫をCSVに記録
            if exec_type == 'record':
                self.kabucom_record()
                exit()

            # configファイルで設定した銘柄の一般在庫をLINEで通知
            elif exec_type == 'notice':
                self.kabucom_notice()
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

    def kabucom_record(self):
        '''auカブコム証券の一般在庫情報の取得／CSV出力'''
        # ログイン
        self.log.info('auカブコム証券ログイン開始')
        session = self.kabucom.login.login()
        if session == False:
            return False
        self.log.info('auカブコム証券ログイン終了')

        self.log.info('auカブコム証券一般在庫取得／出力開始')

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

        self.log.info('auカブコム証券一般在庫取得／出力終了')

        return True

    def kabucom_notice(self):
        '''auカブコム証券の設定ファイルで指定した銘柄コードの一般在庫をLINEで通知する'''

        # 設定データのチェック
        self.notice_check()

        # TODO 取得処理


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
            if len(config.TARGET_STOCK_CODE_LIST) == 0:
                self.log.warning('config.pyに通知対象銘柄の設定がされていません')
                exit()
            else:
                self.stock_list = config.TARGET_STOCK_CODE_LIST
        except AttributeError:
            self.log.error('config.pyに通知対象銘柄用の変数(TARGET_STOCK_CODE_LIST)が定義されていません')
            exit()

        return True

    def test(self):
        '''テスト用コード'''
        self.notice_check()

if __name__ == '__main__':
    main = Main()
    #main.main()

    main.test()