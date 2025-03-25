import csv
import kabutan
import time
from main import Main
from datetime import datetime

class Owarine(Main):
    '''株探から終値を取得してCSVに記録する'''
    def __init__(self):
        super().__init__()
        self.kabutan = kabutan.Kabutan(self.log)

    def main(self):
        self.log.info('終値取得処理開始')
        steal_list = []

        # steal_listから終値をチェックする銘柄を取得する
        try:
            with open('steal_list.csv', 'r', newline = '', encoding = 'UTF-8') as csv_file:
                reader = csv.reader(csv_file)
                for row in reader:
                    steal_list.append(row[0])
        except Exception as e:
            self.log.error(f'steal_list.csvの取得でエラー\n{e}')
            return False

        ### 時間帯によって取得すべき位置が異なる
        ### 営業日 ~ 9:00(?)    : 前営業日の終値欄 → x(前々営業日の終値)、四本値の終値 → o(前営業日の終値) time_type = 3
        ### 営業日 9:00 ~ 15:30 : 前営業日の終値欄 → o                、四本値の終値 → x(ザラ場のため終値なし) time_type = 1,2,4,6
        ### 営業日 15:30 ~      : 前営業日の終値欄 → x(前営業日の終値)  、四本値の終値 → o(当日の終値) time_type = 5
        ### 非営業日            : 前営業日の終値欄 → x(前々営業日の終値)、四本値の終値 → o(前営業日の終値) time_type = 0

        # 営業日チェック
        now = datetime.now()
        if self.culc.is_exchange_workday(now):
            time_type = self.culc.exchange_time(now)
        else:
            time_type = 0

        self.log.info(f'取得対象銘柄数: {len(steal_list)}')

        error_flag = False

        for stock_code in steal_list:
            try:
                # 株探から終値を取得
                self.log.info(f'終値取得/出力開始 証券コード: {stock_code}')
                result, owarine_info = self.kabutan.get.get_closing_price(stock_code, time_type)
                if result == False:
                    self.log.error(f'終値取得処理でエラー\n{owarine_info}')
                    error_flag = True
                    continue

                # 次営業日のS高の価格を計算
                owarine = float(owarine_info[0].replace(',', ''))
                owarine_info[0] = owarine
                upper_price = self.culc.culc_upper_price(stock_code, owarine)

                self.log.info(f'前日終値: {owarine}、翌S高価格: {upper_price}')

                # CSVへ出力
                result, error_message = self.output.owarine_csv(str(stock_code), upper_price, owarine_info)
                if result == False:
                    self.log.error(f'終値出力処理でエラー\n{error_message}')
                    error_flag = True

                self.log.info(f'終値取得/出力終了 証券コード: {stock_code}')
            except Exception as e:
                self.log.error(f'終値取得/出力処理で想定外のエラー\n{e}')
                error_flag = True

            time.sleep(3)

        # 1回でもエラーがあればLINEで通知を行う
        if error_flag:
            self.output.line('終値取得/S高計算スクリプトでエラーが発生しました')

        self.log.info('終値取得処理終了')
        return True

if __name__ == '__main__':
    owarine = Owarine()
    owarine.main()
