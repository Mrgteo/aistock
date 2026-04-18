"""
股票分析数据获取模块 - 整合多源数据
支持：资金流、财务数据、风险数据、市场情绪、新闻数据
"""
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak
from pywencai import get

# 尝试导入ta库用于技术指标计算
try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False


class FundFlowDataFetcher:
    """资金流数据获取 - 使用akshare"""

    @staticmethod
    def get_individual_fund_flow(symbol: str, code: str) -> Dict[str, Any]:
        """
        获取个股资金流数据 (20日)

        Args:
            symbol: 股票代码如 "600519"
            code: 市场代码如 "sh" 或 "sz"

        Returns:
            资金流数据字典
        """
        try:
            # 主力净流入 = 超大单 + 大单净流入
            df = ak.stock_individual_fund_flow(symbol=symbol)

            if df is None or len(df) == 0:
                return {"error": "无资金流数据"}

            # 重命名列
            df.columns = [col.strip() for col in df.columns]

            # 查找相关列
            date_col = None
            close_col = None
            net_col = None
            main_col = None
            super_col = None
            large_col = None
            medium_col = None
            small_col = None

            for col in df.columns:
                col_lower = col.lower()
                if '日期' in col or 'date' in col_lower:
                    date_col = col
                elif '收盘' in col or 'close' in col_lower:
                    close_col = col
                elif '主力' in col and '净额' in col:
                    net_col = col
                elif '主力' in col:
                    main_col = col
                elif '超大' in col:
                    super_col = col
                elif '大单' in col:
                    large_col = col
                elif '中单' in col:
                    medium_col = col
                elif '小单' in col:
                    small_col = col

            # 取最近20个交易日
            df = df.head(20)

            result = {
                "dates": [],
                "close_prices": [],
                "main_net_flow": [],  # 主力净流入
                "main_net_ratio": [],  # 主力净流入占比
                "super_net_flow": [],  # 超大单
                "large_net_flow": [],  # 大单
                "medium_net_flow": [],  # 中单
                "small_net_flow": [],   # 小单
            }

            for _, row in df.iterrows():
                result["dates"].append(str(row[date_col])[:10] if date_col and row[date_col] else "")
                result["close_prices"].append(float(row[close_col]) if close_col and row[close_col] else 0)

                # 主力净额
                if net_col and row[net_col] is not None:
                    val = float(row[net_col])
                    result["main_net_flow"].append(val)
                    # 估算主力净占比 (需要有成交量数据)
                    result["main_net_ratio"].append(round(val / 10000, 2))  # 万元为单位
                else:
                    result["main_net_flow"].append(0)
                    result["main_net_ratio"].append(0)

                # 超大单
                if super_col and row[super_col] is not None:
                    result["super_net_flow"].append(float(row[super_col]))
                else:
                    result["super_net_flow"].append(0)

                # 大单
                if large_col and row[large_col] is not None:
                    result["large_net_flow"].append(float(row[large_col]))
                else:
                    result["large_net_flow"].append(0)

                # 中单
                if medium_col and row[medium_col] is not None:
                    result["medium_net_flow"].append(float(row[medium_col]))
                else:
                    result["medium_net_flow"].append(0)

                # 小单
                if small_col and row[small_col] is not None:
                    result["small_net_flow"].append(float(row[small_col]))
                else:
                    result["small_net_flow"].append(0)

            # 计算统计指标
            main_flows = result["main_net_flow"]
            positive_days = sum(1 for f in main_flows if f > 0)
            negative_days = sum(1 for f in main_flows if f < 0)

            result["statistics"] = {
                "cumulative_net_flow": round(sum(main_flows), 2),
                "avg_daily_net_flow": round(sum(main_flows) / len(main_flows), 2) if main_flows else 0,
                "positive_days": positive_days,
                "negative_days": negative_days,
                "max_net_flow": round(max(main_flows), 2) if main_flows else 0,
                "min_net_flow": round(min(main_flows), 2) if main_flows else 0,
                "flow_trend": "流入" if sum(main_flows) > 0 else "流出",
            }

            return result

        except Exception as e:
            return {"error": f"获取资金流数据失败: {str(e)}"}


