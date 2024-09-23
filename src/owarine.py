import csv
import kabutan
import time
from main import Main

class Owarine(Main):
    '''株探から終値を取得してCSVに記録する'''
    def __init__(self):
        super().__init__()
        self.kabutan = kabutan.Kabutan(self.log)

    def main(self):
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

        for steal in steal_list:
            # 株探から終値を取得
            result, owarine_info = self.kabutan.get.get_closing_price(steal)
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

        return True

if __name__ == '__main__':
    owarine = Owarine()
    owarine.main()
