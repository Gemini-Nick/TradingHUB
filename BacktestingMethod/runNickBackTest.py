# encoding: UTF-8

import pandas as pd
from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME
from vnpy.trader.app.ctaStrategy.strategy.strategyAtrRsi import AtrRsiStrategy
from vnpy.trader.app.ctaStrategy.strategy.strategyBollChannel import BollChannelStrategy
from vnpy.trader.app.ctaStrategy.strategy.strategyDoubleMa import DoubleMaStrategy
# from vnpy.trader.app.ctaStrategy.strategy.strategyDualThrust import DualThrustStrategy
# from vnpy.trader.app.ctaStrategy.strategy.strategyKingKeltner import KkStrategy
# from vnpy.trader.app.ctaStrategy.strategy.strategyMultiSignal import MultiSignalStrategy
# from vnpy.trader.app.ctaStrategy.strategy.strategyMultiTimeframe import MultiTimeframeStrategy
# from vnpy.trader.app.ctaStrategy.strategy.strategyKDJ import KDJStrategy


class NickBackTest(object):
    def __init__(self):
        """"""
    def calculateBacktesting(self, symbollist, strategylist):
        # 填入品种队列和策略队列，返回结果resultlist, 为了输出方便检索，加入品种名称，策略名称和策略参数
        resultlist = []
        for symbol in symbollist:
            for strategy in strategylist:
                result = self.runBacktesting(symbol, strategy)
                # 加入品种名称，策略名称和策略参数
                result["Symbolname"] = str(symbol["vtSymbol"])
                result["strategyname"] = str(strategy[0])
                result["strategysetting"] = str(strategy[1])
                resultlist.append(result)
        return resultlist

    def runBacktesting(self, symbol, strategy):
        # 写入测试品种和参数, 返回回测数据集包含回测结果

        # 在引擎中创建策略对象
        # 创建回测引擎
        engine = BacktestingEngine()
        # 设置引擎的回测模式为K线
        engine.setBacktestingMode(engine.BAR_MODE)
        # 设置回测用的数据起始日期
        engine.setStartDate(symbol["StartDate"])
        engine.setSlippage(symbol["Slippage"])  # 1跳
        engine.setRate(symbol["Rate"])  # 佣金大小
        engine.setSize(symbol["Size"])  # 合约大小
        engine.setPriceTick(symbol["Slippage"])  # 最小价格变动
        engine.setCapital(symbol["Capital"])

        # 设置使用的历史数据库
        engine.setDatabase(MINUTE_DB_NAME, symbol["vtSymbol"])
        # 设置策略，策略元组中第一个是策略，第二个参数
        engine.initStrategy(strategy[0], strategy[1])
        engine.runBacktesting()
        df = engine.calculateDailyResult()
        result = []
        dfp, result = engine.calculateDailyStatistics(df)
        engine.output(u'输出统计数据')
        # engine.showDailyResult(dfp, result)
        return result

    def toExcel(self, resultlist, path="C:/Users/Gemini-Nick/Desktop/IT/vnpy-master/examples/1.xlsx"):
        # 按照输入统计数据队列和路径，输出excel，这里不提供新增模式，如果想，可以改
        # dft.to_csv(path,index=False,header=True, mode = 'a')
        summaryKey = resultlist[0].keys()
        # summaryValue = result.values()

        dft = pd.DataFrame(columns=summaryKey)
        for result in resultlist:
            new = pd.DataFrame(result, index=["0"])
            dft = dft.append(new, ignore_index=True)
        dft.to_excel(path, index=False, header=True)
        print "回测统计结果输出到" + path

if __name__ == "__main__":
    # 创建品种队列，这里可以用json导入，为了方便使用直接写了。
    symbollist = [{
        "vtSymbol": 'IF0000',
        "StartDate": "20160101",
        "Slippage": 1,
        "Size": 10,
        "Rate": 2 / 10000,
        "Capital": 1000000,
        "PriceTick": 0.1
            },
        {
            "vtSymbol": 'rb0000',
            "StartDate": "20160101",
            "Slippage": 1,
            "Size": 10,
            "Rate": 2 / 10000,
            "Capital": 1000000,
            "PriceTick": 0.1
        }]
    #这里定义策略，策略参数先为空；策略加参数是一个元组
    setting = {}
    Strategylist = [(AtrRsiStrategy, setting),
                    (BollChannelStrategy, setting),
                    (DoubleMaStrategy, setting)
                    ]
    # 这里是同一个策略，不同参数的情况，当然可以有多个策略和多个参数组合
    Strategylist2 = []
    # 策略list
    settinglist = []
    # 合并一个元组
    if settinglist != []:
        for para1 in settinglist:
            Strategylist2.append((BollChannelStrategy, para1))

    NT = NickBackTest()
    resultlist = NT.calculateBacktesting(symbollist, Strategylist)
    # 定义路径
    path = "C:/Users/Gemini-Nick/Desktop/IT/vnpy-master/examples/1.xlsx"
    NT.toExcel(resultlist, path)