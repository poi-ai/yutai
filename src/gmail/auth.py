import os
from datetime import timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from pathlib import Path

class Auth():
    '''Gmail APIの認証情報/トークンを管理するクラス'''
    def __init__(self, log):
        '''
        Args:
            log(Log): カスタムログ

        '''
        self.log = log
        self.scope = ['https://www.googleapis.com/auth/gmail.readonly']
        self.token_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'token')
        self.token_path = os.path.join(self.token_dir, 'gmail_token.txt')
        self.token_obj = None

    def oauth(self):
        ''''
        client_secret_xxx.json を用いて初回のOAuth認証フローを実行する
        既にトークンが存在する場合はこの処理を行う必要はない
        自動で実行される処理には組み込まない想定

        Returns:
            result(bool): 実行結果
        '''
        try:
            # 認証情報を格納しているディレクトリのファイル一覧から認証ファイル(client_secret_xxx.json)を取得
            token_dir_files = os.listdir(self.token_dir)
            client_secret_file_name = [file_name for file_name in token_dir_files if 'client_secret' in file_name]
            if not client_secret_file_name:
                self.log.error('client_secret.json が見つかりません')
                return False

            # 認証ファイルを用いて初回のOAuth認証を実行
            client_secret_path = os.path.join(self.token_dir, client_secret_file_name[0])
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, self.scope)
            token_data = flow.run_local_server(port = 0)

            # 取得したトークンを認証ファイルと同じディレクトリに保存
            result = self.save_token(token_data)
            if not result:
                self.log.error('トークンの保存に失敗しました')
                return False
        except Exception as e:
            self.log.error(f'OAuth認証に失敗しました: {e}')
            return False

        return True

    def token_check(self):
        '''
        アクセストークンの有効期限をチェック/再取得をする

        Returns:
            result(bool): トークンの有効性
        '''
        if not Path(self.token_path).exists():
            self.log.error('トークンファイルが存在しません、OAuth認証を実行してください。')
            return False
        try:
            # アクセストークンの読み込み
            self.token_obj = Credentials.from_authorized_user_file(self.token_path, self.scope)
            # トークンの有効性(期限&スコープ(権限))をチェック
            if not self.token_obj.valid:
                # 有効期限切れ(True)でリフレッシュトークンがある場合は再度アクセストークンを取得する
                if self.token_obj.expired and self.token_obj.refresh_token:
                    self.log.info('アクセストークンの有効期限が切れているため再取得を行います')
                    try:
                        self.token_obj.refresh(Request())
                        self.log.info('アクセストークンの再取得に成功しました')
                    except RefreshError as e:
                        self.log.error(f'アクセストークンの再取得に失敗しました: {e}')
                        return False
                    self.save_token(self.token_obj)
                    return True
                else:
                    # それ以外のエラーの場合はスコープの問題があるので何もしない(手動で直す必要がある)
                    self.log.error('アクセストークンがスコープ(権限)が無効です。設定しなおしてください。')
                    return False
            self.log.info(f'アクセストークンは現在有効です。有効期限: {self.token_obj.expiry + timedelta(hours = 9)}')
            return True
        except FileNotFoundError:
            self.log.error('トークンファイルが見つかりません。')
            return False
        except Exception as e:
            self.log.error(f'トークンのチェックに失敗しました: {e}')
            return False

    def save_token(self, token):
        '''
        アクセストークンを保存する

        Args:
            token(google.oauth2.credentials.Credentials): アクセストークン

        Returns:
            result(bool): 保存結果
        '''
        try:
            with open(self.token_path, 'w') as token_file:
                token_file.write(token.to_json())
        except Exception as e:
            self.log.error(f'トークンの保存に失敗しました: {e}')
            return False
        return True