class FinancialDataFetcher:
    """财务数据获取"""

    @staticmethod
    def get_financial_abstract(symbol: str) -> Dict[str, Any]:
        """
        获取财务摘要数据 (同花顺)

        Args:
            symbol: 股票代码如 "600519"

        Returns:
            财务数据字典
        """
        try:
            # 使用同花顺财务摘要
            df = ak.stock_financial_abstract_ths(symbol=symbol)

            if df is None or len(df) == 0:
                return {"error": "无财务数据"}

            # 转换为字典格式
            result = {
                "tables": {}
            }

            # 遍历所有列获取表格数据
            for col in df.columns:
                if '表' in str(col) or '报告' in str(col):
                    continue
                result["tables"][str(col)] = df[col].tolist()

            # 获取基本指标
            try:
                # 尝试获取利润表
                income = ak.stock_profit_sheet_by_report_em(symbol=symbol)
                if income is not None and len(income) > 0:
                    result["income_statement"] = income.head(8).to_dict()
            except:
                pass

            try:
                # 尝试获取资产负债表
                balance = ak.stock_balance_sheet_by_report_em(symbol=symbol)
                if balance is not None and len(balance) > 0:
                    result["balance_sheet"] = balance.head(8).to_dict()
            except:
                pass

            try:
                # 尝试获取现金流量表
                cashflow = ak.stock_cash_flowSheet_by_report_em(symbol=symbol)
                if cashflow is not None and len(cashflow) > 0:
                    result["cash_flow"] = cashflow.head(8).to_dict()
            except:
                pass

            return result

        except Exception as e:
            return {"error": f"获取财务数据失败: {str(e)}"}

    @staticmethod
    def get_financial_ratios(symbol: str) -> Dict[str, Any]:
        """
        获取财务比率数据

        Args:
            symbol: 股票代码如 "600519"

        Returns:
            财务比率字典
        """
        try:
            df = ak.stock_financial_abstract(symbol=symbol)

            if df is None or len(df) == 0:
                return {"error": "无财务比率数据"}

            return {
                "data": df.head(8).to_dict(),
                "dates": df.columns.tolist() if hasattr(df, 'columns') else []
            }

        except Exception as e:
            return {"error": f"获取财务比率失败: {str(e)}"}


class RiskDataFetcher:
    """风险数据获取 - 使用pywencai"""

    @staticmethod
    def get_unlock_info(symbol: str, code: str) -> Dict[str, Any]:
        """
        获取解禁数据

        Args:
            symbol: 股票代码如 "600519"
            code: 市场代码如 "sh" 或 "sz"

        Returns:
            解禁数据字典
        """
        try:
            # 使用pywencai查询解禁数据
            query_code = f"{symbol}.{code.upper()}"
            df = get(content=f"{symbol} 解禁股份", loop=True)

            if df is None or len(df) == 0:
                return {"data": [], "summary": "暂无解禁数据"}

            # 简化数据
            result = {
                "data": [],
                "summary": f"找到 {len(df)} 条解禁记录"
            }

            # 取前10条记录
            for _, row in df.head(10).iterrows():
                item = {}
                for col in df.columns:
                    val = row[col]
                    if pd.notna(val):
                        item[str(col)] = str(val)
                if item:
                    result["data"].append(item)

            return result

        except Exception as e:
            return {"error": f"获取解禁数据失败: {str(e)}"}

    @staticmethod
    def get_shareholder_reduction(symbol: str, code: str) -> Dict[str, Any]:
        """
        获取大股东减持数据

        Args:
            symbol: 股票代码如 "600519"
            code: 市场代码如 "sh" 或 "sz"

        Returns:
            减持数据字典
        """
        try:
            df = get(content=f"{symbol} 大股东减持", loop=True)

            if df is None or len(df) == 0:
                return {"data": [], "summary": "暂无减持数据"}

            result = {
                "data": [],
                "summary": f"找到 {len(df)} 条减持记录"
            }

            for _, row in df.head(10).iterrows():
                item = {}
                for col in df.columns:
                    val = row[col]
                    if pd.notna(val):
                        item[str(col)] = str(val)
                if item:
                    result["data"].append(item)

            return result

        except Exception as e:
            return {"error": f"获取减持数据失败: {str(e)}"}


