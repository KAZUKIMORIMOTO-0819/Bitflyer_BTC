#bitflyer用
import ccxt
import csv
from pprint import pprint
import pandas as pd
import requests
import random
import poloniex
import time
import datetime
from config import *



"""
Lineに送信する関数
"""
def send_line(flag, price_data, trade_range, count):
    try:
        if count != 0:
            message = "\n" + \
                      "自動売買定期報告" + \
                      "\n対象取引所:Bitflyer" + \
                      "\nレンジ:" + str(trade_range["lower"]) + "～" + str(
                trade_range["upper"]) + "円" + \
                      "\nBTC現在価格:" + str(price_data[-1]["close_price"]) + \
                      "\n設定済JPY:" + str(flag["set_jpy"]) + \
                      "\n現在保持JPY:" + str(flag["funds_jpy"]) + \
                      "\nRSI:" + str(flag["RSI"]) + \
                      "\nBTC平均取得価格:" + str(flag["average_get_price"]) + \
                      "\nBTC購入合計数量:" + str(flag["sum_position_size"]) + \
                      "\n実現利益:" + str(flag["profit"]) + \
                     "\n含み損:" + str(
                (price_data[-1]["close_price"] - flag["average_get_price"]) * flag["sum_position_size"])

        else:
            message = "\n" + \
                      "自動売買プログラムを起動しました。"

        payload = {'message': message}
        headers = {'Authorization': 'Bearer ' + line_notify_token}  # 発行したトークン
        # ライン送信
        requests.post(line_notify_api, data=payload, headers=headers)

    except:
        print("ラインを送信できませんでした")
        
"""
position_adminデータを読み込む
初期は[]となっている
"""
def read_position_admin_csv(position_admin):
    # CSVからposition_adminデータ引き継ぐ
    try:
        df = pd.read_csv('bitflyer_position_admin_data_BTC.csv')
        for u in range(len(df)):
            if df.at[u, "position"] == 1:
                position_admin.append({"buy_baseline": df.at[u, "buy_baseline"],
                                       "sell_baseline": df.at[u, "sell_baseline"],
                                       "buy_price": df.at[u, "buy_price"],
                                       "sell_price": df.at[u, "sell_price"],
                                       "buy_fee": df.at[u, "buy_fee"],
                                       "sell_fee": df.at[u, "sell_fee"],
                                       "amount": df.at[u, "amount"],
                                       "position": df.at[u, "position"],
                                       "buy_signal": df.at[u, "buy_signal"],
                                       "sell_signal": df.at[u, "sell_signal"],
                                       "time": df.at[u, "time"]})


    except:
        print("csvファイルからposition_adminデータを読み込めませんでした")
        print("過去に一度も本プログラムを起動したことがない場合もこのメッセージが表示されます")

    return position_admin

"""
日足情報からRSIを計算する。
"""
def cal_RSI():
    try:
        # polonieのAPIを用いてRSIを計算
        polo = poloniex.Poloniex()
        chart_data = polo.returnChartData('USDT_BTC', period=polo.DAY,
                                         start=time.time() - polo.DAY * 14, end=time.time())
 
        df = pd.DataFrame(chart_data)
        close = df["close"].astype("float").diff()  # 差分：値上がりor値下がり幅の計算に用いる
        close = close[1:]
        up, down = close.copy(), close.copy()
        up[up < 0] = 0  # 値上がり幅
        down[down > 0] = 0 # 値下がり幅

        rsi = up.mean() / (up.mean() - down.mean()) * 100

    except:
        rsi = 50
        print("サーバからのデータ取得に失敗し、RSIを計算できませんでした")

    return rsi

"""
position_adminの作成
売買トラップの設定
"""
def set_buy_basicprice(trade_range, bid_interval, position_admin, flag):
    temp_buyBaseline = []
    lot = (trade_range["upper"] - trade_range["lower"]) / bid_interval # 売買トラップ数の計算
    flag["position_number"] = lot # トラップ＝ポジションの数

    if len(position_admin) != 0:
        for i in range(len(position_admin)):
            temp_buyBaseline.append(position_admin[i]["buy_baseline"])

    for i in range(int(lot)):
        if ((trade_range["lower"] + i * bid_interval) not in temp_buyBaseline):
            position_admin.append({"buy_baseline": trade_range["lower"] + i * bid_interval,
                                  "sell_baseline": 0,
                                  "buy_price": 0,
                                  "sell_price": 0,
                                  "buy_fee": 0,
                                  "sell_fee": 0,
                                  "amount": 0,
                                  "position": 0,
                                  "buy_signal": 0,
                                  "sell_signal": 0,
                                  "time": flag["time"]})
    position_admin.sort(key=lambda x: x['buy_baseline'])

    return position_admin, flag

"""
価格データの取得
分速情報を取得している
返り値はopen,high,low,close    
((10[s]*6=1[min])*60[min]=60[min])の間の四本値??   
10秒間隔の値を取得し、そこから四本値を計算している？？
"""
def get_data(price_data):
    temp_price_data = []
    try:
        for _ in range(6*TIME_MARGIN):
