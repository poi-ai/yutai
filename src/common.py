import csv
import logging
import inspect
import json
import numpy as np
import os
import pandas as pd
import smtplib
import sys
import re
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class Output():
    def __init__(self, log):
        self.log = log

    def output_csv(self, data, file_name, add_header = True, add_time = True, data_folder = True, mode = None):
        '''
        dict型のデータをCSVへ出力する

        Args:
            data(list[dict{},dict{},...]): dictで保持されているデータのlist
            file_name(str): 出力するCSVのファイル名
            add_header(bool): ヘッダー行を追加するか、file_nameのCSVが既に存在する場合は無視される
            add_time(bool): 出力するCSVに時間情報を付けるか
            data_folder(bool): dataフォルダに格納するか
                Falseの場合はsrc直下
            mode(str): 上書き/新規作成('w')か末尾追記('a')か

        Returns:
            result(bool): 実行結果
        '''

        try:
            # 時間のカラムを追加する
            if add_time:
                data = self.add_time(data)

            # ファイル名の引数に.csvが書かれていなかった場合の救済
            if not '.csv' in file_name:
                file_name = f'{file_name}.csv'

            # dataディレクトリに格納するためのパスを指定
            if data_folder:
                file_path = f'../data/{file_name}'
            else:
                file_path = f'./{file_name}'

            if mode == None:
                # 既に引数のファイルが存在する場合は追記、そうでない場合は上書き（新規作成）
                mode = 'a' if os.path.exists(file_path) else 'w'

            # データがdict型の場合
            if isinstance(data, dict):
                with open(file_path, mode, encoding = 'UTF-8', newline = '') as csvfile:
                    fieldnames = data[0].keys() if data else []
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    if mode == 'w' and add_header:
                        writer.writeheader()

                    for row in data:
                        writer.writerow(row)
            # データがlist型の場合
            else:
                with open(file_path, mode, encoding='UTF-8', newline='') as csvfile:
                    writer = csv.writer(csvfile)

                    for row in data:
                        writer.writerow(row)

        except Exception as e:
            self.log.error(f'CSV出力に失敗しました\n{e}')
            return False

        return True

    def delete_csv(self, file_path):
        '''
        指定したCSVファイルを削除する

        Args:
            file_path(str): 削除するCSVファイルのパス

        Returns:
            result(bool): 実行結果
        '''
        # ファイル名の引数に.csvが書かれていなかった場合の救済
        if not '.csv' in file_path:
            file_path = f'{file_path}.csv'

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                self.log.info(f'削除対象のCSVがありません\nファイルパス: {file_path}')
                return False
        except Exception as e:
            self.log.error(f'CSVの削除処理に失敗しました\nファイルパス: {file_path}\n{e}')
            return False

        return True

    def add_time(self, data_list):
        '''
        dict型のデータに時刻を付ける

        Args:
            data_list(list[dict{},dict{},...]): dictで保持されているデータのlist

        '''
        now = self.log.now()
        current_date = now.strftime("%Y/%m/%d")
        current_time = now.strftime("%H:%M")

        for data in data_list:
            data['date'] = current_date
            data['time'] = current_time

        return data_list

    def line(self, message, token):
        '''
        LINEにメッセージを送信する

        Args:
            message(str) : LINE送信するメッセージ内容
            token(str): LINE Notifyのトークン

        Returns:
            result(bool): 実行結果
            error_message(str): エラー内容

        '''

        # ヘッダー設定
        headers = {'Authorization': f'Bearer {token}'}

        # メッセージ設定
        data = {'message': f'{message}'}

        # メッセージ送信
        try:
            r = requests.post('https://notify-api.line.me/api/notify', headers = headers, data = data)
        except Exception as e:
            return False, f'LINE Notify APIでのメッセージ送信に失敗しました\n{e}'

        if r.status_code != 200:
            try:
                return False, f'LINE Notify APIでエラーが発生しました\nステータスコード: {r.status_code}\nエラー内容: {json.dumps(json.loads(r.content), indent=2)}'
            except Exception as e:
                return False, f'LINE Notify APIでエラーが発生しました\nステータスコード: {r.status_code}\nエラー内容: []'

        return True, ''

    def zaiko_csv(self, company, stock_code, stock_num, csv_name = None):
        '''
        在庫情報をCSVで出力する

        Args:
            company(str): 証券会社名
            stock_code(str): 証券コード
            stock_num(int): 在庫数
            csv_name(str): CSVファイル名 ※省略可
                省略時は、{証券会社名}_zaiko_{年月}.csv

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ

        '''
        today = datetime.today()
        today_date = today.strftime('%Y%m%d')
        year_month = today.strftime('%Y%m')
        next_month = (today.replace(day = 28) + pd.DateOffset(days = 4)).strftime('%Y%m')
        data_folder = '../data'

        if csv_name == None:
            # ファイル名の指定がない場合
            # 受け渡しの2営業日分のズレを鑑みて2か月分のファイルに出力する
            file_names = [f'{data_folder}/{company}_zaiko_{year_month}.csv', f'{data_folder}/{company}_zaiko_{next_month}.csv']
        else:
            # ファイル名の指定がある場合
            if '.csv' in csv_name:
                file_names = [f'{data_folder}/{company}_{csv_name}']
            else:
                file_names = [f'{data_folder}/{company}_{csv_name}.csv']

        try:
            for file_name in file_names:
                # ファイル存在チェック
                if os.path.exists(file_name):
                    df = pd.read_csv(file_name)
                else:
                    df = pd.DataFrame(columns=['stock_code', today_date])

                # 今日の日付のカラムがなかったらデフォルト値を9として追加
                if today_date not in df.columns:
                    df[today_date] = -9

                # stock_codeカラムがintとして読み込まれてしまってる可能性があるのでstr型と明示する
                df['stock_code'] = df['stock_code'].astype(str)

                # 指定した証券コードの行がない場合はデフォルト値は9として挿入する
                add_flag = False
                if not np.any(df['stock_code'] == stock_code):
                    new_row = pd.DataFrame([[stock_code] + [-9] * (len(df.columns) - 1)], columns = df.columns)
                    df = pd.concat([df, new_row], ignore_index = True)
                    add_flag = True

                # 在庫数の挿入
                df.loc[df['stock_code'] == stock_code, today_date] = stock_num

                # 行が追加されていたらstock_codeカラムを昇順で並べ直す
                if add_flag:
                    df = df.sort_values(by = 'stock_code').reset_index(drop = True)

                # CSV出力
                df.to_csv(file_name, index = False)
        except Exception as e:
                return False, f'在庫情報のCSV出力に失敗しました\n{e}'

        return True, None

    def send_gmail(self, from_address, from_pass, to_address, subject, body):
        '''
        Gmailからメールを送信する

        Args:
            from_address(str): 送信元メールアドレス
            from_pass(str): 送信元メールアドレスのパスワード(外部連携用=アプリパスワード)
            to_address(str): 送信先メールアドレス
            subject(str): 件名
            body(str): 本文

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ
        '''
        # SMTPサーバーの設定
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587

        # メールの作成
        msg = MIMEMultipart()
        msg['From'] = from_address
        msg['To'] = to_address
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # SMTPサーバーに接続してメールを送信
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(from_address, from_pass)
            text = msg.as_string()
            server.sendmail(from_address, to_address, text)
            return True, None
        except Exception as e:
            return False, str(e)
        finally:
            server.quit()

