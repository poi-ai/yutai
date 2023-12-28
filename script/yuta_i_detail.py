import requests
import lxml
import sys
from bs4 import BeautifulSoup

### みんかぶから優待の詳細情報を取得するスクリプト
### コマンドライン引数に証券コードを記載して実行すると

stock_code = sys.argv[1]

r = requests.get(f'https://minkabu.jp/stock/{stock_code}/yutai')
soup = BeautifulSoup(r.content, 'lxml')
try:
    print(soup.find('div', class_='md_card md_box ly_content_wrapper size_ss').text.replace('\n\n', '\n').rstrip("\n"))
except AttributeError as e:
    print('指定された証券コードの銘柄の優待は存在しません')