#         for _ in range(3):
            price = float(bitflyer.fetch_ticker("BTC/JPY")['last'])
            temp_price_data.append(price)
            time.sleep(10)

        price_data.append({"open_price": temp_price_data[0],
        "high_price": max(temp_price_data),
        "low_price": min(temp_price_data),
        "close_price": temp_price_data[-1]})
    except:
        print("分足情報を取得できませんでした。")
        time.sleep(300)

    temp_price_data.clear()

    if len(price_data) >= 4:
        del price_data[0]

    return price_data

"""
現在の市場取引価格、資産を表示
"""
def show_current(price_data, flag):
    try:
        flag["funds_BTC"] = bitflyer.fetch_free_balance()['BTC'] # 口座にあるBTC
        flag["funds_jpy"] = bitflyer.fetch_free_balance()['JPY'] # 口座にある日本円
        flag["set_jpy"] = JPY # 設定済みJPY←なにを表している？
        print("市場取引価格:" + str(price_data[-1]["close_price"]))
        print("BTC資産:" + str(flag["funds_BTC"]))
        print("設定済みJPY:" + str(flag["set_jpy"]))
    except:
        print("資産状況を取得できませでした。")

    return flag


"""
購入サイズを決定する
"""
def decide_buy_size(flag):
    # 日足RSIに応じて購入量を管理
    flag["buy_size"] = int((flag["set_jpy"] / flag["position_number"]) * 1.0)

    if int(flag["RSI"]) < 20:
        flag["buy_size"] = int((flag["set_jpy"] / flag["position_number"]) * 1.2)

    # elif int(flag["RSI"]) > 70:
    #     flag["buy_size"] = int((flag["set_jpy"] / flag["position_number"]) * 0.5)

    return flag

"""
売買有無の判定
"""
def decide_buy_sell(flag, position_admin, price_data):
    try:
        print("売買有無を判定します")
        for i in range(len(position_admin)):
#             print(i)
#             print(position_admin[i])
#             print(price_data[-2])
#             print(flag)
            ### 売却判定
            if position_admin[i]["position"] == 1 and position_admin[i]["sell_baseline"] <= price_data[-1]["close_price"]:
                position_admin[i]["sell_signal"] = 1
                position_admin[i]["position"] = 0

                print("売却シグナルを検知しました")
            ### 買い判定
            elif ((position_admin[i]["buy_baseline"] - price_data[-2]["close_price"]) > 0) and \
                 ((price_data[-1]["close_price"] - position_admin[i]["buy_baseline"]) > 0) and \
                   position_admin[i]["position"] == 0 and int(flag["RSI"]) < 85:
                position_admin[i]["buy_signal"] = 1
                # 利益幅の設定
                position_admin[i]["position"] = 1
                print("購入シグナルを検知しました。")

    except:
        print("売買判定ができませんでした。(初回起動時はこのメッセージが表示されます。)")

    return flag, position_admin

