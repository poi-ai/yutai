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
        パラメータ TODO どんな値でどう変わるかチェック
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

        print(r.status_code)

        if r.status_code != 200:
            print(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        soup = BeautifulSoup(r.content, 'html.parser')

        # メンテンス中
        if 'メンテナンス中' in soup.text:
            print('メンテナンス中')

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