class MarketSentimentDataFetcher:
    """市场情绪数据获取"""

    @staticmethod
    def get_arbr_indicator(symbol: str) -> Dict[str, Any]:
        """
        获取ARBR情绪指标

        Args:
            symbol: 股票代码如 "600519"

        Returns:
            ARBR数据字典
        """
        try:
            df = ak.stock_market_arbr(symbol=symbol)

            if df is None or len(df) == 0:
                return {"error": "无ARBR数据"}

            # 最近5天数据
            df = df.head(5)

            result = {
                "dates": [],
                "ar_values": [],
                "br_values": [],
            }

            for _, row in df.iterrows():
                if len(row) >= 2:
                    result["dates"].append(str(row.index[0])[:10] if hasattr(row.index[0], 'date') else str(row.index[0]))
                    result["ar_values"].append(float(row.iloc[0]) if pd.notna(row.iloc[0]) else 0)
                    result["br_values"].append(float(row.iloc[1]) if pd.notna(row.iloc[1]) else 0)

            # ARBR解读
            latest_ar = result["ar_values"][-1] if result["ar_values"] else 0
            latest_br = result["br_values"][-1] if result["br_values"] else 0

            if latest_ar > 150:
                sentiment = "市场过热，关注回调风险"
            elif latest_ar < 70:
                sentiment = "市场过冷，可能出现反弹机会"
            else:
                sentiment = "市场情绪中性"

            if latest_br > 300:
                sentiment += "，投资者意愿过热"
            elif latest_br < 50:
                sentiment += "，投资者意愿冷淡"

            result["latest_ar"] = latest_ar
            result["latest_br"] = latest_br
            result["sentiment"] = sentiment

            return result

        except Exception as e:
            return {"error": f"获取ARBR数据失败: {str(e)}"}

    @staticmethod
    def get_turnover_rate(symbol: str) -> Dict[str, Any]:
        """
        获取换手率数据 - 使用个股实时数据接口，更高效

        Args:
            symbol: 股票代码如 "600519"

        Returns:
            换手率数据
        """
        try:
            # 使用个股实时数据接口，比全市场查询快很多
            df = ak.stock_zh_a_spot_ths(symbol=symbol)

            if df is None or len(df) == 0:
                return {"error": "无换手率数据"}

            row = df.iloc[0]

            result = {
                "turnover_rate": float(row.get('换手率', 0)) if row.get('换手率') else 0,
                "volume_ratio": float(row.get('量比', 0)) if row.get('量比') else 0,
                "pe": float(row.get('市盈率', 0)) if row.get('市盈率') else 0,
                "pb": float(row.get('市净率', 0)) if row.get('市净率') else 0,
                "market_cap": float(row.get('总市值', 0)) if row.get('总市值') else 0,
                "float_cap": float(row.get('流通市值', 0)) if row.get('流通市值') else 0,
            }

            return result

        except Exception as e:
            # 回退方案：使用腾讯实时数据
            try:
                import requests
                url = f"http://qt.gtimg.cn/q=sh{symbol}"
                resp = requests.get(url, timeout=5)
                text = resp.text
                arr = text.split("~")
                if len(arr) > 40:
                    result = {
                        "turnover_rate": float(arr[38]) if arr[38] else 0,
                        "volume_ratio": 0,
                        "pe": float(arr[39]) if arr[39] else 0,
                        "pb": float(arr[46]) if arr[46] else 0,
                        "market_cap": float(arr[45]) if arr[45] else 0,
                        "float_cap": 0,
                    }
                    return result
            except:
                pass
            return {"error": f"获取换手率数据失败: {str(e)}"}

    @staticmethod
    def get_margin_trading(symbol: str) -> Dict[str, Any]:
        """
        获取融资融券数据

        Args:
            symbol: 股票代码如 "600519"

        Returns:
            融资融券数据
        """
        try:
            df = ak.stock_margin_detail(symbol=symbol)

            if df is None or len(df) == 0:
                return {"error": "无融资融券数据"}

            # 最近5条记录
            df = df.head(5)

            result = {
                "dates": [],
                "margin_balance": [],  # 融资余额
                "short_balance": [],    # 融券余额
                "margin_net": [],       # 融资净买入
            }

            for _, row in df.iterrows():
                result["dates"].append(str(row['日期'])[:10] if '日期' in row else "")
                result["margin_balance"].append(float(row['融资余额']) if '融资余额' in row and pd.notna(row['融资余额']) else 0)
                result["short_balance"].append(float(row['融券余额']) if '融券余额' in row and pd.notna(row['融券余额']) else 0)
                result["margin_net"].append(float(row['融资净买入']) if '融资净买入' in row and pd.notna(row['融资净买入']) else 0)

            return result

        except Exception as e:
            return {"error": f"获取融资融券数据失败: {str(e)}"}


