import csv
import logging
import inspect
import json
import numpy as np
import os
import pandas as pd
import sys
import topix
import re
import requests
from datetime import datetime, timedelta

class Output():
    def __init__(self, log):
        self.log = log
        self.culc = Culc()
        self.notify_token = ''
        self.messaging_api_token = ''

    def output_csv(self, data, file_name, add_header = True, add_time = True, data_folder = True, mode = None):
        '''
        dict型のデータをCSVへ出力する

        Args:
            data(list[dict{},dict{},...] or list): 出力をするデータ
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
                self.log.info(f'削除対象のCSVがありません')
                return False
        except Exception as e:
            self.log.error(f'CSVの削除処理に失敗しました')
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

    def set_notify_token(self, token):
        '''
        LINE Notifyのアクセストークンを設定する

        Args:
            token(str): LINE Notifyのアクセストークン

        '''
        self.notify_token = token
        return

    def set_messaging_api_token(self, token):
        '''
        LINE Messaging APIのアクセストークンを設定する

        Args:
            token(str): LINE Messaging APIのアクセストークン

        '''
        self.messaging_api_token = token
        return

    def line(self, message):
        '''
        LINEを用いてメッセージを送信する

        Args:
            message(str) : LINE送信するメッセージ内容

        Returns:
            result(bool): 実行結果
            error_message(str): エラー内容

        '''

        # インスタンス変数に設定されているアクセストークンからMessaging APIを用いるかNotifyを用いるか判定する
        # 優先はMessaging API
        if self.messaging_api_token != '':
            return self.send_messaging_api(message)
        elif self.notify_token != '':
            return self.send_notify(message)
        else:
            return False, f'LINE Messaging API、Notifyどちらのトークンも設定されていないためメッセージが送信できません\n送信メッセージ: {message}'

    def send_messaging_api(self, message_list):
        '''
        LINE Messaging APIのブロードキャストを用いてメッセージを送信する
        TODO いずれUUIDを用いたプッシュメッセージにしたい

        Args:
            message_list(list[str, str...]) : LINE送信するメッセージ内容

        Returns:
            result(bool): 実行結果
            error_message(str): エラー内容

        '''

        # ヘッダー設定
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.messaging_api_token}'
        }

        # メッセージを吹き出しごとに設定
        messages = []
        for message in message_list:
            messages.append({
                'type': 'text',
                'text': message
            })

        # ペイロード
        data = {
            'messages': messages
        }

        # メッセージ送信
        try:
            r = requests.post('https://api.line.me/v2/bot/message/broadcast', headers = headers, json = data)
        except Exception as e:
            return False, f'LINE Messaging APIでのメッセージ送信に失敗しました\n{e}'

        if r.status_code != 200:
            try:
                return False, f'LINE Messaging APIのメッセージ送信でエラーが発生しました\nステータスコード: {r.status_code}\nエラー内容: {json.dumps(json.loads(r.content), indent=2)}'
            except Exception as e:
                return False, f'LINE Messaging APIのメッセージ送信で発生しました\nエラー内容: {e}'

        return True, ''


    def send_notify(self, message):
        '''
        LINE Notifyを用いてメッセージを送信する

        Args:
            message(str) : LINE送信するメッセージ内容

        Returns:
            result(bool): 実行結果
            error_message(str): エラー内容

        '''

        # ヘッダー設定
        headers = {'Authorization': f'Bearer {self.notify_token}'}

        # メッセージ設定
        data = {'message': message}

        # メッセージ送信
        try:
            r = requests.post('https://notify-api.line.me/api/notify', headers = headers, data = data)
        except Exception as e:
            return False, f'LINE Notify APIでのメッセージ送信に失敗しました\n{e}'

        if r.status_code != 200:
            try:
                return False, f'LINE Notify APIでエラーが発生しました\nステータスコード: {r.status_code}\nエラー内容: {json.dumps(json.loads(r.content), indent=2)}'
            except Exception as e:
                return False, f'LINE Notify APIでエラーが発生しました\nエラー内容: {e}'

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

    def owarine_csv(self, stock_code, upper_price, owarine_info):
        '''
        終値と翌営業日の高値を記録するCSVファイルに出力を行う

        Args:
            stock_code(str): 証券コード
            upper_price(float): 翌営業日の高値
            owarine_info(list[str, str]): 終値データ([終値,日付])

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ ※エラー時のみ
        '''
        filename = 'owarine.csv'
        header = ['stock_code', 'owarine', 'yoku_sdaka', 'yoku_date']

        # 現在の日付を取得し、月日を終値の営業日に置き換える
        today = datetime.now()
        month_day = owarine_info[1]
        month, day = map(int, month_day.split('/'))

        # 月日を現在の年に設定、ただし年跨ぎの場合は前年に設定
        if today.month == 1 and month == 12:
            year = today.year - 1
        else:
            year = today.year
        year_month_day = datetime(year, month, day)

        # 前営業日の次の営業日を算出
        next_trade_day = self.culc.next_exchange_workday(year_month_day).strftime('%Y/%m/%d')

        new_data = [stock_code, owarine_info[0], upper_price, next_trade_day]

        # CSVファイルが存在する場合はデータを読み込み
        if os.path.isfile(filename):
            with open(filename, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)

            # ヘッダー行を取り出し、データ行を分ける
            existing_header = rows[0]
            data_rows = rows[1:] if len(rows) > 1 else []

            # stock_codeに基づいて行を更新または追加
            found = False
            for i, row in enumerate(data_rows):
                if row and row[0] == str(stock_code):
                    data_rows[i] = new_data
                    found = True
                    break
            if not found:
                data_rows.append(new_data)
        else:
            # ファイルが存在しない場合は、新たにデータを追加
            existing_header = header
            data_rows = [new_data]

        # stock_codeで昇順にソート
        data_rows.sort(key=lambda x: x[0])

        # CSVファイルに書き込む
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(existing_header)  # ヘッダー行を先に書き込む
            writer.writerows(data_rows)  # データ行をその後に書き込む

        return True, None

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
        self.today_ym = self.now().strftime("%Y%m")
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

class Culc():
    def culc_upper_price(self, stock_code, price):
        '''
        指定した株価から翌営業日の高値を返す

        Args:
            stock_code(str): 証券コード
            price(float): 前営業日の終値

        Returns:
            upper_price(float): 翌営業日の高値
        '''

        # 現在値と値幅
        thresholds = [
            (100, 30),
            (200, 50),
            (500, 80),
            (700, 100),
            (1000, 150),
            (1500, 300),
            (2000, 400),
            (3000, 500),
            (5000, 700),
            (7000, 1000),
            (10000, 1500),
            (15000, 3000),
            (20000, 4000),
            (30000, 5000),
            (50000, 7000),
            (70000, 10000),
            (100000, 15000),
            (150000, 30000),
            (200000, 40000),
            (300000, 50000),
            (500000, 70000),
            (700000, 100000),
            (1000000, 150000)
        ]

        # 小さい順に辿っていき、値幅を取得する
        add_price = 0
        for threshold, limit_width in thresholds:
            if price < threshold:
                add_price = limit_width
                break
        else:
            add_price = thresholds[-1][1]

        # 価格(終値)に値幅を加算
        upper_price = price + add_price

        # 呼値次第では正しくない値が入る場合があるので修正が必要
        # 例: 999円+50円(値幅)=1049円ではダメで呼値が5円なので1045円でないといけない

        # 銘柄種別チェック
        topix_flag = str(stock_code) in topix.TOPIX_500

        # 注文可能な価格の中で、値幅加算額と同じか満たない中での最高値の取得
        correct_price = self.check_correct_price(price, upper_price, topix_flag)

        # int変換可能なら変換
        if isinstance(correct_price, float) and correct_price.is_integer():
            return int(correct_price)
        return correct_price

    def check_correct_price(self, low_price, check_price, topix_flag):
        '''
        指定した銘柄の株価が注文可能な価格かチェックする

        Args:
            low_price(float): チェック対象の株価より低い株価で注文可能な価格
            check_price(float): チェック対象の株価
            topix_flag(bool): TOPIX 500構成銘柄か

        Returns:
            result(bool): 実行結果
            error_message(str): エラーメッセージ
        '''

        price_list = [low_price]
        now_price = low_price

        while True:
            # 基準価格の呼値を取得
            yobine = self.get_price_range(topix_flag, now_price)

            # 基準価格 + 呼値を計算してリストに挿入
            next_price = now_price + yobine

            # 丸め誤差修正
            next_price = self.polish_price(next_price)

            # 超えた場合は1つ前の正しい値を返す
            if next_price > check_price:
                return price_list[-1]
            elif next_price == check_price:
                return next_price
            else:
                price_list.append(next_price)
                now_price = next_price

    def get_price_range(self, topix_flag, price):
        '''
        指定した銘柄の呼値を取得する

        Args:
            topix_flag(bool): TOPIX 500構成銘柄か
            price(float): 判定したい株価

            price_range(float) or False: 呼値
        '''

        price_ranges = {
            True: [
                (1000, 0.1), (3000, 0.5), (10000, 1), (30000, 5), (100000, 10),
                (300000, 50), (1000000, 100), (3000000, 500), (10000000, 1000),
                (30000000, 5000), (float('inf'), 10000)
            ],
            False: [
                (3000, 1), (5000, 5), (30000, 10), (50000, 50), (300000, 100),
                (500000, 500), (3000000, 1000), (5000000, 5000), (30000000, 10000),
                (50000000, 50000), (float('inf'), 100000)
            ]
        }

        for limit, range_value in price_ranges[topix_flag]:
            if price + 0.1 <= limit:
                return range_value

        return False

    def polish_price(self, price):
        '''
        価格計算結果の丸め誤差を修正する

        Args:
            price(int or float): 修正対象の株価

        Return:
            accurate_price(int or float): 正確な株価
        '''
        # 丸め誤差修正
        accurate_price = round(price, 1)

        # データ型修正
        # int変換可能な値の場合は変換する
        if isinstance(accurate_price, float) and accurate_price.is_integer():
            accurate_price = int(accurate_price)

        return accurate_price


    def next_exchange_workday(self, date):
        '''
        指定した日の翌取引所営業日を返す

        Args:
            date(datetime): 指定日

        Returns:
            next_date(datetime): 指定日の翌取引所営業日
        '''
        while True:
            next_date = date + timedelta(days = 1)

            # 取引所営業日判定
            result = self.is_exchange_workday(next_date)

            # 取引営業日ならその日付を返す
            if result:
                return next_date

            date = next_date

    def previous_exchange_workday(self, date):
        '''
        指定した日の前取引所営業日を返す

        Args:
            date(datetime): 指定日

        Returns:
            previous_date(datetime): 指定日の前取引所営業日
        '''
        while True:
            previous_date = date - timedelta(days = 1)

            # 取引所営業日判定
            result = self.is_exchange_workday(previous_date)

            # 取引営業日ならその日付を返す
            if result:
                return previous_date

            date = previous_date

    def is_exchange_workday(self, date):
        '''
        指定した日が取引所の営業日かの判定を行う

        Args:
            date(datetime): 判定対象の日

        Returns:
            bool: 判定結果
                True: 営業日、False: 非営業日
        '''

        # 土日祝日かの判定を行う
        result = self.is_workday(date)

        # 土日・祝日の場合
        if result == False:
            return False

        # 取引所の営業日の判定を行う
        if self.is_exchange_holiday(date):
            return False

        return True

    def is_workday(self, date):
        '''
        指定した日が営業日かの判定を行う

        Args:
            date(datetime): 判定対象の日

        Returns:
            bool: 判定結果
                True: 営業日、False: 非営業日

        '''

        # 土日判定
        if date.weekday() in [5, 6]:
            return False

        # 祝日判定
        if self.is_holiday(date):
            return False

        return True

    def is_holiday(self, date):
        '''
        指定した日が祝日かの判定を行う

        Args:
            date(datetime): 判定対象の日

        Returns:
            bool: 判定結果
                True: 祝日、False: 非祝日

        '''
        # 祝日のリストの取得
        until_year, holiday_list = self.get_holiday_list()

        # 指定した年が対応しているか
        if int(date.strftime('%Y')) <= until_year:
            # 対応している場合 祝日リストに入っているか
            return date.strftime('%Y%m%d') in holiday_list
        else:
            # 対応していない場合はAPIから取得
            holiday_list = self.holidays_jp_api()
            # TODO リストからチェックする処理 2030年までに対応

    def get_holiday_list(self):
        '''祝日を列挙したリスト

        Returns:
            until_year(int): 記載のある最後の年
            holiday_list(list): 祝日のリスト
        '''
        return 2030, {
            '20250211','建国記念の日',
            '20250223','天皇誕生日',
            '20250224','振替休日',
            '20250320','春分の日',
            '20250429','昭和の日',
            '20250503','憲法記念日',
            '20250504','みどりの日',
            '20250505','こどもの日',
            '20250506','振替休日',
            '20250721','海の日',
            '20250811','山の日',
            '20250915','敬老の日',
            '20250923','秋分の日',
            '20251013','スポーツの日',
            '20251103','文化の日',
            '20251123','勤労感謝の日',
            '20251124','振替休日',
            '20260101','元日',
            '20260112','成人の日',
            '20260211','建国記念の日',
            '20260223','天皇誕生日',
            '20260320','春分の日',
            '20260429','昭和の日',
            '20260503','憲法記念日',
            '20260504','みどりの日',
            '20260505','こどもの日',
            '20260506','振替休日',
            '20260720','海の日',
            '20260811','山の日',
            '20260921','敬老の日',
            '20260922','国民の休日',
            '20260923','秋分の日',
            '20261012','スポーツの日',
            '20261103','文化の日',
            '20261123','勤労感謝の日',
            '20270101','元日',
            '20270111','成人の日',
            '20270211','建国記念の日',
            '20270223','天皇誕生日',
            '20270321','春分の日',
            '20270322','振替休日',
            '20270429','昭和の日',
            '20270503','憲法記念日',
            '20270504','みどりの日',
            '20270505','こどもの日',
            '20270719','海の日',
            '20270811','山の日',
            '20270920','敬老の日',
            '20270923','秋分の日',
            '20271011','スポーツの日',
            '20271103','文化の日',
            '20271123','勤労感謝の日',
            '20280101','元日',
            '20280110','成人の日',
            '20280211','建国記念の日',
            '20280223','天皇誕生日',
            '20280320','春分の日',
            '20280429','昭和の日',
            '20280503','憲法記念日',
            '20280504','みどりの日',
            '20280505','こどもの日',
            '20280717','海の日',
            '20280811','山の日',
            '20280918','敬老の日',
            '20280922','秋分の日',
            '20281009','スポーツの日',
            '20281103','文化の日',
            '20281123','勤労感謝の日',
            '20290101','元日',
            '20290108','成人の日',
            '20290211','建国記念の日',
            '20290212','振替休日',
            '20290223','天皇誕生日',
            '20290320','春分の日',
            '20290429','昭和の日',
            '20290430','振替休日',
            '20290503','憲法記念日',
            '20290504','みどりの日',
            '20290505','こどもの日',
            '20290716','海の日',
            '20290811','山の日',
            '20290917','敬老の日',
            '20290923','秋分の日',
            '20290924','振替休日',
            '20291008','スポーツの日',
            '20291103','文化の日',
            '20291123','勤労感謝の日',
            '20300101','元日',
            '20300114','成人の日',
            '20300211','建国記念の日',
            '20300223','天皇誕生日',
            '20300320','春分の日',
            '20300429','昭和の日',
            '20300503','憲法記念日',
            '20300504','みどりの日',
            '20300505','こどもの日',
            '20300506','振替休日',
            '20300715','海の日',
            '20300811','山の日',
            '20300812','振替休日',
            '20300916','敬老の日',
            '20300923','秋分の日',
            '20301014','スポーツの日',
            '20301103','文化の日',
            '20301104','振替休日',
            '20301123','勤労感謝の日'
        }

    def holidays_jp_api(self):
        '''
        Holidays JP APIから祝日情報を取得する

        Returns:
            holidays(dict): 実行日の前年～翌年までの祝日一覧

        '''
        try:
            r = requests.get('https://holidays-jp.github.io/api/v1/date.json')
        except Exception as e:
            return False, e

        if r.status_code != 200:
            # TODO インスタンス変数logが存在しないからエラー出る
            self.log.error(f'祝日情報取得APIエラー ステータスコード: {r.status_code}')
            return False, f'{r.status_code}\n{r.status_code}\n{json.loads(r.content)}'

        holidays = r.json()

        if len(holidays) == 0:
            self.log.error(f'祝日情報取得APIエラー レスポンス情報が空')
            return False

        return holidays

    def is_exchange_holiday(self, date):
        '''取引所が年末年始の休場日か'''

        # 1/1~1/3
        if date.month == 1 and date.day <= 3:
            return True

        # 12/31
        if date.month == 12 and date.day == 31:
            return True

        return False

    def exchange_time(self, now):
        '''
        指定した時間から取引時間の種別を判定する

        Args:
            now(datetime): 判定対象の時間 省略可

        Returns:
            time_type(int): 時間種別
                1: 前場取引時間、2: 後場取引時間(クロージング・オークション除く)、
                3: 取引時間外(寄り付き前)、4: 取引時間外(お昼休み)、5: 取引時間外(大引け後)、6: クロージング・オークション
        '''
        # 前場
        if 9 <= now.hour < 11 or (now.hour == 11 and now.minute < 30):
            return 1
        # クロージング・オークション
        elif 15 == now.hour and (25 <= now.minute < 30):
            return 6
        # 後場
        elif 12 < now.hour < 15 or (now.hour == 12 and now.minute >= 30) or (now.hour == 15 and now.minute < 25):
            return 2
        # 寄り前
        elif now.hour < 9:
            return 3
        # 引け後
        elif now.hour >= 15:
            return 5
        # お昼休み
        else:
            return 4