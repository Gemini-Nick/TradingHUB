# encoding: UTF-8

import pandas as pd
from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME, OptimizationSetting
from vnpy.trader.app.ctaStrategy.strategy.strategyBollChannel import BollChannelStrategy
from vnpy.trader.app.ctaStrategy.strategy.strategyAtrRsi import AtrRsiStrategy

class BatchOptimization(object):
    def __init__(self):
        """"""
    def calculateBacktesting(self, symbollist, strategylist, sort='sharpratio'):
        # 填入品种队列和策略队列，返回结果resultlist, 为了输出方便检索，加入品种名称，策略名称和策略参数
        resultlist = []
        for symbol in symbollist:
            for strategy in strategylist:
                result = self.runBacktesting(symbol, strategy, sort)
                # 加入品种名称，策略名称和策略参数
                if isinstance(result, dict):
                    # 如果返回的是dict，直接加入
                    result["Symbolname"] = str(symbol["vtSymbol"])
                    result["strategyname"] = str(strategy[0])
                    result["strategysetting"] = str(strategy[1])
                    resultlist.append(result)
                else:
                    # 发现优化回来的是一个包含元组的队列，元组有三个组成，第一个排策略参数，第二个回测目标的值，第三策略参数全部运行结果。
                    # 这里我们要的就是第三个,先插入这个dict，在dict插入symbolname，和strategysetting
                    for resultraw in result:
                        resultlist.append(resultraw[2])
                        resultlist[-1]["Symbolname"] = str(symbol["vtSymbol"])
                        resultlist[-1]["strategysetting"] = str(resultraw[0])
        return resultlist

    def runBacktesting(self, symbol, strategy, sort):
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

        # 调用优化方法，可以集成优化测试
        setting = OptimizationSetting()  # 新建一个优化任务设置对象
        setting.setOptimizeTarget(sort)  # 设置优化排序的目标是策略净盈利
        print strategy[1]
        for settingKey in strategy[1]:
            if isinstance(strategy[1][settingKey], tuple):
                setting.addParameter(settingKey, strategy[1][settingKey][0], strategy[1][settingKey][1],
                                     strategy[1][settingKey][2])
            else:
                setting.addParameter(settingKey, strategy[1][settingKey])
        #
        optimizationresult = engine.runParallelOptimization(strategy[0], setting)

        engine.output(u'输出统计数据')
        # 如果是使用优化模式，这里返回的是策略回测的dict的list，如果普通回测就是单个dict
        # 如果大于30 ，就返回三十之内，否则全部
        if len(optimizationresult) > 30:
            return optimizationresult[:30]
        else:
            return optimizationresult

    def toExcel(self, resultlist, path="C:/Users/Gemini-Nick/Desktop/IT/vnpy-master/examples/2.xlsx"):
        # 按照输入统计数据队列和路径，输出excel，这里不提供新增模式，如果想，可以改
        # dft.to_csv(path,index=False,header=True, mode = 'a')
        summayKey = resultlist[0].keys()

        dft = pd.DataFrame(columns=summayKey)
        for result_ in resultlist:
            new = pd.DataFrame(result_, index=["0"])
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

    # 这里是同一个策略，不同参数的情况，当然可以有多个策略和多个参数组合
    Strategylist2 = []
    # 策略list,如果是元组，那么就是三个，按照第一个初始，第二个结束，第三个步进
    settinglist = [
        {'bollWindow': (10, 20, 2)}]
    # 合并一个元组
    if settinglist != []:
        for para1 in settinglist:
            Strategylist2.append((BollChannelStrategy, para1))
            Strategylist2.append((AtrRsiStrategy, para1))

    NT = BatchOptimization()
    resultlist = NT.calculateBacktesting(symbollist, Strategylist2, sort='sharpratio')
    # 定义路径
    path = "C:/Users/Gemini-Nick/Desktop/IT/vnpy-master/examples/2.xlsx"
    NT.toExcel(resultlist, path)