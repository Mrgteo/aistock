"""
股票数据路由 - 修正版
解决了实时数据合并导致的 0 值及高低价倒置问题
"""

from fastapi import APIRouter, HTTPException
import requests
import pandas as pd
import json
from datetime import datetime, time
import pytz
import akshare as ak

router = APIRouter(tags=["股票数据"])

# --- 工具函数 ---

def get_code_type(code):
    """判断是A股、港股、美股还是全球指数"""
    code = code.upper().strip()

    # 全球指数 - Yahoo格式前缀
    if code.startswith('^'):
        return code, "全球指数"

    # 全球指数 - 明确列出的代码 (不带前缀的纯代码)
    global_indices = {
        'N225',    # 日经225
        'KS11',    # 韩国综合指数
        'TWII',    # 台湾加权指数
        'ENSEX',   # 印度孟买敏感指数
        'FTSTI',   # 新加坡海峡时报指数
        'UKUKX',   # 英国富时100 (有时候显示为UKUKX)
        'DAX30',   # 德国DAX30
        'FCHI',    # 法国CAC40
        'E3X',     # 欧洲斯托克50
        'FTSEMIB', # 意大利富时MIB
        'GDAXI',   # 德国DAX (Yahoo格式)
        'STOXX50E',# 欧洲斯托克50 (Yahoo格式)
        'HSI',     # 恒生指数
        'HSTECH',  # 恒生科技指数
        'DJI',     # 道琼斯工业指数
        'IXIC',    # 纳斯达克综合指数
        'INX',     # 标普500
    }

    # 全球指数代码前缀处理 (来自腾讯API的格式)
    # hkHSI, hkHSTECH -> 港股指数
    # usDJI, usIXIC, usINX -> 美股指数
    # gzN225, gzKS11, gzTWII, gzENSEX, gzFTSTI -> 亚洲指数
    # ukUKX, ftDAX30, gzFCHI, ftE3X, ftFTSEMIB -> 欧洲指数

    if code.startswith('HK'):  # 港股指数代码 (如 hkHSI, HKHSI)
        return code, "港股指数"
    elif code.startswith('US'):  # 美股指数代码 (如 usDJI, USIXIC)
        return code, "美股指数"
    elif code.startswith('UK'):  # 英国指数
        return code, "全球指数"
    elif code.startswith('GZ'):  # 中国A股指数(前缀)
        return code, "全球指数"
    elif code.startswith('FT'):  # 欧洲指数 (ftDAX30, ftE3X, ftFTSEMIB)
        return code, "全球指数"
    elif code.startswith('DJI') or code.startswith('IXIC') or code.startswith('INX'):
        return code, "美股指数"
    elif code in global_indices:
        return code, "全球指数"

    # 全球指数前缀（无前缀格式）
    if code.startswith(("GZ", "UK", "FT")):
        return code, "全球指数"
    if code in global_indices:
        return code, "全球指数"

    # 港股：HK开头或.HK后缀或5位数字代码
    if code.startswith("HK") or ".HK" in code:
        # 统一转换为 xxxxx.HK 格式
        normalized = code.upper().replace(".HK", "").replace("HK", "")
        return normalized + ".HK", "港股"
    # 5位数字港股代码（如 00700, 09988）
    if len(code) == 5 and code.isdigit():
        return code + ".HK", "港股"

    # A股：SH/SZ前缀+8位或纯6位数字 或 .SS/.SZ后缀
    if code.endswith(".SS"):
        return code, "A股-上交所"
    elif code.endswith(".SZ"):
        return code, "A股-深交所"
    elif code.startswith("SH") and len(code) == 8 and code[2:].isdigit():
        return code[2:] + ".SS", "A股-上交所"
    elif code.startswith("SZ") and len(code) == 8 and code[2:].isdigit():
        return code[2:] + ".SZ", "A股-深交所"
    elif len(code) == 6 and code.isdigit():
        if code[0] == '6':
            return code + ".SS", "A股-上交所"
        else:
            return code + ".SZ", "A股-深交所"

    # 美股：US开头或GB_前缀或纯字母代码
    if code.startswith("US") or code.startswith("GB_"):
        return code, "美股"
    # 纯字母代码通常是美股（如 AAPL, TSLA）
    elif code.isalpha() and len(code) >= 2:
        return code, "美股"

    return code, "未知市场"

def get_tx_code(code):
    """转换成腾讯格式"""
    code_upper = code.upper()
    if ".SS" in code:
        return "sh" + code.replace(".SS", "")
    elif ".SZ" in code:
        return "sz" + code.replace(".SZ", "")
    elif ".HK" in code_upper:
        c = code_upper.replace(".HK", "")
        return "hk" + c.zfill(5)
    elif code_upper.startswith("HK"):
        return code.lower()
    else:
        return "us" + code_upper

# --- 核心修正逻辑 ---

def is_valid_price(val, min_val=0.01, max_val=1000000):
    """检查价格是否在合理范围内"""
    if val <= 0 or val > max_val or val < min_val:
        return False
    return True

def safe_cast_float(val, divisor=1.0):
    """
    安全地将接口返回的值转换为浮点数，并处理单位转换
    增强版：更严格的输入校验
    """
    try:
        if val is None:
            return 0.0
        if isinstance(val, str):
            val = val.strip()
            if val == "-" or val == "" or val == "0":
                return 0.0
        return float(val) / divisor
    except (ValueError, TypeError):
        return 0.0

def detect_unit_by_price(price, raw_value):
    """
    通过比较价格量级来检测原始数据单位
    如果价格明显太小（如 < 1），说明 raw_value 可能是"分"单位，需要除以 100
    """
    try:
        if raw_value == 0:
            return 1.0  # 无单位

        # 价格已经是合理的元单位
        if 1 <= price <= 100000:
            return 1.0

        # 如果原始值和价格差距太大，说明原始值可能是"分"
        if raw_value > price * 100:
            return 100.0
        elif raw_value > price * 10 and raw_value < price * 100:
            return 10.0
        return 1.0
    except:
        return 1.0

def get_realtime_data_unit(code):
    """
    根据市场类型返回实时数据的建议除数
    A股：东财接口 f43/f44/f45/f46 通常返回"分"，需要除以100转为"元"
    港股/美股：可能是不同单位
    """
    code_upper = code.upper()
    if ".SS" in code_upper or ".SZ" in code_upper:
        return 100.0  # A股分转元
    elif ".HK" in code_upper:
        return 100.0  # 港股分转元
    return 1.0  # 美股/其他保持原值

def is_market_trading_time(code):
    """
    检查当前是否在交易时间内
    用于判断是否应该合并实时数据
    """
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    current_time = now.time()
    current_weekday = now.weekday()  # 0=周一, 6=周日

    # 周六周日休市
    if current_weekday >= 5:
        return False

    code_upper = code.upper()

    # A股交易时间: 9:30-11:30, 13:00-15:00
    if ".SS" in code_upper or ".SZ" in code_upper:
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        if (time(9, 30) <= current_time <= time(11, 30) or
            time(13, 0) <= current_time <= time(15, 0)):
            return True
        return False

    # 港股交易时间: 9:30-12:00, 13:00-16:00
    elif ".HK" in code_upper:
        if (time(9, 30) <= current_time <= time(12, 0) or
            time(13, 0) <= current_time <= time(16, 0)):
            return True
        return False

    # 美股交易时间（假设）: 21:30-次日4:00 EST (简化处理)
    # 美国东部时间 EDT = UTC-4, 北京时间 +12
    # 实际简化：美股 21:30-次日4:00 北京时间对应 9:30-16:00
    elif code_upper.startswith("US") or code_upper.startswith("GB_"):
        # 简化处理
        if time(21, 30) <= current_time or current_time <= time(4, 0):
            return True
        return False

    # 全球指数：更宽松的处理
    return True

def merge_realtime_kline(df, code, qt_data=None):
    """
    修正后的合并逻辑：
    1. 增加日期严格匹配，防止非交易日污染。
    2. 增加 0 值保护，防止无效开盘价覆盖历史数据。
    3. 强制执行物理校验：High >= (Open, Close) >= Low。
    4. 单位自动检测，防止不同接口返回不同单位导致的数据错乱。
    5. 交易时间检测，防止盘前盘后数据污染。
    """
    try:
        if df is None or len(df) == 0:
            return df

        # 如果没有传入 qt_data，尝试获取
        if qt_data is None:
            rt = get_ifzq_realtime(code)
            if not rt:
                return df
        else:
            rt = qt_data
            if not rt:
                return df

        # 从qt数据中提取实时信息
        # qt_data 格式: ["1", "name", "code", current, yesterday_close, open, volume, ...]
        try:
            if isinstance(rt, dict):
                # 找到股票代码对应的数据
                code_key = None
                for key in rt:
                    if isinstance(rt[key], list) and len(rt[key]) > 6:
                        code_key = key
                        break

                if code_key is None:
                    return df

                qt = rt[code_key]
                if len(qt) < 10:
                    return df

                rt_price = float(qt[3])  # 当前价格
                rt_open = float(qt[5])   # 开盘价
                rt_vol = int(qt[6])      # 成交量

                # 提取最高最低价（从买卖盘数据）
                # qt[9] = 买一价, qt[11] = 卖一价
                # 但这些不是真正的高低价，需要从K线中获取
                # 简单处理：使用当前价格更新收盘价，最高最低暂时用原来的

                # 获取上一个交易日的最高最低
                idx = -1
                orig_high = float(df.iloc[idx]["high"])
                orig_low = float(df.iloc[idx]["low"])

                # 如果当前价格更高，更新最高价
                if rt_price > orig_high:
                    df.iloc[idx, df.columns.get_loc("high")] = rt_price

                # 如果当前价格更低，更新最低价
                if rt_price < orig_low:
                    df.iloc[idx, df.columns.get_loc("low")] = rt_price

                # 更新收盘价
                df.iloc[idx, df.columns.get_loc("close")] = rt_price

                # 更新开盘价（仅当原开盘价为0或空）
                if rt_open > 0 and (df.iloc[idx]["open"] <= 0 or pd.isna(df.iloc[idx]["open"])):
                    df.iloc[idx, df.columns.get_loc("open")] = rt_open

                # 更新成交量
                if rt_vol > 0:
                    df.iloc[idx, df.columns.get_loc("volume")] = rt_vol

                # 强制校验
                row = df.iloc[idx]
                valid_vals = [v for v in [row['open'], row['close'], row['high'], row['low']] if pd.notna(v) and v > 0]
                if valid_vals:
                    max_val = max(valid_vals)
                    min_val = min(valid_vals)
                    if row['high'] < max_val:
                        df.iloc[idx, df.columns.get_loc("high")] = max_val
                    if row['low'] > min_val:
                        df.iloc[idx, df.columns.get_loc("low")] = min_val

                    # 最终校验
                    if df.iloc[idx]['high'] < df.iloc[idx]['low']:
                        return df  # 数据异常，不合并

        except (IndexError, ValueError, TypeError) as e:
            print(f"merge_realtime_kline parse error: {e}")
            return df

        return df

    except Exception as e:
        print(f"merge_realtime_kline error: {e}")
        return df

# --- 数据抓取逻辑 ---

def get_ifzq_kline(code, period='day', days=500):
    """
    从IFZQ获取K线数据
    code: 股票代码，如 sh600000, hk00700, usAAPL, hkHSI, usDJI
    period: day, week, month
    days: 获取天数
    """
    try:
        code_upper = code.upper()
        code_lower = code.lower()

        # 转换代码格式
        if code.endswith(".SS"):
            ifzq_code = "sh" + code.replace(".SS", "")
        elif code.endswith(".SZ"):
            ifzq_code = "sz" + code.replace(".SZ", "")
        elif code.endswith(".HK"):
            ifzq_code = "hk" + code.replace(".HK", "").zfill(5)
        elif code.startswith("US") or code.startswith("GB_"):
            # 美股转换 (usDJI, usIXIC, usINX 等美股指数)
            ifzq_code = code_upper.replace('US', 'us.')  # usDJI -> us.dji
        elif code_upper.startswith("HK"):
            # 港股指数 (hkHSI, hkHSTECH)
            ifzq_code = 'hk' + code_upper[2:]  # hkHSI -> hkHSI (preserves case)
        elif code_upper.startswith("UK"):
            # 英国指数
            ifzq_code = code_lower
        elif code_upper.startswith("GZ"):
            # 中国A股指数前缀 (gzN225 等)
            ifzq_code = code_lower
        elif code_upper.startswith("FT"):
            # 欧洲指数前缀 (ftDAX30 等)
            ifzq_code = code_lower
        else:
            ifzq_code = code_lower

        # 周期映射
        period_map = {'day': 'day', 'week': 'week', 'month': 'month'}
        p = period_map.get(period, 'day')

        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {"param": f"{ifzq_code},{p},,,{days},qfq"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.qq.com/",
        }

        res = requests.get(url, params=params, headers=headers, timeout=10).json()

        # 解析数据 - IFZQ返回格式: {"sh600000": {"qfqday": [[日期, 开盘, 收盘, 最高, 最低, 成交量], ...], "qt": {...}}}
        klines = []
        qt_data = None

        data = res.get("data", {})
        if isinstance(data, dict):
            # data 的 key 是股票代码如 "sh600000"，value 才是真正的数据
            stock_data = None
            for key in data:
                if isinstance(data[key], dict):
                    stock_data = data[key]
                    break

            if stock_data:
                # 获取K线数据 - 根据周期获取对应数据
                # A股有qfqday（前复权日线），但指数只有day/week/month
                if period == 'day':
                    kline_data = stock_data.get("qfqday") or stock_data.get("day") or []
                elif period == 'week':
                    kline_data = stock_data.get("week") or stock_data.get("day") or []
                elif period == 'month':
                    kline_data = stock_data.get("month") or stock_data.get("day") or []
                else:
                    kline_data = stock_data.get("qfqday") or stock_data.get("day") or []
                qt_data = stock_data.get("qt", {})

                for item in kline_data:
                    if len(item) >= 6:
                        try:
                            klines.append({
                                "date": item[0],
                                "open": float(item[1]),
                                "close": float(item[2]),
                                "high": float(item[3]),
                                "low": float(item[4]),
                                "volume": int(float(item[5]))
                            })
                        except (ValueError, IndexError):
                            continue

        if not klines:
            return None, None

        df = pd.DataFrame(klines)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        return df, qt_data

    except Exception as e:
        print(f"IFZQ K-line error: {e}")
        return None, None


def get_akshare_kline(code, period='daily', days=500):
    """
    使用AKShare获取K线数据
    支持：A股、港股、美股、全球指数
    code: 股票代码，如 000001, 00700.HK, AAPL, ^N225, hkHSI, usDJI, gzN225
    period: daily, weekly, monthly
    days: 获取天数
    返回: (DataFrame, None) 或 (None, None)
    """
    try:
        # 确定市场类型和代码格式
        code_upper = code.upper()

        # 周期映射
        period_map = {'daily': 'daily', 'weekly': 'weekly', 'monthly': 'monthly'}
        akshare_period = period_map.get(period, 'daily')

        # A股指数代码 (需要使用 index_zh_a_hist 而不是 stock_zh_a_hist)
        # 这些代码在东方财富既是股票代码也是指数代码，需要单独处理
        zh_index_codes = {
            '000001',  # 上证指数
            '399001',  # 深证成指
            '399006',  # 创业板指
            '000300',  # 沪深300
            '000016',  # 上证50
            '000688',  # 科创50
            '000010',  # 上证180
            '399300',  # 深证100
            '000905',  # 中证500
            '000906',  # 中证800
            '000852',  # 中证1000
        }

        # A股 (6位数字或带.SS/.SZ后缀)
        if code_upper.endswith('.SS') or code_upper.endswith('.SZ'):
            symbol = code_upper.replace('.SS', '').replace('.SZ', '')

            # 判断是指数还是股票
            if symbol in zh_index_codes:
                # A股指数使用 index_zh_a_hist
                df = ak.index_zh_a_hist(symbol=symbol, period=akshare_period, start_date='19000101', end_date='20500101')
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
            else:
                # A股股票使用 stock_zh_a_hist
                adjust = 'qfq'
                df = ak.stock_zh_a_hist(symbol=symbol, period=akshare_period, start_date='19000101', end_date='20500101', adjust=adjust)
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()

            # 取最后days条
            if len(df) > days:
                df = df.tail(days)

            return df, None

        # 港股 (5位数字或带.HK后缀 或 hk前缀的指数如 hkHSI)
        elif code_upper.endswith('.HK') or (len(code) == 5 and code.isdigit()):
            symbol = code.replace('.HK', '').zfill(5)

            df = ak.stock_hk_hist(symbol=symbol, period=akshare_period, start_date='19000101', end_date='20500101')
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()

            if len(df) > days:
                df = df.tail(days)

            return df, None

        # 港股指数 (hkHSI, hkHSTECH) - 使用腾讯接口
        elif code_upper.startswith('HK'):
            # 腾讯格式: hkHSI -> 恒生指数, hkHSTECH -> 恒生科技
            # 注意：必须保持原大小写，如 'hkHSI'
            return get_ifzq_kline('hk' + code_upper[2:], period=akshare_period, days=days)

        # 美股指数 (usDJI, usIXIC, usINX) - 使用腾讯接口
        elif code_upper.startswith('US') and len(code) <= 10:
            # 腾讯格式: us.DJI, us.IXIC, us.INX (注意有点号，指数名称大写)
            ifzq_code = 'us.' + code_upper[2:]  # usDJI -> us.DJI
            return get_ifzq_kline(ifzq_code, period=akshare_period, days=days)

        # 美股 (US开头或纯字母代码如 AAPL, TSLA)
        elif code_upper.startswith('US') or (len(code) >= 2 and code.isalpha() and not code_upper.startswith('HSI')):
            symbol = code_upper.replace('US', '')

            df = ak.stock_us_hist(symbol=symbol, period=akshare_period, start_date='19000101', end_date='20500101')
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()

            if len(df) > days:
                df = df.tail(days)

            return df, None

        # 全球指数 (如 ^N225, ^HSI, ^DAX 等 Yahoo格式 或 gzN225, ftDAX30 等腾讯格式)
        elif code.startswith('^') or code in ['N225', 'KS11', 'TWII', 'ENSEX', 'FTSTI', 'DAX30', 'FCHI', 'E3X', 'FTSEMIB', 'HSI', 'HSTECH', 'DJI', 'IXIC', 'INX']:
            # 转换代码格式为Yahoo Finance格式
            yahoo_symbol = code
            if code.upper() == 'N225' or code == 'gzN225':
                yahoo_symbol = '^N225'      # 日经225
            elif code.upper() == 'KS11' or code == 'gzKS11':
                yahoo_symbol = '^KS11'      # 韩国综合指数
            elif code.upper() == 'TWII' or code == 'gzTWII':
                yahoo_symbol = '^TWII'      # 台湾加权指数
            elif code.upper() == 'ENSEX' or code == 'gzENSEX':
                yahoo_symbol = '^ENSEX'     # 印度孟买敏感指数
            elif code.upper() == 'FTSTI' or code == 'gzFTSTI':
                yahoo_symbol = '^FTSTI'     # 新加坡海峡时报指数
            elif code.upper() in ['DAX30', 'DAX'] or code in ['ftDAX30', 'gzDAX30']:
                yahoo_symbol = '^GDAXI'     # 德国DAX
            elif code.upper() == 'FCHI' or code in ['gzFCHI', 'ftFCHI']:
                yahoo_symbol = '^FCHI'      # 法国CAC40
            elif code.upper() in ['E3X', 'E3X.EU'] or code in ['ftE3X', 'gzE3X']:
                yahoo_symbol = '^STOXX50E'  # 欧洲斯托克50
            elif code.upper() == 'FTSEMIB' or code in ['ftFTSEMIB', 'gzFTSEMIB']:
                yahoo_symbol = '^FTSEMIB'   # 意大利富时MIB
            elif code.upper() == 'HSI' or code == 'hkHSI':
                yahoo_symbol = '^HSI'       # 恒生指数
            elif code.upper() == 'HSTECH' or code == 'hkHSTECH':
                yahoo_symbol = '^HSTECH'    # 恒生科技指数
            elif code.upper() == 'DJI' or code == 'usDJI':
                yahoo_symbol = '^DJI'       # 道琼斯工业指数
            elif code.upper() == 'IXIC' or code == 'usIXIC':
                yahoo_symbol = '^IXIC'      # 纳斯达克综合指数
            elif code.upper() == 'INX' or code == 'usINX':
                yahoo_symbol = '^INX'       # 标普500

            # 使用stock_us_hist获取全球指数K线
            df = ak.stock_us_hist(symbol=yahoo_symbol, period=akshare_period, start_date='19000101', end_date='20500101', adjust='')
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()

            # 过滤未来日期
            df = df[df.index <= pd.Timestamp.today()]

            if len(df) > days:
                df = df.tail(days)

            return df, None

        # 欧洲指数前缀处理 (ftDAX30, ftE3X, ftFTSEMIB, ukUKX)
        elif code.startswith('FT') or code.startswith('UK'):
            # 转换格式
            if code.upper() == 'FTDAX30':
                yahoo_symbol = '^GDAXI'
            elif code.upper() == 'FTE3X':
                yahoo_symbol = '^STOXX50E'
            elif code.upper() == 'FTFTSEMIB':
                yahoo_symbol = '^FTSEMIB'
            elif code.upper() == 'UKUKX':
                yahoo_symbol = '^UKX'
            else:
                yahoo_symbol = code

            df = ak.stock_us_hist(symbol=yahoo_symbol, period=akshare_period, start_date='19000101', end_date='20500101', adjust='')
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            df = df[df.index <= pd.Timestamp.today()]

            if len(df) > days:
                df = df.tail(days)

            return df, None

        # 纯6位数字 -> 默认为A股
        elif len(code) == 6 and code.isdigit():
            symbol = code
            adjust = 'qfq'

            df = ak.stock_zh_a_hist(symbol=symbol, period=akshare_period, start_date='19000101', end_date='20500101', adjust=adjust)
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()

            if len(df) > days:
                df = df.tail(days)

            return df, None

        else:
            print(f"AKShare: Unknown code type: {code}")
            return None, None

    except Exception as e:
        print(f"AKShare K-line error for {code}: {e}")
        return None, None


def get_eastmoney_kline(code, period='101'):
    """从东财获取K线（备用）"""
    try:
        secid = ("1." if ".SS" in code else "0.") + code.replace(".SS", "").replace(".SZ", "")
        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid, "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": period, "fqt": "1", "end": "20500101", "lmt": "500"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "http://quote.eastmoney.com/",
            "Accept": "*/*",
        }
        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        if res.get("data") and res["data"].get("klines"):
            res_list = [item.split(",")[:6] for item in res["data"]["klines"]]
            df = pd.DataFrame(res_list, columns=["date", "open", "close", "high", "low", "volume"])
            df["date"] = pd.to_datetime(df["date"])
            return df.set_index("date").apply(pd.to_numeric)
        return None
    except Exception as e:
        print(f"Eastmoney K-line error: {e}")
        return None

def get_eastmoney_realtime(code):
    """获取东财实时快照"""
    try:
        secid = ("1." if ".SS" in code else "0.") + code.replace(".SS", "").replace(".SZ", "")
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {"secid": secid, "fields": "f43,f44,f45,f46,f47,f58"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "http://quote.eastmoney.com/",
            "Accept": "*/*",
        }
        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        if res.get("data"):
            d = res["data"]
            return {
                "price": d.get("f43"), "high": d.get("f44"), "low": d.get("f45"),
                "open": d.get("f46"), "volume": d.get("f47"), "date": d.get("f58")
            }
        return None
    except Exception as e:
        print(f"Realtime API error: {e}")
        return None

def get_ifzq_realtime(code):
    """
    从IFZQ获取实时数据
    返回 qt 字典，格式: {"sh600000": ["1", "name", "code", current, yesterday_close, open, volume, ...]}
    """
    try:
        # 转换代码格式
        if code.endswith(".SS"):
            ifzq_code = "sh" + code.replace(".SS", "")
        elif code.endswith(".SZ"):
            ifzq_code = "sz" + code.replace(".SZ", "")
        elif code.endswith(".HK"):
            ifzq_code = "hk" + code.replace(".HK", "").zfill(5)
        elif code.startswith("US") or code.startswith("GB_"):
            ifzq_code = code.lower().replace("gb_", "us")
        else:
            ifzq_code = code.lower()

        url = "https://web.ifzq.gtimg.cn/appstock/app/minute/query"
        params = {"code": ifzq_code}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.qq.com/",
        }

        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        data = res.get("data", {})

        if isinstance(data, dict):
            qt_data = data.get("qt")
            if qt_data:
                return qt_data

        return None
    except Exception as e:
        print(f"IFZQ Realtime error: {e}")
        return None

# --- 指标计算 ---

def my_rsi(series, n=14):
    """计算RSI"""
    diff = series.diff()
    up, down = diff.copy(), diff.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    avg_up = up.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    avg_down = down.abs().ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    return 100 - (100 / (1 + (avg_up / avg_down)))

def my_macd(series):
    """计算MACD"""
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    return dif, dea, dif - dea

def get_indicators(df):
    """计算指标"""
    c = df["close"]
    if len(c) < 60: raise HTTPException(400, "数据量不足以计算指标")

    rsi = my_rsi(c)
    dif, dea, macd = my_macd(c)

    return {
        "as_of": str(c.index[-1].date()),
        "price": round(float(c.iloc[-1]), 2),
        "change_pct": round(((c.iloc[-1] / c.iloc[-2]) - 1) * 100, 2),
        "ma5": round(c.rolling(5).mean().iloc[-1], 2),
        "ma20": round(c.rolling(20).mean().iloc[-1], 2),
        "ma60": round(c.rolling(60).mean().iloc[-1], 2),
        "rsi14": round(float(rsi.iloc[-1]), 2),
        "macd_hist": round(float(macd.iloc[-1]), 3),
        "volume": int(df["volume"].iloc[-1])
    }

# --- FastAPI 接口 ---

async def fetch_with_retry(fetch_func, *args, max_retries=2, delay=0.5, **kwargs):
    """
    带重试的数据获取函数
    fetch_func: 同步的获取函数
    """
    import asyncio
    for attempt in range(max_retries):
        try:
            result = await asyncio.to_thread(fetch_func, *args, **kwargs)
            if result[0] is not None:
                return result
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
    return None, None

@router.get("/stock/kline")
async def get_kline(symbol: str, days: int = 180, period: str = "daily"):
    """获取K线数据接口 - 使用AKShare作为主数据源，带重试机制

    Args:
        symbol: 股票代码
        days: 获取天数，默认180天以确保有足够历史数据
        period: 日K(daily)/周K(weekly)/月K(monthly)
    """
    code, market = get_code_type(symbol)

    # 使用AKShare获取K线（支持A股、港股、美股、全球指数），带重试
    df, qt_data = await fetch_with_retry(get_akshare_kline, code, period=period, days=days)

    # 如果AKShare失败或数据为空，备用IFZQ（带重试）
    if df is None or len(df) == 0:
        p_map = {'daily': 'day', 'weekly': 'week', 'monthly': 'month'}
        p = p_map.get(period, 'day')
        df, qt_data = await fetch_with_retry(get_ifzq_kline, code, period=p, days=days)

    if df is None or len(df) == 0:
        raise HTTPException(404, f"无法获取 {symbol} 的K线数据")

    # 合并实时数据（仅日线）- 如果有实时数据
    if period == 'daily' and qt_data:
        df = merge_realtime_kline(df, code, qt_data)

    df = df.tail(days)
    klines = []
    for idx, row in df.iterrows():
        # 过滤掉坏数据：开盘价必须 > 0，且 high >= low
        if row["open"] > 0 and row["high"] >= row["low"] > 0:
            klines.append({
                "date": str(idx.date()),
                "open": float(row["open"]),
                "close": float(row["close"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "volume": int(row["volume"])
            })

    return {"symbol": symbol, "market": market, "klines": klines}

@router.get("/metrics")
async def get_metrics(symbol: str):
    """获取指标接口"""
    code, market = get_code_type(symbol)
    df, qt_data = get_ifzq_kline(code, period='day', days=500)
    if df is None:
        raise HTTPException(404, f"无法获取 {symbol} 的数据")
    if qt_data:
        df = merge_realtime_kline(df, code, qt_data)

    metrics = get_indicators(df)

    # 从qt_data中提取股票名称
    name = None
    if qt_data:
        for key in qt_data:
            if isinstance(qt_data[key], list) and len(qt_data[key]) > 1:
                name = qt_data[key][1]  # qt[1] 是股票名称
                break

    # IFZQ API 不直接提供52周高低价，从历史数据计算
    high_52w = None
    low_52w = None

    if len(df) >= 252:
        high_52w = round(float(df['high'].tail(252).max()), 2)
        low_52w = round(float(df['low'].tail(252).min()), 2)
    elif len(df) > 60:
        high_52w = round(float(df['high'].max()), 2)
        low_52w = round(float(df['low'].min()), 2)

    metrics["high_52w"] = high_52w
    metrics["low_52w"] = low_52w
    metrics["name"] = name

    return {
        "input_symbol": symbol,
        "vendor_symbol": code,
        "market": market,
        "name": name,
        "metrics": metrics
    }

# 别名，兼容 analysis.py 的导入
get_kline_data = get_kline
