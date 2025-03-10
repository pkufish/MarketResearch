import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import platform
import matplotlib as mpl

# 全局配置参数
MIN_DRAWDOWN_RATE = 10  # 最小回撤率要求（百分比）
MIN_DAYS = 5           # 最小天数
MAX_DAYS = 60          # 最大天数
TOP_N = 10             # 显示组数
TARGET = 'QQQ'        # 标的
START_DATE = '2018-01-01'

def set_chinese_font():
    """
    根据操作系统设置中文字体
    """
    system = platform.system()
    
    if system == 'Windows':
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 微软雅黑
    elif system == 'Darwin':  # macOS
        plt.rcParams['font.sans-serif'] = ['PingFang HK', 'Arial Unicode MS']
    else:  # Linux
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
    
    plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
    mpl.rcParams['font.family'] = plt.rcParams['font.sans-serif'][0]

def save_stock_data(df, ticker):
    """
    保存股票数据到本地文件
    """
    try:
        # 创建data目录（如果不存在）
        if not os.path.exists('data'):
            os.makedirs('data')
            
        # 生成文件名（包含时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'data/{ticker}_{timestamp}.csv'
        
        # 保存数据
        df.to_csv(filename)
        print(f"\n数据已保存到: {filename}")
        
        return filename
    except Exception as e:
        print(f"保存数据时发生错误: {e}")
        return None

def load_stock_data(filename):
    """
    从本地文件加载股票数据
    """
    try:
        if not os.path.exists(filename):
            raise Exception("文件不存在")
            
        df = pd.read_csv(filename, index_col=0, parse_dates=True)
        return df
    except Exception as e:
        print(f"加载数据时发生错误: {e}")
        return None

def find_top_drawdown_intervals(data):
    """
    查找前N组最大回撤区间，确保区间之间不重叠
    """
    drawdown_intervals = []
    used_dates = set()  # 用于记录已使用的日期
    
    # 遍历所有可能的起始日期
    for start_idx in range(len(data)):
        # 遍历所有可能的结束日期（在最小和最大天数范围内）
        for days in range(MIN_DAYS, MAX_DAYS + 1):
            end_idx = start_idx + days
            if end_idx >= len(data):
                break
                
            # 检查这个区间是否与已选区间重叠
            current_dates = set(data.index[start_idx:end_idx + 1])
            if current_dates.intersection(used_dates):
                continue
                
            # 计算这段时间内的回撤率
            start_price = data['Close'].iloc[start_idx]
            end_price = data['Close'].iloc[end_idx]
            drawdown_rate = (end_price / start_price - 1) * 100
            
            # 只记录回撤率大于最小要求的区间
            if drawdown_rate <= -MIN_DRAWDOWN_RATE:
                drawdown_intervals.append({
                    'start_date': data.index[start_idx],
                    'end_date': data.index[end_idx],
                    'days': days,
                    'drawdown_rate': drawdown_rate,
                    'start_price': start_price,
                    'end_price': end_price,
                    'dates': current_dates  # 保存区间内的所有日期
                })
    
    # 按回撤率排序（从大到小）
    drawdown_intervals.sort(key=lambda x: x['drawdown_rate'])
    
    # 选择不重叠的前N个区间
    selected_intervals = []
    for interval in drawdown_intervals:
        if len(selected_intervals) >= TOP_N:
            break
            
        # 检查是否与已选区间重叠
        current_dates = interval['dates']
        is_overlap = False
        for selected in selected_intervals:
            if current_dates.intersection(selected['dates']):
                is_overlap = True
                break
                
        if not is_overlap:
            selected_intervals.append(interval)
            used_dates.update(current_dates)
    
    return selected_intervals

try:
    # 获取股票的历史数据
    ticker = TARGET
    start_date = START_DATE
    end_date = datetime.now().strftime('%Y-%m-%d')  # 使用当前日期

    # 创建Ticker对象
    stock = yf.Ticker(ticker)
    
    # 下载数据
    data = stock.history(start=start_date, end=end_date)
    
    if data.empty:
        raise Exception("未能获取到数据")

    print("\n数据概览:")
    print(data.head())

    # 保存原始数据
    saved_file = save_stock_data(data, ticker)

    # 查找前N组最大回撤区间
    top_drawdown_intervals = find_top_drawdown_intervals(data)

    # 打印前N组最大回撤信息
    print(f"\n前{TOP_N}组最大回撤分析（回撤率>{MIN_DRAWDOWN_RATE}%）:")
    for i, interval in enumerate(top_drawdown_intervals, 1):
        print(f"\n第{i}组:")
        print(f"最大回撤率: {interval['drawdown_rate']:.2f}%")
        print(f"回撤天数: {interval['days']}天")
        print(f"开始日期: {interval['start_date'].date()}")
        print(f"结束日期: {interval['end_date'].date()}")
        print(f"起始价格: ${interval['start_price']:.2f}")
        print(f"结束价格: ${interval['end_price']:.2f}")

    # 保存分析数据
    if saved_file:
        analysis_file = saved_file.replace('.csv', '_maxdrawdown_analysis.csv')
        data.to_csv(analysis_file)
        print(f"\n分析数据已保存到: {analysis_file}")

    # 设置中文字体
    set_chinese_font()

    # 可视化前N组最大回撤区间
    plt.figure(figsize=(15, 8))
    plt.plot(data.index, data['Close'], label='收盘价', color='blue', alpha=0.5)
    
    # 使用不同颜色绘制前N组回撤区间
    colors = plt.cm.rainbow(np.linspace(0, 1, len(top_drawdown_intervals)))
    for i, interval in enumerate(top_drawdown_intervals):
        plt.plot([interval['start_date'], interval['end_date']], 
                 [interval['start_price'], interval['end_price']], 
                 color=colors[i], linewidth=2, 
                 label=f'第{i+1}组: {interval["drawdown_rate"]:.2f}%\n'
                       f'开始: {interval["start_date"].strftime("%Y-%m-%d")}\n'
                       f'结束: {interval["end_date"].strftime("%Y-%m-%d")}\n'
                       f'天数: {interval["days"]}天')
        
        # 添加区间标记
        plt.axvspan(interval['start_date'], interval['end_date'], 
                   color=colors[i], alpha=0.1)
    
    plt.title(f'{ticker} 前{TOP_N}组最大回撤分析（回撤率>{MIN_DRAWDOWN_RATE}%）')
    plt.xlabel('日期')
    plt.ylabel('价格 ($)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # 询问是否要加载保存的数据进行验证
    if saved_file:
        print("\n是否要加载保存的数据进行验证？(y/n)")
        if input().lower() == 'y':
            loaded_df = load_stock_data(saved_file)
            if loaded_df is not None:
                print("\n加载的数据概览:")
                print(loaded_df.head())
                print("\n数据加载成功！")

except Exception as e:
    print(f"发生错误: {e}") 

    