"""
股票筛选服务 - 基于同花顺问财(pywencai)
"""
import pywencai
import pandas as pd
import warnings
from typing import List, Dict, Any, Optional

# 忽略Node.js警告
warnings.filterwarnings('ignore', category=DeprecationWarning)


class StockScreener:
    """股票筛选器 - 使用同花顺问财自然语言接口"""

    def __init__(self):
        pass

    def screen(self, query: str, page_size: int = 50) -> Dict[str, Any]:
        """
        筛选A股股票（使用同花顺问财自然语言）

        Args:
            query: 问财格式的自然语言查询
            page_size: 返回结果数量上限

        Returns:
            包含筛选结果的字典
        """
        try:
            result = pywencai.get(query=query, loop=True)

            if result is None or (isinstance(result, pd.DataFrame) and result.empty):
                return {
                    "code": 0,
                    "message": "success",
                    "data": {"columns": [], "rows": [], "count": 0}
                }

            # pywencai返回pandas DataFrame
            if isinstance(result, pd.DataFrame):
                columns = result.columns.tolist()

                # 映射列为更友好的英文名
                column_map = {
                    "股票代码": "code",
                    "股票简称": "name",
                    "最新价": "price",
                    "最新涨跌幅": "change_pct",
                    "涨跌幅:前复权[20260324]": "change_pct_adj",
                    "涨跌[20260324]": "change",
                    "振幅[20260324]": "amplitude",
                    "成交量[20260324]": "volume",
                    "成交额[20260324]": "amount",
                    "换手率[20260324]": "turnover_rate",
                    "量比": "volume_ratio",
                    "委比": "buy_sell_ratio",
                    "市盈率(动态)": "pe",
                    "市净率": "pb",
                    "总市值": "total_market_cap",
                    "流通市值": "float_market_cap",
                    "market_code": "market_code",
                    "code": "原始代码",
                }

                # 构建映射后的列名
                mapped_columns = []
                for col in columns:
                    mapped_columns.append({
                        "cn": col,
                        "en": column_map.get(col, col.lower())
                    })

                # 转换数据为行列表
                rows_data = []
                for _, row in result.head(page_size).iterrows():
                    row_dict = {}
                    for col in columns:
                        en_key = column_map.get(col, col.lower())
                        val = row[col]
                        # 处理numpy/pandas类型
                        if pd.isna(val):
                            row_dict[en_key] = None
                        else:
                            row_dict[en_key] = val
                    rows_data.append(row_dict)

                return {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "columns": mapped_columns,
                        "rows": rows_data,
                        "count": len(rows_data)
                    }
                }

            # 如果是dict类型
            if isinstance(result, dict):
                return {
                    "code": 0,
                    "message": "success",
                    "data": {"columns": [], "rows": [], "count": 0}
                }

            return {
                "code": -1,
                "message": "返回数据格式异常",
                "data": {"columns": [], "rows": [], "count": 0}
            }

        except Exception as e:
            return {
                "code": -1,
                "message": f"筛选失败: {str(e)}",
                "data": {"columns": [], "rows": [], "count": 0}
            }

    def hot_strategies(self) -> List[Dict[str, Any]]:
        """
        获取热门选股策略（同花顺问财格式）

        Returns:
            热门策略列表
        """
        # 预定义热门策略（同花顺问财格式）
        strategies = [
            {"rank": 1, "question": "MACD金叉"},
            {"rank": 2, "question": "KDJ金叉"},
            {"rank": 3, "question": "换手率大于5%"},
            {"rank": 4, "question": "量比大于2"},
            {"rank": 5, "question": "涨幅大于5%"},
            {"rank": 6, "question": "跌幅大于3%"},
            {"rank": 7, "question": "市盈率小于30"},
            {"rank": 8, "question": "市净率小于3"},
            {"rank": 9, "question": "流通市值小于50亿"},
            {"rank": 10, "question": "股价小于10元"},
            {"rank": 11, "question": "RSI低于30"},
            {"rank": 12, "question": "RSI超买70"},
            {"rank": 13, "question": "创历史新高"},
            {"rank": 14, "question": "创历史新低"},
            {"rank": 15, "question": "10日内有涨停"},
            {"rank": 16, "question": "突破年线"},
            {"rank": 17, "question": "站在所有均线上方"},
            {"rank": 18, "question": "5日均线上穿10日均线"},
            {"rank": 19, "question": "今日低开高走"},
            {"rank": 20, "question": "今日放量上涨"},
        ]
        return strategies


# 全局实例
_screener: Optional[StockScreener] = None


def get_screener() -> StockScreener:
    """获取筛选器实例"""
    global _screener
    if _screener is None:
        _screener = StockScreener()
    return _screener
