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

        # どこの枠からとるか 1: 前営業日の終値欄 2: 四本値の終値
        get_area = 2

        # 営業日チェック
        now = datetime.now()
        if self.culc.is_exchange_workday(now):
            time_type = self.culc.exchange_time(now)
        else:
            time_type = 0

        self.log.info(f'取得対象銘柄数: {len(steal_list)}')

        for steal in steal_list:
            # 株探から終値を取得
            result, owarine_info = self.kabutan.get.get_closing_price(steal, time_type)
            if result == False:
                self.log.error(f'終値取得処理でエラー\n{owarine_info}')
                continue

            # 次営業日の高値を計算 # TODO 呼値によっては単純に値幅を足すだけじゃダメなときある？要チェック
            upper_price = self.culc.culc_upper_price(float(owarine_info[0]))

            # CSVへ出力
            result, error_message = self.output.owarine_csv(str(steal), upper_price, owarine_info)
            if result == False:
                self.log.error(f'終値出力処理でエラー\n{error_message}')
                continue

            time.sleep(3)

        self.log.info('終値取得処理終了')
        return True

if __name__ == '__main__':
    owarine = Owarine()
    owarine.main()
