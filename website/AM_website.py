# encoding:utf-8
# AM_website 作为程序入口点, 连接 AM_trader 和 AM_strategy

# In[] --------------- import -------------------

# >>>>  general import >>>>
import datetime
from multiprocessing import Process, Queue
import time
import pandas as pd
import json

# >>>>>>>>>>>>>>>> strategy >>>>

import AM_strategy as am

# >>>>>>>>>>>>>>>>  website import >>>>
from flask import Flask, render_template, request, jsonify
import json
import plotly
import plotly.graph_objs as go

# import flask
# import requests
# import pytz
# from flask_httpauth import HTTPBasicAuth # TODO 密码验证，稍后加
# import websockets

# >>>> 定时 读取数据 >>>>
# from warnings import filterwarnings
# from pytz_deprecation_shim import PytzUsageWarning # dev2安装了
# filterwarnings('ignore', category=PytzUsageWarning)
from flask_apscheduler import APScheduler

# In[] ------------------ 全局数据 -----------------

# website app
app = Flask(__name__)

# AM_strategy 对象
am1 = am.AM_strategy(webapp=app)

# In[] --------------- website interface ----------------

# ------------ 入口 ------------
@app.route('/')
def index():
    # 创建蜡烛图
    data1 = am1.dfday
    trace = go.Candlestick(x=data1.index, #.astype(str),
                           open=data1[am1.collist[0]],
                           high=data1[am1.collist[1]],
                           low=data1[am1.collist[2]],
                           close=data1[am1.collist[3]])
    layout = go.Layout(title="Basic Candlestick Chart")
    fig = go.Figure(data=[trace], layout=layout)
    # 将图形转换为 JSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('hh127.html', # html
                           graphJSON=graphJSON, # bar
                           # df_trend = dftrend.to_json(orient='split')
                          )
    # return render_template( 'resizeable_example1.html' )#
    #return render_template(  'index2.html' , graphJSON=graphJSON)

# ------------ bar数据更新  ------------
@app.route('/refresh_data') # TODO 这个有问题，需要加入 stdt 和 endt！
def refresh_data():
    dfdata = am1.dfday[am1.collist].reset_index()
    #dfdata['index'] = dfdata['index'].astype(str)
    senddata = dfdata.to_dict()
    #print(senddata)
    return jsonify(senddata)

# ----------- bar 的fut改变 ------------
@app.route('/fut_change', methods=['POST'])
def getmonthbyfut():
    futid = request.form['futid']
    # mlist= am1.dffutnames[am1.dffutnames.fut == futid].month.to_list()
    mlist = am1.futdict[futid]
    return jsonify(mlist)  # 'Date received'

# ----------- bar 的fut改变 ------------
# TOBE cut when upload 20240310
typelist_dict = {
    '日线': ['杯柄形态', '三角形', '岛型反转', '顺向孤岛', '三重顶底',
            '双顶底', '2b牛角', '矩形/高锦旗形', '圆弧顶底', '塔形顶底',
            '独轮震荡', '四肩顶',
            '扩散形态', '分手线/空中加油','大型宽幅震荡区间', '长影线'
           ],
    '半小时': ['双顶底', '2b牛角', '头肩顶底', '高锦旗形', '小双顶/小双底',
           '上升/下降三角形', '连续三根及以上长上/下影线', '两次顺向跳空/岛型反转',
           '窄幅矩形震荡', '蝙蝠/倒蝙蝠', '独轮震荡', '准备突破:支撑位处小十字星',
           '连续两根小星线', '启明星/黄昏星', '宽幅矩形震荡', '宽幅扁圆拱形震荡',
           '上涨乏力/跌不下去的连续小K线', '长影线', '单K震荡'  # 黄昏星
           ],
    '3分钟': ['双顶底', '高位上吊线/流星线', '低位小锤子线/倒锤子线', '包孕形态',
            '乌云盖顶', '并列阳阴', '小单顶/黄昏星', '小单顶/启明星', '一阴包多阳',
            '一阳包多阴', '高开低走的VSB', '低开高走的VDB', '长上影线+包含上影线的吞噬形态',
            '长下影线+包含下影线的吞噬形态', '连续两根小十字星+顺向跳空',
            '假突破:窄幅震荡区间边沿/反向掩体', '头肩顶底/三重顶底/三山三川', '上升/下降三法',
            '长影线', '高浪线/十字星/墓碑十字星/蜻蜓十字星', '2b牛角',
            '连续三根长上影线/连续两根长上影线+吞噬', '连续三根长下影线/连续两根长下影线+吞噬',
            '支撑位处小十字星/锤子线/倒锤子线', '压力位处小十字星/上吊线/流星线'
            '小双顶底', '回封前跳空缺口',  '单K震荡区间:VSB/VDB', '上升/下降三角形/楔形/带杆旗形/旗形',
            '手指形态', '跳空突破', '突破:横向/斜向或同时突破横向和斜向掩体', '两次顺向的跳空',
            '塔形顶底', '长上影线+包含其实体的阳线', '长下影线+包含其实体的阴线',
            '高锦旗形', '吞噬形态', '独轮震荡'
           ],

}
@app.route('/period_change', methods=['POST'])
def get_typelist():
    period_type = request.form['period_type']
    if period_type[:2] == '波段':
        period_type = '日线'
    return jsonify(typelist_dict[period_type])  # 'Date received'

# ------------ bar日期范围 等 ------------
@app.route('/update_dtrange', methods=['POST'])
def update_dtrange():
    stdt = request.form['stdt']
    endt = request.form['endt']
    futid = request.form['futid']
    monthid = request.form['monthid']

    futname = futid + monthid # monthid[-5:-3] + monthid[-2:] # 期货合约名字
    bar_period = request.form['bar_period'] #

    if bar_period == '日线': # TODO 以下这部分修改修改！
        dfdata = am1.dfday
    elif bar_period == '半小时':
        dfdata = am1.df30m
    elif bar_period == '3分钟':
        dfdata = am1.df3m

    #print(futname)

    dfdata = dfdata[dfdata.futname == futname] # InstrumentID
    #print(dfdata)
    if stdt == '' or endt == '' or stdt is None or endt is None:
        dfdata = dfdata[am1.collist].sort_index() # .reset_index()
    else:
        dfdata = dfdata[am1.collist].loc[stdt:endt].sort_index() # .reset_index()

    #print(dfdata)

    #dfdata['index'] = dfdata['index'].astype(str)
    senddata = { c1: dfdata[c1].to_list() for c1 in dfdata.columns}
    #print(senddata)
    return jsonify(senddata) # 'Date received'


# ------------ row2,3 基本数据传输 ----------------
# 定义一个路由，用于返回数据表的数据
@app.route('/r2_data')
def r2_data():
    return jsonify(data=am1.df_shapes.reset_index().to_dict(orient='records'))

@app.route('/r3_data')
def r3_data():
    # print(am1.df_barries.reset_index().to_dict(orient='records'))
    return jsonify(data=am1.df_barries.reset_index().to_dict(orient='records'))

# ------------ row2,3 相关 增删改查 ----------------
# 定义一个路由，用于添加数据
@app.route('/add', methods=['POST'])
def add():
    data = request.form  # 获取名为'mydata'的表单数据
    # data = request.get_json()
    if data['type'] == 'r2': # 如果是 r2
        data_typelist = data.getlist('typelist[]')
        am1.df_shapes.loc[am1.df_shapes.index.max() + 1] = [-1, 'rb2405',  # TODO: 对应当前选择 futname
            datetime.datetime.now(),  pd.to_datetime('2100-01-01'), # TODO: now 不对， 后面这个表示最新
            data['period_type'], data['stdt'], data['endt'], data['trend_dir'], data['trend_type'],
            data['pts'], data['line'], str(data_typelist)] # data['typelist']]
        am1.df_shapes.to_csv(am1.file_shape, encoding='gbk')
    elif data['type'] == 'r3': # 如果是 r3
        am1.df_barries.loc[am1.df_barries.index.max() + 1] = [-1, 'rb2405',  # TODO: 对应当前选择 futname
            datetime.datetime.now(),  pd.to_datetime('2100-01-01'), # TODO: now 不对， 后面这个表示最新
            data['bar_level'], data['bar_type'], data['bar_line']]
        am1.df_barries.to_csv(am1.file_barrier, encoding='gbk')
    # 返回一个json响应
    return jsonify(success=True)

# 定义一个路由，用于删除数据
@app.route('/delete', methods=['POST'])
def delete():
    # 获取json格式的数据
    data = request.form  # 获取名为'mydata'的表单数据
    if data['type'] == 'r2': # 如果是 r2
        am1.df_shapes.drop(int(data['id']), inplace=True)
        am1.df_shapes.to_csv(am1.file_shape, encoding='gbk')
    elif data['type'] == 'r3': # 如果是 r2
        am1.df_barries.drop(int(data['barid']), inplace=True)
        am1.df_barries.to_csv(am1.file_barrier, encoding='gbk')

    # 返回一个json响应
    return jsonify(success=True)

# 定义一个路由，用于更新数据
@app.route('/update', methods=['POST'])
def update():
    # 获取json格式的数据
    data = request.form # request.get_json()
    # 根据索引更新dataframe中的一行数据
    if data['type'] == 'r2': # 如果是 r2
        df = am1.df_shapes
        for c1 in ['period_type', 'stdt', 'endt', 'trend_dir', 'trend_type', 'pts', 'line', 'typelist' ]:
            if c1 == 'typelist': # 多选
                values = data.getlist('typelist[]')
                df.loc[int(data['id']), c1] = str(values)
                # print('typelist[]:', df.loc[int(data['id']), c1])
            else:
                df.loc[int(data['id']), c1] = data[c1]
        am1.df_shapes.to_csv(am1.file_shape, encoding='gbk')
    elif data['type'] == 'r3': ## r3
        # print(data)
        df = am1.df_barries
        for c1 in ['bar_level', 'bar_type', 'bar_line']:
            df.loc[int(data['barid']), c1] = data[c1]
        am1.df_barries.to_csv(am1.file_barrier, encoding='gbk')
    # 返回一个json响应
    return jsonify(success=True)

# ------------ 定时接口 ------------
scheduler = APScheduler()
# TODO: 如何忽略 PytzUsageWarning # TODO: 这个应该是定时查询！
@scheduler.task('cron', id='do_minute_task', minute='*', second='00', max_instances=10)
def on_bar():
    pass # TODO: 数据获取部分应该 和 网站部分 分开 独立运行, 可以在这里定期重新载入 或 更新 csv 数据


# In[] ---------------- main function -----------------------
if __name__ == '__main__':
    # --- 定时任务 ---
    scheduler.init_app(app)
    scheduler.start() # 有警告, timezone相关, 暂时忽略!
    # --- website ---
    app.run(debug=True, port = 11122) #   app.run(host='0.0.0.0', port=portnum)