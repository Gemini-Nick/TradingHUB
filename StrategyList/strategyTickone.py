# encoding: UTF-8

"""


策略逻辑：
入场： 每两秒读一次，分析过去N1个tick的的总计，如果买量大于卖量K倍，且lastprice向上（最后一个值的lastprice大于或等于10个中的N2个tick的lastprice）
空单反之
下单价格是档期tick，bid or ask价格加一个点位的市价单，（止损）同时开反向2个点为的阻止单；
离场：如果已经是买入价格正向N3个点，再吃判断趋势，如果已经不符合，市价卖出。如何持有，清掉之前阻止单，改挂当前价位反向2个点阻止单。

"""

from __future__ import division
from vnpy.trader.vtGateway import *
from datetime import datetime, time
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager,
                                                     TickArrayManager)


########################################################################
class TickOneStrategy(CtaTemplate):
    """基于Tick的交易策略"""
    className = 'TickOneStrategy'
    author = u'BillyZhang'

    # 策略参数
    fixedSize = 1
    Ticksize = 10
    initDays = 0

    DAY_START = time(9, 00)  # 日盘启动和停止时间
    DAY_END = time(14, 58)
    NIGHT_START = time(21, 00)  # 夜盘启动和停止时间
    NIGHT_END = time(10, 58)

    # 策略变量
    posPrice = 0  # 持仓价格
    pos = 0       # 持仓数量


    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'initDays',
                 'Ticksize',
                 'fixedSize'
                 ]

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'posPrice'
               ]

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'posPrice',
                'intraTradeHigh',
                'intraTradeLow']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""

        super(TickOneStrategy, self).__init__(ctaEngine, setting)

        #创建Array队列
        self.tickArray = TickArrayManager(self.Ticksize)

    # ----------------------------------------------------------------------
    def onminBarClose(self, bar):
        """"""

        # ----------------------------------------------------------------------

    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)
        #tick级别交易，不需要过往历史数据


        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        currentTime = datetime.now().time()
        # 平当日仓位, 如果当前时间是结束前日盘15点28分钟,或者夜盘10点58分钟，如果有持仓，平仓。
        if ((currentTime >= self.DAY_START and currentTime <= self.DAY_END) or
            (currentTime >= self.NIGHT_START and currentTime <= self.NIGHT_END)):
            TA = self.tickArray
            TA.updateTick(tick)
            if not TA.inited:
                return
            if self.pos == 0:
                # 如果空仓，分析过去10个对比，ask卖方多下空单，bid买方多下多单，并防止两个差价阻止单
                if TA.askBidVolumeDif() > 0:
                    self.short(tick.lastPrice, self.fixedSize, False)
                    self.cover(tick.lastPrice + 2,self.fixedSize, True)
                elif TA.askBidVolumeDif() < 0:
                    self.buy(tick.lastPrice, self.fixedSize, False)
                    self.sell(tick.lastPrice - 2, self.fixedSize, True)

            elif self.pos > 0:
                # 如果持有多单，如果已经是买入价格正向N3个点，再次判断趋势，如果已经不符合，市价卖出。如果持有，清掉之前阻止单，改挂当前价位反向2个点阻止单。
                if  tick.lastprice - self.posPrice >= 3:
                    if TA.askBidVolumeDif() < 0:
                        self.cancelAll()
                        self.sell(tick.lastPrice - 2, self.fixedSize, True)
                    else:
                        self.cancelAll()
                        self.sell(tick.lastPrice, self.fixedSize, False)

            elif self.pos < 0:
                # 如果持有空单，如果已经是买入价格反向N3个点，再次判断趋势，如果已经不符合，市价卖出。如果持有，清掉之前阻止单，改挂当前价位反向2个点阻止单。
                if  tick.lastPrice - self.posPrice <= -3:
                    if TA.askBidVolumeDif() > 0:
                        self.cancelAll()
                        self.cover(tick.lastPrice + 2, self.fixedSize, True)
                    else:
                        self.cancelAll()
                        self.cover(tick.lastPrice, self.fixedSize, False)
        else:
            if self.pos > 0:
                self.sell(tick.close, abs(self.pos),False)
            elif self.pos < 0:
                self.cover(tick.close, abs(self.pos),False)
            elif self.pos == 0:
                return





    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""


    # ----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到X分钟K线"""



    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):

        self.posPrice = trade.price
        # 同步数据到数据库
        self.saveSyncData()
        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass