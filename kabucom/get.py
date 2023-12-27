import time
from bs4 import BeautifulSoup

class Get():
    '''auカブコム証券から情報を取得する'''

    def stock_num(self, session):
        '''
        auカブコムの一般信用売の在庫数を取得する

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            stock_code_list(list[int,int...]): 取得対象の証券コードのリスト

        Returns:
            stock_data(list[dict,dict...]) 各証券コードの取得データ
                num(int): 一般信用売り在庫数
                premium(float): プレミアム料
        '''

        '''
        パラメータ
            conditions = {
                'Keyword': ''
                'FilterMarginType.Value': 'ALL'
                'FilterBackwardation.Value': 'ALL'
                'FilterSpecialBenefit.Value': 'ALL'
                'FilterPremium.Value': 'ALL',
                'FilterAvailableOnly': false
                'FilterFavoriteOnlyCh': true
                'FilterFavoriteOnly': false
                'BenefitMonth': 0
                'market': 0
                'search.x': 62
                'search.y': 19
                'PageNo': 1
                'ReadSortType':'Brand'
                'SortType.Value':'Brand'
            }
        '''

        try:
            r = session.get('https://s20.si0.kabu.co.jp/ap/pc/Stocks/Margin/MarginSymbol/GeneralSellList?PageNo=1')
        except:
            print('接続に失敗')
            return False

        if r.status_code != 200:
            print(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        soup = BeautifulSoup(r.content, 'html.parser')

        # ログインができていない
        if '口座番号とパスワードを入力してログインしてください' in soup.text:
            print('ログインできてない')
            return False

        # 大引け~19:30までは在庫数が表示されない
        if '※翌営業日分' in soup.text:
            print('対象時間外')
            return False

        # TODO データをdictにする処理
        return True



    def _stock_num(self, session, stock_code_list):
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
