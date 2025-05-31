import base64
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class Mail():
    '''GmailのAPIを実行するクラス'''

    def __init__(self, log, token):
        '''
        Args:
            log(Log): カスタムログ
            token(Auth): 認証情報/トークンを管理するクラス
        '''
        self.log = log
        self.token = token

    def get_message_ids(self, query = '', max_results = 30):
        '''
        メッセージのID一覧を取得する

        Args:
            query(str): 検索クエリ
                例)'from:example@gmail.com' example@gmail.comからのメールを取得
                    空文字を指定した場合は全てのメールを取得

            max_results(int): 取得するメッセージの最大数
                デフォルトは30件

        Returns:
            list or False: メッセージIDのリスト
        '''
        try:
            # Gmail API サービスを構築
            service = build('gmail', 'v1', credentials = self.token.token_obj, cache_discovery = False)
            # メッセージ一覧を取得
            results = service.users().messages().list(userId = 'me', q = query, maxResults = max_results).execute()
            messages = results.get('messages', [])
            message_ids = [message['id'] for message in messages]
            self.log.info(f'取得したメッセージID: {message_ids}')
            return message_ids
        except HttpError as error:
            self.log.error(f'メッセージIDの取得に失敗しました: {error}')
            return False
        except Exception as e:
            self.log.error(f'予期しないエラーが発生しました: {e}')
            return False

    def get_message_content(self, message_id):
        '''
        メッセージIDからメールの内容を取得する

        Args:
            message_id(str): Gmail固有のメッセージID

        Returns:
            dict or False: メール内容(件名/送信者/本文)
                subject: 件名、sender: 送信者、body: 本文
        '''
        try:
            # Gmail APIからメッセージを取得
            service = build('gmail', 'v1', credentials=self.token.token_obj, cache_discovery = False)
            message = service.users().messages().get(userId = 'me', id = message_id, format='full').execute()
            payload = message.get('payload', {})
            headers = payload.get('headers', [])

            # 件名と送信者を抽出
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
            body = base64.urlsafe_b64decode(payload.get('body', {}).get('data', '')).decode('utf-8')

            return {
                'subject': subject,
                'sender': sender,
                'body': body
            }
        except HttpError as error:
            self.log.error(f'メール内容の取得に失敗しました (ID: {message_id}): {error}')
            return False
        except Exception as e:
            self.log.error(f'予期しないエラーが発生しました (ID: {message_id}): {e}')
            return False