class NewsDataFetcher:
    """新闻数据获取"""

    @staticmethod
    def get_stock_news(symbol: str, code: str, limit: int = 30) -> Dict[str, Any]:
        """
        获取股票新闻 (多源)

        Args:
            symbol: 股票代码如 "600519"
            code: 市场代码如 "sh" 或 "sz"
            limit: 返回新闻数量

        Returns:
            新闻数据字典
        """
        result = {
            "news_list": [],
            "sources": []
        }

        # 1. 东方财富新闻
        try:
            df = ak.stock_news_em(symbol=symbol)
            if df is not None and len(df) > 0:
                for _, row in df.head(limit).iterrows():
                    result["news_list"].append({
                        "title": str(row.get('新闻标题', '')),
                        "content": str(row.get('新闻内容', ''))[:500] if row.get('新闻内容') else '',
                        "date": str(row.get('发布时间', ''))[:19],
                        "source": "东方财富"
                    })
                result["sources"].append("eastmoney")
        except Exception as e:
            pass

        # 2. 新浪财经新闻
        try:
            df = ak.stock_news_sina(symbol=symbol)
            if df is not None and len(df) > 0:
                for _, row in df.head(limit).iterrows():
                    result["news_list"].append({
                        "title": str(row.get('新闻标题', '')),
                        "content": str(row.get('新闻内容', ''))[:500] if row.get('新闻内容') else '',
                        "date": str(row.get('发布时间', ''))[:19],
                        "source": "新浪财经"
                    })
                result["sources"].append("sina")
        except Exception as e:
            pass

        # 去重 (根据标题)
        seen = set()
        unique_news = []
        for news in result["news_list"]:
            if news["title"] not in seen:
                seen.add(news["title"])
                unique_news.append(news)

        result["news_list"] = unique_news[:limit]
        result["total_count"] = len(result["news_list"])

        return result

    @staticmethod
    def get_cls_news(symbol: str = None, limit: int = 30) -> Dict[str, Any]:
        """
        获取财联社新闻

        Args:
            symbol: 股票代码 (可选)
            limit: 返回数量

        Returns:
            财联社新闻数据
        """
        try:
            df = ak.stock_news_cls()

            if df is None or len(df) == 0:
                return {"error": "无财联社新闻"}

            result = {
                "news_list": [],
                "total_count": 0
            }

            for _, row in df.head(limit).iterrows():
                title = str(row.get('资讯标题', ''))
                content = str(row.get('资讯内容', ''))[:500] if row.get('资讯内容') else ''

                # 如果指定了股票代码，只返回相关的
                if symbol:
                    if symbol in title or symbol in content:
                        result["news_list"].append({
                            "title": title,
                            "content": content,
                            "date": str(row.get('发布时间', ''))[:19],
                            "source": "财联社"
                        })
                else:
                    result["news_list"].append({
                        "title": title,
                        "content": content,
                        "date": str(row.get('发布时间', ''))[:19],
                        "source": "财联社"
                    })

            result["total_count"] = len(result["news_list"])
            return result

        except Exception as e:
            return {"error": f"获取财联社新闻失败: {str(e)}"}


