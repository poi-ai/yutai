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
        print(session)

if __name__ == '__main__':
    main = Main()
    main.test()