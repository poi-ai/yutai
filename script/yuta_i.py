import time
import requests
import re
import unicodedata
import lxml
from bs4 import BeautifulSoup

### みんかぶから指定した月の優待情報をまとめて取得しCSVに書き出すスクリプト ###
### 下記に取得したい月を入力 ###
month = 8

for page in range(1, 100):
    time.sleep(2)

    r = requests.get(f'https://minkabu.jp/yutai/popular_ranking/total?month={month}&page={page}')
    soup = BeautifulSoup(r.content, 'lxml')

    # ページ送りで存在しない=これ以上優待情報がない場合はここでストップ
    if 'URLが間違っているか、ページが削除された可能性があります。' in soup.text:
        print(f'取得ページ数:{page - 1}')
        exit()

    month_list = []
    # 権利確定付きを取得
    for target_month in soup.find_all('span', class_='dpib fsize_sss fcgl'):
        month_list.append(target_month.text.replace('権利確定', '').replace('月', '').replace(',', '&').replace('優待', ''))

    index = 0
    for data in soup.find_all('div', class_='ly_col ly_colsize_9'):
        # 廃止済みチェック
        if '廃止されました' in data.text:
            continue

        # 各優待ごとに情報を取得
        stock_data = re.search('(.+)\((.+)\)', str(data.find('a').text.lstrip()))
        stock_name, stock_code = stock_data.groups()

        # 文字数短縮
        stock_name = unicodedata.normalize('NFKC', stock_name).replace('ホールディングス', 'HD')

        # 必要最低金額・株数を取得
        price_list =  data.find_all('span', class_='fwb')
        min_price = price_list[0].text
        min_num = price_list[1].text.replace(',', '')

        # 優待商品種別を取得
        item_name = data.find('div', class_='yutai_item w350p fwb').text

        # ファイルに出力
        with open(f'../yutai_2024{str(month).zfill(2)}.csv', mode = 'a', encoding = 'UTF-8') as f:
            f.write(f'{stock_code},{stock_name},{min_price},{month_list[index]},{min_num},{item_name}\n')

        index += 1



