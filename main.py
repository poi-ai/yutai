import config
import kabucom
import matsui
import rakuten
import sbi
import smbc

class Main():
    def __init__(self):
        self.kabucom = kabucom.Kabucom(config.KABUCOM_ACCOUNT_NUMBER,
                                       config.KABUCOM_PASSWORD)
        self.matsui = matsui.Matsui()
        self.rakuten = rakuten.Rakuten()
        self.sbi = sbi.Sbi(config.SBI_USER_NAME,
                           config.SBI_LOGIN_PASSWORD)
        self.smbc = smbc.Smbc(config.SMBC_BRANCH_CODE,
                              config.SMBC_ACCOUNT_NUMBER,
                              config.SMBC_LOGIN_PASSWORD)

    def test(self):
        '''テスト用コード'''
        session = self.smbc.login.login()
        if not session:
            print('ログインエラー')

        stock_list = self.smbc.get.stock_num(session)
        if stock_list == False:
            print('在庫データ取得エラー')
            
        print(stock_list)


if __name__ == '__main__':
    main = Main()
    main.test()