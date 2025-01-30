import math
import re
from bs4 import BeautifulSoup

class Get():
    '''SMBC日興証券から情報を取得する'''

    def __init__(self, log):
        '''
        Args:
            log(Log): カスタムログ

        '''
        self.log = log

    def stock_num(self, session, page_no = '1', output_type = '0'):
        '''
        SMBC日興証券の一般信用売の在庫数を取得する

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            page_num(int or str): ページ番号
            output_type(int or str): 銘柄コードの上1桁で絞り込むか
                0: 絞り込みをしない、1: 1000番台のみ表示、2: 2000番台のみ表示...

        Returns:
            stock_list(list[dict{},dict{}...]): 各銘柄の一般信用売在庫情報
                stock_num(str): 銘柄コード
                stock_name(str): 銘柄名
                stock_num(str): 在庫数(0は取扱はあるが在庫なし、-1は非貸借銘柄など未取扱の銘柄)

        '''

        # 検索対象の絞り込み
        # 基本的には一般信用売しか見ないので、ページ数・証券コード上1桁絞り込み以外のパラメータは固定(必要になったら拡張)
        search_info = {
            'search': '1',
            'searchmeig': '',                 # 銘柄名・銘柄コード検索ワード
            'seidokai': '0',                  # 制度信用買がある銘柄
            'seidouri': '0',                  # 制度信用売がある銘柄
            'ipankai': '0',                   # 一般信用買がある銘柄
            'ipanuri': '1',                   # 一般信用売がある銘柄
            'tse1': '1',                      # 東証プライムの銘柄
            'tse2': '1',                      # 東証スタンダードの銘柄
            'tse3': '1',                      # 東証グロースの銘柄
            'nse1': '1',                      # 名証プレミアの銘柄
            'nse2': '1',                      # 名証メインの銘柄
            'nse3': '1',                      # 名証ネクストの銘柄
            'bottonSyubetu': '1',             # 並び順、1: 銘柄コード順、2: 銘柄名順
            'meigCdJyun': str(output_type),   # 銘柄コード順の場合、全銘柄かx000番台のみ表示か。0: 全銘柄、1: 1000番台、...
            'meigNmJyun': '0',                # 銘柄名順の場合、全銘柄かあ行のみ表示か。0: 全銘柄、1: あ行、2:か行、...11: その他
            'pageno': page_no                 # ページ番号
        }

        try:
            r = session.post('https://trade.smbcnikko.co.jp/StockOrderConfirmation/hoge/sinyo/meig/toriichiran', data = search_info)
        except:
            self.log.error('接続に失敗')
            return False

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        soup = BeautifulSoup(r.content, 'html.parser')

        # セッション切れ
        if 'NOL11007E' in soup.text:
            self.log.error('未ログイン/セッション切れでのエラー')
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

                        stock_info = {}
                        tds = tr.find_all('td')
                        stock_info['stock_code'] = tds[0].text.replace('\n', '').replace('\t', '').replace('\r', '')
                        stock_info['stock_name'] = tds[1].text.replace('\n', '').replace('\u3000', '')
                        stock_info['stock_num'] = int(tds[6].text.replace('株', '').replace(',', '').replace('-', '-1').replace('\n', ''))
                        stock_list.append(stock_info)

        return stock_list

    def subject_num(self, session, output_type = '0'):
        '''
        在庫取得対象の件数／ページ数を取得する

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            output_type(int or str): 証券コードの上1桁で絞り込むか
                0: 絞り込みをしない、1: 1000番台のみ表示、2: 2000番台のみ表示...

        Returns:
            total_num(int): 対象件数
            pages(int): 対象ページ数

        '''

        # 検索対象の絞り込み
        # 現在使えるフィルタリングは証券コードの上1桁の数値。必要になればフィルタリング可能条件を拡張する
        search_info = {
            'search': '1',
            'searchmeig': '',                # 銘柄名・銘柄コード検索ワード
            'seidokai': '0',                 # 制度信用買がある銘柄
            'seidouri': '0',                 # 制度信用売がある銘柄
            'ipankai': '0',                  # 一般信用買がある銘柄
            'ipanuri': '1',                  # 一般信用売がある銘柄
            'tse1': '1',                     # 東証プライムの銘柄
            'tse2': '1',                     # 東証スタンダードの銘柄
            'tse3': '1',                     # 東証グロースの銘柄
            'nse1': '1',                     # 名証プレミアの銘柄
            'nse2': '1',                     # 名証メインの銘柄
            'nse3': '1',                     # 名証ネクストの銘柄
            'bottonSyubetu': '1',            # 並び順、1: 銘柄コード順、2: 銘柄名順
            'meigCdJyun': str(output_type),  # 銘柄コード順の場合、全銘柄かx000番台のみ表示か。0: 全銘柄、1: 1000番台、...
            'meigNmJyun': '0',               # 銘柄名順の場合、全銘柄かあ行のみ表示か。0: 全銘柄、1: あ行、2:か行、...11: その他
            'pageno': '1'                    # ページ番号
        }

        try:
            r = session.post('https://trade.smbcnikko.co.jp/StockOrderConfirmation/hoge/sinyo/meig/toriichiran', data = search_info)
        except:
            self.log.error('接続に失敗')
            return False, False

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False, False

        soup = BeautifulSoup(r.content, 'html.parser')

        # セッション切れ
        if 'NOL11007E' in soup.text:
            self.log.error('未ログイン/セッション切れでのエラー')
            return False, False

        # 検索した銘柄が存在しない場合
        if '現在お取扱中の銘柄はございません。' in soup.text:
            self.log.info('対象銘柄は存在しませんでした')
            return 0, 0

        # 件数取得
        search = re.search('([\d,]+)件中.+?([\d,]+)件表示', soup.text)
        if search is None:
            self.log.error('対象件数の取得が行えませんでした')
            return False, False

        # 1ページ当たりの表示件数、全件数
        total_num, per_page = int(search.groups()[0].replace(',', '')), int(search.groups()[1].replace(',', ''))

        return total_num, math.ceil(total_num / per_page)

    def order_input(self, session, stock_code):
        '''
        一般売注文情報入力画面のHTMLを取得する

        Args:
            session(requests.sessions.Session): ログイン状態のセッション
            stock_code(str): 証券コード

        Returns:
            html(bs4.BeautifulSoup) or False

        '''

        try:
            r = session.get(f'https://trade.smbcnikko.co.jp/OdrMng/000000000000/sinyo/tku_odr/init?meigCd=00{stock_code}0000&specifyMeig=1&sinyoToriKbn=1')
        except Exception as e:
            self.log.error(f'接続に失敗\n{e}')
            return False

        if r.status_code != 200:
            self.log.error(f'接続に失敗 ステータスコード: {r.status_code}')
            return False

        soup = BeautifulSoup(r.content, 'html.parser')

        # 正常に取得できたかチェック
        if 'お客様名:' not in soup.text:
            self.log.error('一般売注文情報入力画面の取得に失敗')
            # セッション切れエラー
            if 'NOL11007E' in soup.text:
                self.log.error('未ログイン/セッション切れでのエラー')
                return False
            self.log.error('原因不明なエラー')
            return False

        return soup