class TechnicalDataFetcher:
    """技术指标数据增强"""

    @staticmethod
    def calculate_advanced_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算高级技术指标 (使用ta库)

        Args:
            df: 包含 high, low, close, volume 的DataFrame

        Returns:
            高级技术指标字典
        """
        if df is None or len(df) < 20:
            return {"error": "数据量不足"}

        result = {}

        if TA_AVAILABLE:
            high = df['high']
            low = df['low']
            close = df['close']
            volume = df['volume']

            # KDJ指标
            try:
                from ta.momentum import StochasticOscillator
                stoch = StochasticOscillator(high=high, low=low, close=close, n=14, d=3)
                result['kdj_k'] = round(float(stoch.stoch_signal().iloc[-1]), 2)
                result['kdj_d'] = round(float(stoch.stoch_d().iloc[-1]), 2)
                result['kdj_j'] = round(float(stoch.stoch_k().iloc[-1] * 3 - stoch.stoch_d().iloc[-1] * 2 + stoch.stoch_signal().iloc[-1]), 2)
            except:
                pass

            # 布林带
            try:
                from ta.volatility import BollingerBands
                bb = BollingerBands(close=close, n=20, ndev=2)
                result['bb_upper'] = round(float(bb.bollinger_hband().iloc[-1]), 2)
                result['bb_middle'] = round(float(bb.bollinger_mavg().iloc[-1]), 2)
                result['bb_lower'] = round(float(bb.bollinger_lband().iloc[-1]), 2)
                # 布林带位置 (0-100)
                bb_position = (close.iloc[-1] - result['bb_lower']) / (result['bb_upper'] - result['bb_lower']) * 100
                result['bb_position'] = round(float(bb_position), 2)
            except:
                pass

            # ATR (Average True Range)
            try:
                from ta.volatility import AverageTrueRange
                atr = AverageTrueRange(high=high, low=low, close=close, n=14)
                result['atr'] = round(float(atr.average_true_range().iloc[-1]), 2)
            except:
                pass

            # MACD (已有一部分，这里补充完整)
            try:
                from ta.trend import MACD
                macd = MACD(close=close)
                result['macd_dif'] = round(float(macd.macd_diff().iloc[-1]), 3)
                result['macd_dea'] = round(float(macd.macd_signal().iloc[-1]), 3)
                result['macd_hist'] = round(float(macd.macd().iloc[-1]), 3)
            except:
                pass

        # 量比 (手动计算)
        try:
            vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
            result['volume_ratio'] = round(float(df['volume'].iloc[-1] / vol_ma5), 2) if vol_ma5 > 0 else 0
        except:
            pass

        # 5日均量
        try:
            result['volume_ma5'] = round(float(df['volume'].tail(5).mean()), 0)
        except:
            pass

        return result


class StockDataFetcher:
    """综合股票数据获取器"""

    def __init__(self, symbol: str = None, code: str = None):
        self.symbol = symbol
        self.code = code

    def fetch_all_data(self) -> Dict[str, Any]:
        """
        获取所有分析所需数据

        Returns:
            完整数据字典
        """
        result = {
            "symbol": self.symbol,
            "code": self.code,
            "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": {}
        }

        # 1. 资金流数据
        try:
            result["data"]["fund_flow"] = FundFlowDataFetcher.get_individual_fund_flow(self.symbol, self.code)
        except Exception as e:
            result["data"]["fund_flow"] = {"error": str(e)}

        # 2. 财务数据 (异步获取，不阻塞)
        # 注意：财务数据获取较慢，单独调用

        # 3. 风险数据
        try:
            result["data"]["risk_unlock"] = RiskDataFetcher.get_unlock_info(self.symbol, self.code)
        except Exception as e:
            result["data"]["risk_unlock"] = {"error": str(e)}

        try:
            result["data"]["risk_reduction"] = RiskDataFetcher.get_shareholder_reduction(self.symbol, self.code)
        except Exception as e:
            result["data"]["risk_reduction"] = {"error": str(e)}

        # 4. 情绪数据
        try:
            result["data"]["sentiment_arbr"] = MarketSentimentDataFetcher.get_arbr_indicator(self.symbol)
        except Exception as e:
            result["data"]["sentiment_arbr"] = {"error": str(e)}

        try:
            result["data"]["sentiment_turnover"] = MarketSentimentDataFetcher.get_turnover_rate(self.symbol)
        except Exception as e:
            result["data"]["sentiment_turnover"] = {"error": str(e)}

        try:
            result["data"]["sentiment_margin"] = MarketSentimentDataFetcher.get_margin_trading(self.symbol)
        except Exception as e:
            result["data"]["sentiment_margin"] = {"error": str(e)}

        # 5. 新闻数据
        try:
            result["data"]["news"] = NewsDataFetcher.get_stock_news(self.symbol, self.code, limit=20)
        except Exception as e:
            result["data"]["news"] = {"error": str(e)}

        return result

    def fetch_financial_data(self) -> Dict[str, Any]:
        """
        单独获取财务数据 (因为较慢)

        Returns:
            财务数据字典
        """
        try:
            financial = FinancialDataFetcher.get_financial_abstract(self.symbol)
            ratios = FinancialDataFetcher.get_financial_ratios(self.symbol)

            return {
                "symbol": self.symbol,
                "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "financial": financial,
                "ratios": ratios
            }
        except Exception as e:
            return {"error": str(e)}


def fetch_all_analysis_data(symbol: str, code: str) -> Dict[str, Any]:
    """
    便捷函数：获取所有分析数据

    Args:
        symbol: 股票代码如 "600519"
        code: 市场代码如 "sh" 或 "sz"

    Returns:
        完整数据字典
    """
    fetcher = StockDataFetcher(symbol, code)
    return fetcher.fetch_all_data()


async def fetch_all_analysis_data_async(symbol: str, code: str) -> Dict[str, Any]:
    """
    异步获取所有分析数据 - 使用线程池避免阻塞

    Args:
        symbol: 股票代码如 "600519"
        code: 市场代码如 "sh" 或 "sz"

    Returns:
        完整数据字典
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    result = {
        "symbol": symbol,
        "code": code,
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data": {}
    }

    def fetch_fund_flow():
        try:
            return ("fund_flow", FundFlowDataFetcher.get_individual_fund_flow(symbol, code))
        except Exception as e:
            return ("fund_flow", {"error": str(e)})

    def fetch_risk_unlock():
        try:
            return ("risk_unlock", RiskDataFetcher.get_unlock_info(symbol, code))
        except Exception as e:
            return ("risk_unlock", {"error": str(e)})

    def fetch_risk_reduction():
        try:
            return ("risk_reduction", RiskDataFetcher.get_shareholder_reduction(symbol, code))
        except Exception as e:
            return ("risk_reduction", {"error": str(e)})

    def fetch_sentiment_arbr():
        try:
            return ("sentiment_arbr", MarketSentimentDataFetcher.get_arbr_indicator(symbol))
        except Exception as e:
            return ("sentiment_arbr", {"error": str(e)})

    def fetch_sentiment_turnover():
        try:
            return ("sentiment_turnover", MarketSentimentDataFetcher.get_turnover_rate(symbol))
        except Exception as e:
            return ("sentiment_turnover", {"error": str(e)})

    def fetch_sentiment_margin():
        try:
            return ("sentiment_margin", MarketSentimentDataFetcher.get_margin_trading(symbol))
        except Exception as e:
            return ("sentiment_margin", {"error": str(e)})

    def fetch_news():
        try:
            return ("news", NewsDataFetcher.get_stock_news(symbol, code, limit=20))
        except Exception as e:
            return ("news", {"error": str(e)})

    # 使用线程池并行执行所有数据获取
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = [
            executor.submit(fetch_fund_flow),
            executor.submit(fetch_risk_unlock),
            executor.submit(fetch_risk_reduction),
            executor.submit(fetch_sentiment_arbr),
            executor.submit(fetch_sentiment_turnover),
            executor.submit(fetch_sentiment_margin),
            executor.submit(fetch_news),
        ]

        for future in futures:
            try:
                key, value = future.result(timeout=30)
                result["data"][key] = value
            except Exception as e:
                pass

    return result


