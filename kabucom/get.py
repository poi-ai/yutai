import requests
import time
import lxml
import login
from bs4 import BeautifulSoup

def stock(session, stock_code_list):
    '''
    auカブコムの一般信用の在庫数を取得する

    Args:
        session(requests.Session): セッション
        stock_code_list(list[int,int...]): 取得対象の証券コードのリスト

    Returns:
        stock_data(list[dict,dict...]) 各証券コードの取得データ
            num(int): 一般信用売り在庫数
            premium(float): プレミアム料
    '''
    base_url = 'https://s20.si0.kabu.co.jp/ap/pc/Stocks/Margin/MarginSymbol/GeneralSellList?PageNo='

    if len(stock_code_list) == 0: return


    # 在庫情報は1000番ごとにページ数が異なる
    for page in (1, 10):
        # 1000番ごとに取得
        target_stock = [v for v in stock_code_list if 1000 * page <= v <= 1000 * page + 999]

        # 対象なしならスキップ
        if len(target_stock) == 0: continue

        # HTMLを取得
        time.sleep(2)
        r = session.get(f'{base_url}{page}')
        print(f'{base_url}{page}')
        soup = BeautifulSoup(r.content, 'lxml')
        print(soup.text)


if __name__ == '__main__':
    stock([1005])