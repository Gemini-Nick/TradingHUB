# encoding: UTF-8
from __future__ import division

from vnpy.trader.vtGateway import *
from math import isnan
import numpy as np
import pandas as pd
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate, TargetPosTemplate,
                                                     BarGenerator,
                                                     ArrayManager)


class GridStrategy(CtaTemplate):
    className = 'GridStrategy'
    author = u'张老师'

    # 策略参数
    historyBars = 200  # 历史数据大小，用来确定网格基准线
    initDays = 20  # 初始化数据所用的天数，随着历史数据大小要改变
    gridlines = 10  # 网格线数量，单边数量
    ordersize = 10  # 最大持仓数量
    order = 1      # 每次下单手数
    barMins = 30    #bar的时间
    frozenBars = 1 #平仓后，frozenBars个bar不再开反向单
    atrWindow = 30         # ATR窗口数
    slMultiplier = 5.0     # 计算止损距离的乘数

    # 基本变量
    upline = 0   #当前上线
    bottomline = 0 #当前下线
    frozen = 0 #当前是否冻结开反向单
    intraTradeHigh = 0
    intraTradeLow = 0
    atrValue = 0



    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'historyBars',
                 'initDays',
                 'gridlines',
                 'barMins',
                 'order',
                 'ordersize',
                 'atrWindow',
                 'slMultiplier'
                 ]
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'frozen',
               'upline',
               'bottomline'
               'atrValue']
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'frozen']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(GridStrategy, self).__init__(ctaEngine, setting)
        self.bg = BarGenerator(self.onBar, self.barMins, self.onXminBar)  # 创建K线合成器对象
        self.am = ArrayManager(self.historyBars + 50)

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        self.putEvent()

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()



    # -----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到X分钟K线"""
        # 全撤之前发出的委托
        self.cancelAll()
        # 保存K线数据
        am = self.am
        am.updateBar(bar)
        if not am.inited:
            return
        # 这里采用了均量交易法,就是每笔。
        # 空仓时候，每次突破上线是开多单，突破下线是开空单；
        # 有多单时候，突破上线加多单，突破下线情况清空所有多单，
        # 有空单时候，突破下线加空单，突破上线清空所有空单，
        # 为防止在一个线上下波动，造成重复开平仓情况，如果突破平仓，比如平多单，后面n个bar不能再开多单，只能开空单；反之平空单后，
        # 后面n个bar只能开多单。
        # 计算网格,返回通道队列, 再算出当前点位所在通道，0为最下通道，2*self.gridlines - 1为最上通道
        baseline = self.am.sma(self.historyBars)
        # 过去300的标准差，按照顶一个gridlines取整做出一个队列
        intervallist = baseline+ np.array([n * 1.00 / self.gridlines for n in range(-1 * self.gridlines, self.gridlines + 1)]) * self.am.std(self.historyBars)

        griploc = pd.cut([bar.close], intervallist, labels=[nx for nx in range(0,2*self.gridlines)])[0]
        # 如果返回为nan，说明现在bar.close在标准差范围以外，如果没有仓位，先不处理；如果有，按照ATR波动移动止盈
        if isnan(griploc):
            # 持有多头仓位
            if self.pos > 0:
                self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
                self.intraTradeLow = bar.low
                self.longStop = self.intraTradeHigh - self.atrValue * self.slMultiplier
                self.sell(self.longStop, abs(self.pos), True)
            # 持有空头仓位
            elif self.pos < 0:
                self.intraTradeHigh = bar.high
                self.intraTradeLow = min(self.intraTradeLow, bar.low)
                self.shortStop = self.intraTradeLow + self.atrValue * self.slMultiplier
                self.cover(self.shortStop, abs(self.pos), True)
            return
        #返回上下线：
        self.upline = intervallist[griploc + 1]
        self.bottomline = intervallist[griploc]

        # 空仓时候，每次突破上线是开多单，突破下线是开空单；
        # 如果此时在最下一个通道，此时只挂往上的多单, 如果在最上面通道，此时只挂往下空单；如果在中间的，则同时开上下单
        if self.pos == 0:
            if griploc ==0:
                self.buy(self.upline, self.order, True)
            elif griploc == 2*self.gridlines - 1:
                self.short(self.bottomline,self.order,True)
            else:
                #此时如果frozen 为0， 直接开上下单：
                if self.frozen == 0:
                    self.buy(self.upline, self.order, True)
                    self.short(self.bottomline, self.order, True)
                #此时如果大于0，只能开空单，如果小于0，只能开多单
                elif self.frozen > 0:
                    self.frozen = self.frozen -1
                    self.short(self.bottomline, self.order, True)
                elif self.frozen < 0:
                    self.frozen = self.frozen + 1
                    self.buy(self.upline, self.order, True)
        #如果持有多仓时候，如果在中间通道，同时开上下单；如果最高点位不再开单，突破最大标准差高点，
        elif self.pos > 0:
            # 在最下通道不可能有多单，只用考量在中间段,pos 小于ordersize可以增多仓，否则只能向下平仓；和最高段情况,最高段设置往下平仓，
            if griploc == 2*self.gridlines - 1:
                self.intraTradeHigh = bar.high
                self.sell(self.bottomline, abs(self.pos), True)
            else:
                if abs(self.pos) < self.ordersize:
                    self.buy(self.upline, self.order, True)
                    self.sell(self.bottomline, abs(self.pos), True)
                else:
                    self.sell(self.bottomline, abs(self.pos), True)
        elif self.pos < 0:
            # 最上通道通道不可能有空单，只用考虑中间段，和最低档情况
            if griploc == 0:
                self.intraTradeLow = bar.low
                self.cover(self.upline,abs(self.pos),True)
            else:
                if abs(self.pos) < self.ordersize:
                    self.cover(self.upline, abs(self.pos),True)
                    self.sell(self.bottomline, self.order, True)
                else:
                    self.cover(self.upline, abs(self.pos), True)


    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)
    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托推送"""
        pass


    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        # 如果收到成交，清空所有挂单
        self.cancelAll()
        # 如果交易多头方向，且现在仓位为0，则应该是空头平仓，不再开空单
        if trade.direction == DIRECTION_LONG and self.pos == 0:
            self.frozen = -1* self.frozen
        # 如果交易空头方向，且现在仓位为0，则应该是多平仓，不再开多单
        elif trade.direction == DIRECTION_SHORT and self.pos == 0:
            self.frozen = self.frozen


        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass