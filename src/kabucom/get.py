import time
from bs4 import BeautifulSoup

class Get():
    '''auカブコム証券から情報を取得する'''

    def stock_num(self, session, page_no = 1):
        '''
        auカブコムの一般信用売の在庫数を取得する

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            page_no(int): ページ番号

        Returns:
           stock_list(list[dict{},dict{}...]): 各銘柄の一般信用売在庫情報
                stock_num(int): 銘柄コード
                stock_name(str): 銘柄名
                stock_num(int): 在庫数(0は取扱はあるが在庫なし、-1は非貸借銘柄など未取扱の銘柄)
                premium(float): 1株あたりのプレミアム料
        '''

        search_info = {
            'Keyword': '',                        # 銘柄名・銘柄コード検索ワード
            'FilterMarginType.Value': 'LONG',     # 空売り種別 LONG: 長期、DAY: デイトレ、ALL: 長期&デイトレ
            'FilterBackwardation.Value': 'ALL',   # 逆日歩有無 ARI: あり、NASHI: なし、ALL: 両方
            'FilterSpecialBenefit.Value': 'ARI',  # 優待有無 ARI: あり、NASHI: なし、ALL: 両方
            'FilterPremium.Value': 'ALL',         # プレミアム料 ARI: あり、NASHI: なし、ALL: 両方
            'FilterAvailableOnly': False,         # 注文可能銘柄のみか True: 注文可能銘柄のみ、False: 全て
            'FilterFavoriteOnly': False,          # お気に入り登録銘柄のみか True: お気に入り登録銘柄のみ、False: 全て
            'BenefitMonth': '0',                  # 権利確定月 0: 指定なし、1: 1月、...、12: 12月
            'market': '0',                        # 市場 0: 指定なし、13: 東証プライム、1A: 東証スタンダード、1B: 東証グロース、3: 名古屋
            'PageNo': page_no,                    # ページ番号
            'SortType.Value': 'Brand'             # 並び順 SymbolCodeUnit: 銘柄コード1000番ごと、Brand: 銘柄コード昇順で100件ごと 以下割愛
        }

        try:
            r = session.post('https://s20.si0.kabu.co.jp/ap/pc/Stocks/Margin/MarginSymbol/GeneralSellList', data = search_info)
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
        # TODO この間の時間にアクセスをかけてみてチェック
        #if 'TODO' in soup.text:
        #    print('対象時間外')
        #    return False

        # TODO 抽選予約中の時間(19:30~20:30)の予約状況のテーブルと注文可能時間で(20:30~翌営業日大引け)の取得ロジックで切り替える
        # とりあえず今は後者のみ実装

        table_count = 0
        stock_list = []

        # ページ内のテーブルを一つずつ取得
        for table in soup.find_all('table'):
            # 在庫情報のテーブルにのみ記載のある文字列の場合のみ取得
            if '(在庫株数量)(株(口))' in table.text:
                table_count += 1

                # 三重テーブルになっているので一番内側のテーブルの場合のみ詳細データの抜き出しを行う
                if table_count == 3:
                    for index, tr in enumerate(table.find_all('tr')):
                        # 1行目はヘッダーなのでスルー
                        if index == 0: continue

                        stock_info = {}
                        tds = tr.find_all('td')
                        stock_info['stock_code'] = int(tds[0].text.replace('\n', '').replace(' ', '').replace('\r', ''))
                        stock_info['stock_name'] = tds[1].text.replace('\n', '').replace('\u3000', '')
                        stock_info['stock_num'] = int(tds[3].text.replace(' ', '').replace('株', '').replace(',', '').replace('\n', '').replace('\r', '').replace('残数量なし', '0'))
                        stock_info['premium'] = float(tds[4].text.replace(' ', '').replace('\n', '').replace('\r', '').replace('-', '0.00'))
                        stock_list.append(stock_info)

        return stock_list
