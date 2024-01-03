import config, common
import kabucom, matsui, rakuten, sbi, smbc
import sys

class Main():
    def __init__(self):
        self.log = common.Log()
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

    def main(self):
        '''主処理'''
        if len(sys.argv) < 3:
            self.log.error('コマンドライン引数が足りません')
            exit()

        # 対象となる証券会社・の判別
        shoken, exec_type = sys.argv[1], sys.argv[2]

        # auカブコム証券
        if shoken == 'kabucom':
            # 一般在庫をCSVに記録
            if exec_type == 'record':
                self.kabucom_record()
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

        # 一般在庫情報取得
        self.log.info('auカブコム証券一般在庫取得開始')
        stock_list = self.kabucom.get.stock_num(session)
        if stock_list == False or len(stock_list) == 0:
            return False
        self.log.info('auカブコム証券一般在庫取得終了')

        # CSV出力
        self.log.info('auカブコム証券一般在庫CSV出力開始')
        result = self.output.output_csv(stock_list, 'kabucom')
        if result == False:
            return False
        self.log.info('auカブコム証券一般在庫CSV出力終了')
        return True

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
        stock_list = self.smbc.get.stock_num(session)
        if stock_list == False or len(stock_list) == 0:
            return False
        self.log.info('SMBC日興証券一般在庫取得終了')

        # CSV出力
        self.log.info('SMBC日興証券一般在庫CSV出力開始')
        result = self.output.output_csv(stock_list, 'smbc')
        if result == False:
            return False
        self.log.info('SMBC日興証券一般在庫CSV出力終了')

        return True

    def test(self):
        '''テスト用コード'''
        session = self.kabucom.login.login()
        if not session:
            print('ログインエラー')
            return

        stock_list = self.kabucom.get.stock_num(session)
        if stock_list == False:
            print('在庫データ取得エラー')
            return

        print(stock_list)


if __name__ == '__main__':
    main = Main()
    main.main()

    #main.test()