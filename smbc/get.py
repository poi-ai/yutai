from bs4 import BeautifulSoup

class Get():
    '''SMBC日興証券から情報を取得する'''

    def stock_num(self, session, page_no = 1):
        '''
        SMBC日興証券の一般信用売の在庫数を取得する

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            page_num: ページ番号

        Returns:
            stock_list(list[dict{},dict{}...]): 各銘柄の一般信用売在庫情報
                stock_num(str): 銘柄コード
                stock_name(str): 銘柄名
                stock_num(str): 在庫数(0は取扱はあるが在庫なし、-1は非貸借銘柄など未取扱の銘柄)

        '''

        # 検索対象の絞り込み
        # 基本的には一般信用売しか見ないので、ページ数以外のパラメータは固定(必要になったら拡張)
        search_info = {
            'search': '1',
            'searchmeig': '',       # 銘柄名・銘柄コード検索ワード
            'seidokai': '0',        # 制度信用買がある銘柄
            'seidouri': '0',        # 制度信用売がある銘柄
            'ipankai': '0',         # 一般信用買がある銘柄
            'ipanuri': '1',         # 一般信用売がある銘柄
            'tse1': '1',            # 東証プライムの銘柄
            'tse2': '1',            # 東証スタンダードの銘柄
            'tse3': '1',            # 東証グロースの銘柄
            'nse1': '1',            # 名証プレミアの銘柄
            'nse2': '1',            # 名証メインの銘柄
            'nse3': '1',            # 名証ネクストの銘柄
            'bottonSyubetu': '1',   # 並び順、1: 銘柄コード順、2: 銘柄名順
            'meigCdJyun': '0',      # 銘柄コード順の場合、全銘柄かx000番台のみ表示か。0: 全銘柄、1: 1000番台、...
            'meigNmJyun': '0',      # 銘柄名順の場合、全銘柄かあ行のみ表示か。0: 全銘柄、1: あ行、2:か行、...11: その他
            'pageno': page_no       # ページ番号
        }

        try:
            r = session.post('https://trade.smbcnikko.co.jp/StockOrderConfirmation/hoge/sinyo/meig/toriichiran', data = search_info)
        except:
            print('接続に失敗')
            return False

        if r.status_code != 200:
            print(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        soup = BeautifulSoup(r.content, 'html.parser')

        # セッション切れ
        if 'NOL11007E' in soup.text:
            print('セッション切れ')
            return False

        # 検索した銘柄が存在しない場合
        if '現在お取扱中の銘柄はございません。' in soup.text:
            return []

        table_count = 0
        stock_list = []

        # ページ内の全テーブルを取得
        tables = soup.find_all('table')

        for table in tables:
            # 在庫情報のテーブルにのみ記載のある文字列の場合のみ取得
            if '銘柄ｺｰﾄﾞ' in table.text:
                table_count += 1
                # 三重テーブルになっているので一番内側のテーブルの場合のみ詳細データの抜き出しを行う
                if table_count == 3:
                    for index, tr in enumerate(table.find_all('tr')):
                        # 1, 2行目はヘッダーなのでパス
                        if index <= 1: continue
                        print(index)

                        stock_info = {}
                        tds = tr.find_all('td')
                        stock_info['stock_code'] = int(tds[0].text.replace('\n', '').replace('\t', '').replace('\r', ''))
                        stock_info['stock_name'] = tds[1].text.replace('\n', '').replace('\u3000', '')
                        stock_info['stock_num'] = int(tds[6].text.replace('株', '').replace(',', '').replace('-', '-1').replace('\n', ''))
                        stock_list.append(stock_info)

        return stock_list