class Log():
    '''
    loggerの設定を簡略化
        ログファイル名は呼び出し元のファイル名
        出力はINFO以上のメッセージのみ

    Args:
        output(int):出力タイプを指定
                    0:ログのみ出力、1:コンソールのみ出力、空:両方出力

    '''
    def __init__(self, filename = '', output = None):
        self.logger = logging.getLogger()
        self.output = output
        self.filename = filename
        self.today = self.now().strftime("%Y%m%d")
        self.set()

    def set(self):
        # 重複出力防止処理 / より深いファイルをログファイル名にする
        for h in self.logger.handlers[:]:
            # 起動中ログファイル名を取得
            log_path = re.search(r'<FileHandler (.+) \(INFO\)>', str(h))
            # 出力対象/占有ロックから外す
            self.logger.removeHandler(h)
            h.close()
            # ログファイルの中身が空なら削除
            if log_path != None:
                if os.stat(log_path.group(1)).st_size == 0:
                    os.remove(log_path.group(1))

        # フォーマットの設定
        formatter = logging.Formatter(f'%(asctime)s ({os.getpid()})  [%(levelname)s] %(message)s')

        # 出力レベルの設定
        self.logger.setLevel(logging.INFO)

        # ログ出力設定
        if self.output != 1:
            # リポジトリのルートフォルダを指定
            log_folder = os.path.join(os.path.dirname(__file__), '..', 'log')
            # ログフォルダチェック。無ければ作成
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)
            # 出力先を設定
            handler = logging.FileHandler(filename = os.path.join(log_folder, f'{self.now().strftime("%Y%m%d")}.log'), encoding = 'utf-8')
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.logger.addHandler(handler)

        # コンソール出力設定
        if self.output != 0:
            # ハンドラの設定
            handler = logging.StreamHandler(sys.stdout)
            # 出力レベルを設定
            handler.setLevel(logging.INFO)
            # フォーマットの設定
            handler.setFormatter(formatter)
            # ハンドラの適用
            self.logger.addHandler(handler)

    def date_check(self):
        '''日付変更チェック'''
        date = self.now().strftime("%Y%m%d")
        if self.today != date:
            self.today = date
            # PG起動中に日付を超えた場合はログ名を設定しなおす
            self.set()

    def now(self):
        '''現在のJSTを取得'''
        return datetime.utcnow() + timedelta(hours = 9)

    def debug(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.debug(f'{message} [{file_name} in {line}]')

    def info(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.info(f'{message} [{file_name} in {line}]')

    def warning(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.warning(f'{message} [{file_name} in {line}]')

    def error(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.error(f'{message} [{file_name} in {line}]')

    def critical(self, message):
        self.date_check()
        file_name, line = self.call_info(inspect.stack())
        self.logger.critical(f'{message} [{file_name} in {line}]')

    def call_info(self, stack):
        '''
        ログ呼び出し元のファイル名と行番号を取得する

        Args:
            stack(list): 呼び出し元のスタック

        Returns:
            os.path.basename(stack[1].filename)(str): 呼び出し元ファイル名
            stack[1].lineno(int): 呼び出し元行番号

        '''
        return os.path.basename(stack[1].filename), stack[1].lineno