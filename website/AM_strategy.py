# -*- coding: utf-8 -*-
"""
Created on Sat Jan 13 16:26:10 2024

@author: fastwater
"""

import pandas as pd
import datetime
import pickle # 用于存储

class AM_strategy():
    # 只存储策略数据，不存储行情数据，行情数据从 trade_engine 中引用！
    # 行情数据就是一个 合约相关的 DataFrame, 有基础 bar 信息。行情数据最好有 数字 index 数据，方便计算距离，趋势线等！
    def __init__(self, webapp):

        self.webapp = webapp  # 网页接口 --- 引发网页显示变化 --- 读取网页post 更新 策略数据

        # self.file_state = 'strdata/df_states.csv'
        self.file_shape = 'strdata/df_shapes.csv' # 以后也可以考虑 分 期货种类存储？载入快！
        self.file_barrier = 'strdata/df_barries.csv'
        self.file_shape_base = 'basedata/shape_base.csv'

        self.fut_name = ''

        self.data_init()

    # 核心函数 被 check_conditions_trade 调用，检查是否符合 某个 条件
    # 生成 交易 信号
    def condition_meets(self):
        return True
    # 核心函数 检查条件，然后符合 就交易
    def check_conditions_trade(self):
        if self.condition_meets():
            pass # trade

    # 策略数据初始化, 从pickle文件读取?
    def data_init(self): # 用 pickle存取更方便，快速！

        # self.collist= ['OpenPrice', 'HighPrice', 'LowPrice', 'LastPrice'] # ['open','high','low','close' ]
        self.collist= ['open', 'high', 'low', 'close']
        # ---------------------------------- 行情数据 new -------------------------------
        self.futlist = ['i', 'p']
        self.futdict = {}
        df3m = []
        for fut in self.futlist:
            df1 = pd.read_csv('bardata/' + fut + '_futall.csv', index_col=0)  # 对应 am1.dfbar, 实时存储
            df1.index = pd.to_datetime(df1.index)
            df3m.append(df1)
            self.futdict[fut] = sorted(list(df1.futname.str[len(fut):].unique())) # 合约字典

        df3m = pd.concat(df3m)

        self.df30m, self.dfday = get30M_from3M(df3m.copy())
        self.df3m = df3m

        # ---------------------------------- 行情数据 old -------------------------------
        # self.file_bar = 'bardata/histall.csv'  # 这个使混合存储的，以后要改成分别存储的！
        # # 'curdfbar.csv' # 'curdfbar.csv' # 'curdfbarNew.csv'
        #
        # self.dfbar = pd.read_csv(self.file_bar, index_col=0)  # 对应 am1.dfbar, 实时存储
        # self.dfbar.index = pd.to_datetime(self.dfbar.index)
        #
        # # ----- 可用合约相关 df -----
        # futlist = self.dfbar.InstrumentID.unique() # 所有的 futlist
        # futdict = {f1: [f1[:1], f1[1:]] if f1[1].isdigit() else [f1[:2], f1[2:]] for f1 in futlist}
        #
        # self.dffutnames = pd.DataFrame(futdict).T
        # self.dffutnames.columns = ['fut', 'month']
        # print(self.dffutnames)
        # print(self.dffutnames[self.dffutnames.fut == 'MA'].month.to_list())

        # print(self.dfbar)
        # self.dfbar.index = pd.to_datetime(self.dfbar['TradingDay'].str[2:-1] + ' ' + self.dfbar['UpdateTime'].str[2:-1])

        # ----------------------------------- 趋势波段形态综合 数据 -----------------------------------
        state_columns = [ # 仅仅用于说明
            # 基本信息
            'id', 'idlast', # 上次状态变更前的 id
            'fut_name',  # 对应的期货主力合约, 只有一个，如果时间段内，换了期货主力合约, 则 更新 state_id，生成新的 state, 时间段相连

            # 级别信息 ---- 5的级别可以相互 成为 child
            'period_type', # 0,1,2,3,4,5 对应 3min, 30min, day, trend0, trend1, trend2, # 6 个级别 放在 一起，用 period_type 区分

            # 日期相关 --- # 2个 enddt 如果 = pd.to_datetime('2100-01-01'), 则表示 enddt 是当前最新的状态，
            'stdt_effect', 'enddt_effect',  # 当前shape 适用时间范围范围！！
            'stdt', 'enddt',  # 当前shape 范围, (enddt 如果 大于 当前时间，表明是实时 形态，enddt取当前时间)

            # 波段趋势相关 ----- 波段和形态 2选1 trend or shape
            'trend_type', # 之字形, N字形，
            'trend_dir',  # 趋势方向, 1, 0, -1 # 更精确可以考虑用斜率...
            'pts',  # 点(dt+price)的list, ['2023-12-12 14:34',3000]_[...] # 展示在bar图，从bar图选取！
            'line',  # 趋势线, 类似pts，只有两个点  # 展示在 bar图，从bar图选点连接！

            # 形态相关 ----- 对应到下面的 形态相关 df_shape_base 中的形态 --- 分开 不在一起 ---
            'typelist', # （可多选）内部还可以带参数，主要是str格式即可（后续显示可以格式转换为更好的格式）
                        # e.g. [typename:{para1:v1,para2:v2}]_[typename2]... # 无参数也可以

        ]

        self.df_shapes = pd.read_csv(self.file_shape, index_col=0, encoding='gbk') # 盘中仅显示当前还有效的 states # 区间 、 趋势线 、 点能否显示在图上？
        self.df_shapes.fillna('无', inplace=True)
        # ----------------------------------- 掩体相关 -----------------------------------
        barrier_columns = ['barid',  'baridlast', 'fut_name', # 每次触及 bar 特点发生改变，则 更新一个新的 barid, 上次的 barid 存储在 baridlast中！
                           'stdt_effect', 'enddt_effect',  # 掩体可以作用的时间
                           'bar_level','bar_type', # bar_level 分级 0 平仓, 1 重要, bar_type 具体类型,
                           'bar_line', # bar 掩体的实体！因为可能不是水平线，所以可以是两点的线！类似 line
                           ] # 仅仅用于说明
        self.df_barries = pd.read_csv(self.file_barrier, index_col=0, encoding='gbk') # 盘中仅显示当前还有效的 barriers # 掩体的线或块 能否显示在图上
        self.df_barries.fillna('', inplace=True)

        # ----------------------------------- 基础信息相关 -----------------------------------
        # self.df_shape_base = pd.read_csv(self.file_shape_base, encoding='gbk') # 级别形态数据存储 columns: 形态名 中文名 类别 备注
        # （可选级别list）(参数list) 等固定常数 --- 用来 网页中 选择 ---


        # ----------------------------------- 逻辑相关 -----------------------------------

        # 知识图谱，方便查询，修改，新增 ？
        # 条件 对应 函数，有些简单条件，可以统一对应简单函数，eval 或者 包装版的 string 或 list等 解读 。。。
        # 'up1': '上涨趋势' + ('波段1的点3' or '摸顶' or   )+ '反抽不突破1的趋势线' + '波段1是之字形'


        # 逻辑定义 ----- 比较复杂 ----- 所有 多空 的逻辑 ---- 平仓逻辑 --- 止损相关逻辑 --- 平推相关逻辑



    # 手动更新 策略数据
    def get_data_manual_chg(self):
        pass


    # 自动更新数据 --- 根据行情数据 --- 目前考虑 tick数据用于 交易 --- bar 数据用于 生成信号
    def data_update(self, bar_dict):
        if self.dfbar.shape[0] == 0:
            self.dfbar = pd.DataFrame([bar_dict])
            self.dfbar.index = pd.to_datetime(bar_dict['TradingDay'].decode('utf-8') + ' ' + bar_dict['UpdateTime'].decode('utf-8'))
            # self.dfbar.index = pd.to_datetime(self.dfbar['TradingDay'].str[2:-1] + ' ' + self.dfbar['UpdateTime'].str[2:-1])
        else:
            inddt = pd.to_datetime(bar_dict['TradingDay'].decode('utf-8') + ' ' + bar_dict['UpdateTime'].decode('utf-8'))
            print(inddt)
            self.dfbar.loc[inddt] = pd.Series(bar_dict)

        self.dfbar.to_csv(self.file_bar)



    # ------------------------------------ 一些需要的子函数, 比如一些底层计算 (趋势线等) ----------------------------
    def calc_ddd(self):
        pass

