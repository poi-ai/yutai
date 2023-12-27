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
        self.sbi = sbi.Sbi()
        self.smbc = smbc.Smbc()

    def test(self):
        '''テスト用コード'''
        session = self.kabucom.login.login()
        if not session:
            print('ログインエラー')

        stock_data = self.kabucom.get.stock_num(session)
        if stock_data == False:
            print('在庫データ取得エラー')


if __name__ == '__main__':
    main = Main()
    main.test()