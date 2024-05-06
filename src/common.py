import csv
import logging
import inspect
import json
import os
import sys
import re
import requests
from datetime import datetime, timedelta

class Output():
    def __init__(self, log):
        self.log = log

    def output_csv(self, data, file_name, add_header = True, add_time = True):
        '''
        dict型のデータをCSVへ出力する

        Args:
            data(list[dict{},dict{},...]): dictで保持されているデータのlist
            file_name(str): 出力するCSVのファイル名
            add_header(bool): ヘッダー行を追加するか、file_nameのCSVが既に存在する場合は無視される
            add_time(bool): 出力するCSVに時間情報を付けるか
        '''

        # 時間のカラムを追加する
        if add_time:
            data = self.add_time(data)

        # ファイル名の引数に.csvが書かれていなかった場合の救済
        if not '.csv' in file_name:
            file_name = f'{file_name}.csv'

        # dataディレクトリに格納するためのパスを指定
        file_path = f'../data/{file_name}'

        # 既に引数のファイルが存在する場合は追記、そうでない場合は上書き（新規作成）
        mode = 'a' if os.path.exists(file_path) else 'w'

        with open(file_path, mode, encoding = 'UTF-8', newline = '') as csvfile:
            fieldnames = data[0].keys() if data else []
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if mode == 'w' and add_header:
                writer.writeheader()

            for row in data:
                writer.writerow(row)

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
            handler = logging.FileHandler(filename = os.path.join(log_folder, f'{self.now().strftime("%Y%m")}.log'), encoding = 'utf-8')
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