"""
売買実施
"""
def buy_sell_order(price_data, flag, position_admin):
    for i in range(len(position_admin)):
        ### 売却処理
        if position_admin[i]["sell_signal"] == 1:
            try:
                bid_amount = position_admin[i]["amount"]
                position_admin[i]["sell_price"] = float(
                    bitflyer.fetch_ticker("BTC/JPY")['last']) + random.randint(11, 51)
                time.sleep(1)
                # random.randintをつけているのはテイカーではなく、メイカーで売り注文を出す確率を上げるため
                trade_result = bitflyer.create_order(symbol="BTC/JPY",
                                                   type="limit",
                                                   side="sell",
                                                   amount=bid_amount,
                                                   price=position_admin[i]["sell_price"]
                                                   )

                pprint(trade_result)
                print("売却しました")
                time.sleep(2)

                # ポジション管理用
                position_admin[i]["sell_signal"] = 0
                # 売りはすべてmakerで約定したものと仮定
                position_admin[i]["sell_fee"] = -float(bid_amount * position_admin[i]["sell_price"] * 0.0002)

            except:
                print("売却できませんでした")

            try:
                if position_admin[i]["sell_signal"] == 0:
                    # 利益計算
                    prof = [
                        (position_admin[i]["sell_price"] - position_admin[i]["buy_price"]) * bid_amount -
                        position_admin[i][
                            "buy_fee"] - position_admin[i]["sell_fee"]]
                    print(prof)
                    with open('bitflyer_BTC_profit.csv', mode='a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(prof)
            except:
                print("利益計算用CSVファイルを開くことができませんでした")
        
        ### 購入処理
        elif position_admin[i]["buy_signal"] == 1:
            try:
                print("購入処理を開始します")
#                 bid_amount = int(flag["buy_size"] / price_data[-1]["close_price"] * 10000) / 10000
#                 bid_amount = flag["buy_size"] / price_data[-1]["close_price"] 
#                 print("buy_size={}".format(flag["buy_size"]))
#                 print("price_data={}".format(price_data[-1]["close_price"]))
#                 print("bid_amount={}".format(bid_amount))
                bid_amount = 0.001
                trade_result = bitflyer.create_order(symbol="BTC/JPY",
                                                   type="market",
                                                   side="buy",
                                                   amount=bid_amount,
                                                   price=0
                                                   )

                pprint(trade_result)
                print("購入しました")
                time.sleep(5)

            except:
                print("購入できませんでした")
                position_admin[i]["buy_signal"] = 0
                position_admin[i]["buy_price"] = 0
                position_admin[i]["sell_price"] = 0
                position_admin[i]["sell_baseline"] = 0
                position_admin[i]["position"] = 0

            try:
                # ポジション管理用
                position_admin[i]["buy_signal"] = 0
                position_admin[i]["amount"] = bid_amount
                # position_admin[i]["buy_price"] = price_data[-1]["close_price"]
                position_admin[i]["buy_price"] = bitflyer.fetch_my_trades("BTC/JPY", None, 1)[0]["price"]
                position_admin[i]["sell_baseline"] = position_admin[i]["buy_price"] * PROFIT_MARGIN

                trade_history = bitflyer.fetch_my_trades("BTC/JPY", limit=1)
                position_admin[i]["buy_fee"] = float(trade_history[0]["info"]["fee_amount_quote"])

            except:
                print("購入時の手数料を取得できませんでした")

    return flag, position_admin

def cal_get_average_price(position_admin, flag):
    try:
        sum_position_price = 0
        sum_position_amount = 0

        for i in range(len(position_admin)):
            if position_admin[i]["position"] == 1:
                sum_position_price += position_admin[i]["buy_price"] * position_admin[i]["amount"]
                sum_position_amount += position_admin[i]["amount"]

        flag["average_get_price"] = sum_position_price / sum_position_amount
        flag["sum_position_size"] = sum_position_amount

    except:
        print("ポジションサイズの計算ができませんでした")
        print("ポジションを1つも所持していない場合もこのメッセージが表示されます。")

    return flag

"""
利益計算
"""
def cal_current_profit(flag):
    try:
        current_value = 0
        data = pd.read_csv('bitflyer_BTC_profit.csv', header=None)
        for i in range(len(data)):
            current_value += data[0][i]

        flag["profit"] = current_value
    except:
        print("利益ファイルの読み込みに失敗しました。1円も利益が発生していない場合は失敗します。")

    return flag

def write_position_admin_csv(position_admin):
    try:
        with open('bitflyer_position_admin_data_BTC.csv', mode='w', newline="") as f:
            pass

        with open('bitflyer_position_admin_data_BTC.csv', mode='w', newline="") as f:
            writer = csv.DictWriter(f, ["buy_baseline",
                                       "sell_baseline",
                                       "buy_price",
                                       "sell_price",
                                       "buy_fee",
                                       "sell_fee",
                                       "amount",
                                       "position",
                                       "buy_signal",
                                       "sell_signal",
                                       "time"])
            writer.writeheader()
            for _ in range(len(position_admin)):
                writer.writerow(position_admin[_])
    except:
        print("ポジション管理データを書き込みできませんでした")
        
"""

"""
def del_position_admin(position_admin, flag):
    temp = []
    for i in range(len(position_admin)):
        if position_admin[i]["position"] == 1:
            temp.append(position_admin[i])

    position_admin = temp

    return position_admin



### main処理
position_admin = read_position_admin_csv(position_admin)
send_line(flag, price_data, trade_range, count)
flag["RSI"] = cal_RSI()

# 以下は繰り返し処理
while True:
    count += 1

    print("■ 現在の情報、" + str(count) + "回目です。")
    print("レンジは" + str(trade_range["lower"]) + "～" + str(trade_range["upper"]) + "円です。")
    print("RSI:" + str(flag["RSI"]))

    # position_admin作成
    position_admin, flag = set_buy_basicprice(trade_range, bid_interval, position_admin, flag)

    # 価格情報取得
    price_data = get_data(price_data)
    # 現在の市場取引価格、資産を表示
    flag = show_current(price_data, flag)
    # 購入サイズを検討
    flag = decide_buy_size(flag)
    print(flag)

    # 売買有無判定
    flag, position_admin = decide_buy_sell(flag, position_admin, price_data)
    # 売買実施
    flag, position_admin = buy_sell_order(price_data, flag, position_admin)
    # 利益計算
    flag = cal_current_profit(flag)
    # 現在のポジション状況出力
    write_position_admin_csv(position_admin)
    # 過去ポジション消去
    position_admin = del_position_admin(position_admin, flag)

    if count == 1:
        flag = cal_get_average_price(position_admin, flag)
        send_line(flag, price_data, trade_range, count)

    elif count % 2 == 0:
        flag = cal_get_average_price(position_admin, flag)
        flag["RSI"] = cal_RSI()
        send_line(flag, price_data, trade_range, count)

    print("--------------------------------------------------------------------------------")