def format_fund_flow_for_prompt(fund_flow_data: Dict) -> str:
    """格式化资金流数据为提示词文本"""
    if not fund_flow_data or fund_flow_data.get("error"):
        return "暂无资金流数据"
    stats = fund_flow_data.get("statistics", {})
    dates = fund_flow_data.get("dates", [])
    flows = fund_flow_data.get("main_net_flow", [])
    if not dates or not flows:
        return "暂无资金流数据"
    text = f"【资金流分析】\n最近 {len(dates)} 个交易日主力资金流向统计：\n"
    text += f"- 累计净流入：{stats.get('cumulative_net_flow', 0):.2f} 万元\n"
    text += f"- 日均净流入：{stats.get('avg_daily_net_flow', 0):.2f} 万元\n"
    text += f"- 资金流入天数：{stats.get('positive_days', 0)} 天\n"
    text += f"- 资金流出天数：{stats.get('negative_days', 0)} 天\n"
    text += f"- 资金流向趋势：{stats.get('flow_trend', '未知')}\n\n"
    text += "每日资金流详情：\n"
    for date, flow in zip(dates[-7:], flows[-7:]):
        trend = "↑流入" if flow > 0 else "↓流出"
        text += f"- {date}：主力净流入 {flow:.2f} 万元 {trend}\n"
    return text


