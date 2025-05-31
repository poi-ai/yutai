import requests
import time
import chromedriver_autoinstaller
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class Login():
    '''SMBC日興証券にログインを行う'''

    def __init__(self, log, branch_code, account_number, password):
        '''
        Args:
            log(Log): カスタムログ
            branch_code(int): 支店コード
            account_number(int): 口座番号
            password(str): パスワード

        '''
        self.log = log
        self.branch_code = branch_code
        self.account_number = account_number
        self.password = password
        self.otp_create_info = {}
        self.otp_input_info = {}

    def login(self):
        '''
        SMBC日興証券にログインを行う(requests)

        Return:
            session(requests.sessions.Session) or False: ログインを行った状態のセッション情報
            display_type(str): 遷移した画面の種別
                success: ログイン後の画面(ログイン成功)
                otp confirm: ワンタイムパスワードの発行画面
                otp input: ワンタイムパスワードの入力画面

        '''
        session = requests.session()

        # Chromeに偽装するヘッダーを付ける
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Referer': 'https://trade.smbcnikko.co.jp/Login/0/login/ipan_web/exec'
        }

        login_info = {
            "koza1": self.branch_code,
            "koza2": self.account_number,
            "passwd": self.password,
            "syokiGamen": "0",
            "logIn": "ログイン",
        }

        try:
            r = session.post('https://trade.smbcnikko.co.jp/Login/0/login/ipan_web/exec', data = login_info, headers = headers)
        except:
            self.log.error('接続に失敗')
            return False, None

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False, None

        soup = BeautifulSoup(r.content, 'lxml')
        soup_text = soup.text

        # 二段階認証が表示された場合
        if 'ワンタイムパスワードを送信します' in soup_text:
            self.log.warning('ワンタイムパスワードの発行が必要なためログインできません')
            self.otp_create_info['url'] = soup.find('form', id='otp_select_form').get('action')
            self.otp_create_info['oldSessionId'] = soup.find('input', attrs = {'name': 'oldSessionId'}).get('value')
            self.otp_create_info['tokenId'] = soup.find('input', attrs = {'name': 'tokenId'}).get('value')
            return session, 'otp confirm'

        # 既にワンタイムパスワード発行済みの場合
        if 'ワンタイムパスワードを送信しました' in soup_text:
            self.log.warning('ワンタイムパスワード発行済で入力が必要なためログインできません')
            self.otp_input_info['url'] = soup.find('form', attrs = {'name': 'F1'}).get('action')
            self.otp_input_info['oldSessionId'] = soup.find('input', attrs = {'name': 'oldSessionId'}).get('value')
            self.otp_input_info['tokenId'] = soup.find('input', attrs = {'name': 'tokenId'}).get('value')
            self.otp_input_info['otpYkoKign'] = soup.find('input', attrs = {'name': 'otpYkoKign'}).get('value')
            return session, 'otp input'

        # 支店コード・口座番号・パスワードのどれかが違う
        if 'NOL11003E' in soup_text:
            self.log.error('ログイン認証エラー')
            return False, None

        # ログイン後のトップページに遷移できているか確認
        if '前回ログイン' not in soup_text:
            self.log.error('ログインエラー')
            return False, None

        return session, 'success'

    def login_selenium(self):
        '''
        SMBC日興証券にログインを行う(Selenium)

        Return:
            driver(webdriver.Chrome) or False: ログインを行った状態のドライバー
            display_type(str): 遷移した画面の種別
                success: ログイン後の画面(ログイン成功)
                otp confirm: ワンタイムパスワードの発行画面
                otp input: ワンタイムパスワードの入力画面

        '''
        # ChromeDriverのバージョンチェック・最新版インストール
        try:
            chromedriver_autoinstaller.install()
        except Exception as e:
            self.log.error(f'ChromeDriverのインストールに失敗: {e}')
            return False, None

        options = Options()
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36')
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            self.log.error(f'ChromeDriverの起動に失敗: {e}')
            return False, None

        try:
            url = 'https://trade.smbcnikko.co.jp/Login/0/login/ipan_web/exec'
            driver.get(url)

            time.sleep(1)

            # 支店コード・口座番号・パスワードを入力
            branch_input = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/div[1]/div/div/div[1]/div[1]/div/form/div[1]/div[2]/div/input')
            branch_input.clear()
            branch_input.send_keys(self.branch_code)

            account_input = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/div[1]/div/div/div[1]/div[1]/div/form/div[2]/div[2]/div/input')
            account_input.clear()
            account_input.send_keys(self.account_number)

            password_input = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/div[1]/div/div/div[1]/div[1]/div/form/div[3]/div[2]/div[1]/input')
            password_input.clear()
            password_input.send_keys(self.password)

            # ログインボタンをクリック
            login_button = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/div[1]/div/div/div[1]/div[1]/div/form/div[4]/div/button')
            login_button.click()

            time.sleep(3)

            # 遷移後のページのソースを取得
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            soup_text = soup.text

            # 二段階認証が表示された場合
            if 'ワンタイムパスワードを送信します' in soup_text:
                self.log.warning('ワンタイムパスワードの発行が必要なためログインできません')
                return driver, 'otp confirm'

            # 既にワンタイムパスワード発行済みの場合
            if 'ワンタイムパスワードを送信しました' in soup_text:
                self.log.warning('ワンタイムパスワードの発行が必要なためログインできません(ワンタイムパスワード発行済)')
                return driver, 'otp input'

            # ログインに成功した場合
            if '前回ログイン' in soup_text:
                self.log.info('ログイン成功')
                return driver, 'success'

            time.sleep(20)

        except Exception as e:
            self.log.error(f'ログイン処理でエラー: {e}')
            driver.quit()
            return False, None


    def create_otp(self, driver):
        '''
        ワンタイムパスワード発行リクエストを投げる

        Return:
            driver(webdriver.Chrome) or False: 成功後のドライバー or エラー

        '''

        try:
            url = f'https://trade.smbcnikko.co.jp{self.otp_create_info["url"]}'
            driver.get(url)

            # 発行ボタンをクリックする
            issue_button = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/form/div[2]/div/button')
            issue_button.click()

            time.sleep(1)
            page_source = driver.page_source

            # 送信成功画面に遷移したか確認
            if 'ワンタイムパスワードを送信しました' not in page_source:
                self.log.error('ワンタイムパスワード送信に失敗')
                return False

            self.log.info('ワンタイムパスワード送信成功')
            return driver

        except Exception as e:
            self.log.error(f'ワンタイムパスワード送信処理でエラー {e}')
            return False

    def send_otp(self, driver, otp):
        '''
        受信したワンタイムパスワードを入力する

        Args:
            driver(webdriver.Chrome): SeleniumのWebDriverインスタンス
            otp(str): ワンタイムパスワード

        Return:
            bool: 成功時True、失敗時False
        '''

        try:
            url = f'https://trade.smbcnikko.co.jp{self.otp_input_info["url"]}'
            driver.get(url)

            # ワンタイムパスワードを入力
            otp_input = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/div[2]/form/div[1]/div/div/input')
            otp_input.clear()
            otp_input.send_keys(otp)

            # 認証ボタンをクリック
            auth_button = driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div/div[2]/form/div[2]/button')
            auth_button.click()

            page_source = driver.page_source
            if '前回ログイン' not in page_source:
                self.log.error('ワンタイムパスワードの認証に失敗')
                return False

            self.log.info('ワンタイムパスワード認証成功')
            return driver

        except Exception as e:
            self.log.error(f'ワンタイムパスワード入力処理でエラー: {e}')
            driver.quit()
            return False
