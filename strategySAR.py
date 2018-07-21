# encoding: UTF-8

from __future__ import division

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager)


########################################################################
class SARKELStrategy(CtaTemplate):
    """基于sar and Keltner 交易策略"""
    className = 'SARKELStrategy'
    author = u'张老师'

    # 策略参数
    sarAcceleration = 0.02 #加速线
    sarMaximum = 0.2    #
    cciWindow = 20  # CCI窗口数
    keltnerWindow = 25  # keltner窗口数
    keltnerlMultiplier = 6.0  # 乘数
    initDays = 10  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量
    barMins = 15
    barMinsClose = 10
    # 策略变量
    sarValue = 0  # sar指标数值
    cciValue = 0  # CCI指标数值
    keltnerup = 0
    keltnerdown = 0
    longStop = 0  # 多头止损
    shortStop = 0  # 空头止损

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'sarAcceleration',
                 'sarMaximum',
                 'cciWindow',
                 'keltnerWindow',
                 'keltnerlMultiplier',
                 'initDays',
                 'fixedSize',
                 'barMinsClose',
                 'barMins']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'sarValue',
               'cciValue',
               'atrValue']

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(SARKELStrategy, self).__init__(ctaEngine, setting)

        self.bg = BarGenerator(self.onBar, self.barMins, self.onXminBar)  # 创建K线合成器对象
        self.am = ArrayManager()

        self.bgclose = BarGenerator(self.onBar, self.barMinsClose, self.onminBarClose)
        self.amClose = ArrayManager()

    # ----------------------------------------------------------------------
    def onminBarClose(self, bar):
        """分钟作为清仓周期"""
        # 如果没有仓位,那么不用care,直接skip

        # 保存K线数据
        amClose = self.amClose

        amClose.updateBar(bar)

        if not amClose.inited:
            return

        # 计算指标数值
        self.sarValue = amClose.sar(self.sarAcceleration, self.sarMaximum)

        # 判断是否要进行交易
        if self.pos == 0:
            return

        # 当前无仓位，发送开仓委托
        # 持有多头仓位
        elif self.pos > 0:
            self.cancelAll()
            self.sell(self.sarValue, abs(self.pos), True)

        # 持有空头仓位
        elif self.pos < 0:
            self.cancelAll()
            self.cover(self.sarValue, abs(self.pos), True)

        # 同步数据到数据库
        self.saveSyncData()

        # 发出状态更新事件
        self.putEvent()


        # ----------------------------------------------------------------------

    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

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
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)
        self.bgclose.updateBar(bar)

    # ----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到X分钟K线"""
        # 全撤之前发出的委托
        self.cancelAll()

        # 保存K线数据
        am = self.am

        am.updateBar(bar)

        if not am.inited:
            return

        # 计算指标数值
        self.cciValue = am.cci(self.cciWindow)
        self.keltnerup, self.keltnerdown = am.keltner(self.keltnerWindow, self.keltnerlMultiplier)

        # 判断是否要进行交易

        # 当前无仓位，发送开仓委托
        if self.pos == 0:

            if self.cciValue > 0:
                # ru
                self.buy(self.keltnerup, self.fixedSize, True)

            elif self.cciValue < 0:
                self.short(self.keltnerdown, self.fixedSize, True)

        # 同步数据到数据库
        self.saveSyncData()

        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