def format_news_for_prompt(news_data: Dict, limit: int = 10) -> str:
    """格式化新闻数据为提示词文本"""
    if not news_data or news_data.get("error"):
        return "暂无新闻数据"
    news_list = news_data.get("news_list", [])
    if not news_list:
        return "暂无新闻数据"
    text = f"【最新新闻】(共 {len(news_list)} 条)\n\n"
    for i, news in enumerate(news_list[:limit]):
        title = news.get("title", "")
        date = news.get("date", "")[:10]
        source = news.get("source", "")
        content = news.get("content", "")
        text += f"{i+1}. {title}\n   时间：{date} | 来源：{source}\n"
        if content:
            text += f"   摘要：{content[:200]}...\n"
        text += "\n"
    return text


def format_risk_for_prompt(risk_unlock: Dict, risk_reduction: Dict) -> str:
    """格式化风险数据为提示词文本"""
    text = "【风险数据】\n\n"
    if risk_unlock and not risk_unlock.get("error"):
        summary = risk_unlock.get("summary", "")
        data = risk_unlock.get("data", [])
        text += f"【解禁风险】{summary}\n"
        if data:
            for item in data[:3]:
                text += f"- {str(item)[:200]}\n"
        text += "\n"
    else:
        text += "【解禁风险】暂无数据\n\n"
    if risk_reduction and not risk_reduction.get("error"):
        summary = risk_reduction.get("summary", "")
        data = risk_reduction.get("data", [])
        text += f"【减持风险】{summary}\n"
        if data:
            for item in data[:3]:
                text += f"- {str(item)[:200]}\n"
    else:
        text += "【减持风险】暂无数据\n"
    return text


def format_sentiment_for_prompt(sentiment_arbr: Dict, sentiment_turnover: Dict, sentiment_margin: Dict) -> str:
    """格式化情绪数据为提示词文本"""
    text = "【市场情绪数据】\n\n"
    if sentiment_arbr and not sentiment_arbr.get("error"):
        ar = sentiment_arbr.get("latest_ar", 0)
        br = sentiment_arbr.get("latest_br", 0)
        sentiment = sentiment_arbr.get("sentiment", "")
        dates = sentiment_arbr.get("dates", [])
        ar_values = sentiment_arbr.get("ar_values", [])
        br_values = sentiment_arbr.get("br_values", [])
        text += f"【ARBR指标】\n- AR人气指标：{ar:.2f}\n- BR意愿指标：{br:.2f}\n- 情绪判断：{sentiment}\n"
        if dates and ar_values and br_values:
            text += "\n近5日ARBR走势：\n"
            for d, a, b in zip(dates[-5:], ar_values[-5:], br_values[-5:]):
                text += f"- {d}: AR={a:.2f}, BR={b:.2f}\n"
        text += "\n"
    else:
        text += "【ARBR指标】暂无数据\n\n"
    if sentiment_turnover and not sentiment_turnover.get("error"):
        turnover = sentiment_turnover.get("turnover_rate", 0)
        vol_ratio = sentiment_turnover.get("volume_ratio", 0)
        pe = sentiment_turnover.get("pe", 0)
        pb = sentiment_turnover.get("pb", 0)
        mkt_cap = sentiment_turnover.get("market_cap", 0)
        text += f"【交易活跃度】\n- 换手率：{turnover:.2f}%\n- 量比：{vol_ratio:.2f}\n"
        text += f"- 市盈率(PE)：{pe:.2f}\n- 市净率(PB)：{pb:.2f}\n"
        text += f"- 总市值：{mkt_cap/1e8:.2f} 亿元\n\n"
    else:
        text += "【交易活跃度】暂无数据\n\n"
    if sentiment_margin and not sentiment_margin.get("error"):
        dates = sentiment_margin.get("dates", [])
        margin_balances = sentiment_margin.get("margin_balance", [])
        text += "【融资融券】\n"
        if dates and margin_balances:
            text += f"- 最新融资余额：{margin_balances[0]/1e4:.2f} 亿元\n- 统计日期：{dates[0]}\n"
        else:
            text += "暂无融资融券数据\n"
    else:
        text += "【融资融券】暂无数据\n"
    return text