def get30M_from3M(df1):
    # get 30m from 3m
    df1['30Min_sig'] = df1.index
    df1['30Min_sig_minutes'] = df1['30Min_sig'].dt.minute % 30

    df1.loc[(df1.index.time >= datetime.time(10, 30)) & (df1.index.time < datetime.time(10, 45)), '30Min_sig_minutes'] += 30
    df1.loc[(df1.index.time >= datetime.time(13, 30)) & (df1.index.time < datetime.time(13, 45)), '30Min_sig_minutes'] += 30 + 2 * 60  # 中午休息2小时
    df1.loc[(df1.index.time >= datetime.time(10, 45)) & (df1.index.time <= datetime.time(15, 00)), '30Min_sig_minutes'] -= 15
    df1.loc[df1['30Min_sig_minutes'] < 0, '30Min_sig_minutes'] += 30
    df1['30Min_sig'] -= df1['30Min_sig_minutes'].apply(lambda x: datetime.timedelta(minutes=x))

    dfgr1 = df1.groupby(['futname', '30Min_sig'])
    df30M = dfgr1[['cumvol', 'turnover']].last()  # ohlc()

    df30M['open'] = dfgr1.open.first()  # ohlc()
    df30M['high'] = dfgr1.high.max()  # ohlc()
    df30M['low'] = dfgr1.low.min()  # ohlc()
    df30M['close'] = dfgr1.close.last()  # ohlc()

    df30M.reset_index(level=0, inplace=True)
    df30M.index.name = None

    # day
    df1['day_sig'] = df1.index.date # TODO later

    dfgr1 = df1.groupby(['futname', 'day_sig'])
    dfday = dfgr1[['cumvol', 'turnover']].last()  # ohlc()

    dfday['open'] = dfgr1.open.first()  # ohlc()
    dfday['high'] = dfgr1.high.max()  # ohlc()
    dfday['low'] = dfgr1.low.min()  # ohlc()
    dfday['close'] = dfgr1.close.last()  # ohlc()
    dfday.reset_index(level=0, inplace=True)
    dfday.index.name = None

    return df30M, dfday # 如果直接设为 Mulit index， 是否更好？
