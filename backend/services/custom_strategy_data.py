"""
定制量化策略数据获取模块
整合5种选股策略的数据获取：主力选股、低价擒牛、小市值、净利增长、低估值
基于 pywencai (同花顺问财) 获取数据
"""

import pywencai
import pandas as pd
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

warnings.filterwarnings('ignore', category=DeprecationWarning)


class CustomStrategyData:
    """定制量化策略数据获取类"""

    def __init__(self):
        pass

    # ========== 主力选股 ==========
    def get_main_force_stocks(
        self,
        start_date: str = None,
        days_ago: int = 90,
        min_market_cap: float = 0,
        max_market_cap: float = 500,
        top_n: int = 20
    ) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        获取主力资金净流入前N名股票

        Args:
            start_date: 开始日期，格式如"2025年10月1日"
            days_ago: 距今天数
            min_market_cap: 最小市值(亿)
            max_market_cap: 最大市值(亿)
            top_n: 返回前N只

        Returns:
            (success, dataframe, message)
        """
        try:
            if not start_date:
                date_obj = datetime.now() - timedelta(days=days_ago)
                start_date = f"{date_obj.year}年{date_obj.month}月{date_obj.day}日"

            queries = [
                f"{start_date}以来主力资金净流入，并计算区间涨跌幅，市值{min_market_cap}-{max_market_cap}亿，非科创非st，"
                f"所属同花顺行业，总市值，净利润，营收，市盈率，市净率",

                f"{start_date}以来主力资金净流入前100名，并计算区间涨跌幅，市值{min_market_cap}-{max_market_cap}亿，非st非科创板，所属行业，总市值",
            ]

            for query in queries:
                try:
                    result = pywencai.get(query=query, loop=True)
                    if result is None:
                        continue
                    df = self._to_dataframe(result)
                    if df is None or df.empty:
                        continue

                    # 查找主力资金列并排序
                    main_fund_col = self._find_column(df, ['主力资金净流入', '区间主力资金净流入', '主力净流入', '主力资金流向'])
                    if main_fund_col:
                        df[main_fund_col] = pd.to_numeric(df[main_fund_col], errors='coerce')
                        df = df.nlargest(top_n, main_fund_col)

                    return True, df, f"成功获取{len(df)}只主力资金流入股票"
                except Exception:
                    continue

            return False, None, "主力选股查询失败"

        except Exception as e:
            return False, None, f"主力选股失败: {str(e)}"

    # ========== 低价擒牛 ==========
    def get_low_price_stocks(self, top_n: int = 5) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        获取低价高成长股票
        策略: 股价<10元 + 净利润增长率>=100% + 沪深A股
        """
        try:
            query = (
                "股价<10元，"
                "净利润增长率(净利润同比增长率)≥100%，"
                "非st，非科创板，非创业板，"
                "沪深A股，"
                "成交额由小至大排名"
            )

            result = pywencai.get(query=query, loop=True)
            if result is None:
                return False, None, "问财接口返回None"

            df = self._to_dataframe(result)
            if df is None or df.empty:
                return False, None, "未获取到符合条件的股票"

            selected = df.head(top_n) if len(df) > top_n else df
            return True, selected, f"成功筛选出{len(selected)}只低价高成长股票"

        except Exception as e:
            return False, None, f"低价擒牛选股失败: {str(e)}"

    # ========== 小市值策略 ==========
    def get_small_cap_stocks(self, top_n: int = 5) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        获取小市值高成长股票
        策略: 总市值<=50亿 + 营收增长>=10% + 净利增长>=100%
        """
        try:
            query = (
                "总市值≤50亿，"
                "营收增长率≥10%，"
                "净利润增长率(净利润同比增长率)≥100%，"
                "沪深A股，非ST，非创业板，非科创板，"
                "总市值由小至大排名"
            )

            result = pywencai.get(query=query, loop=True)
            if result is None or result.empty:
                return False, None, "未找到符合条件的股票"

            selected = result.head(top_n) if len(result) > top_n else result
            return True, selected, f"成功获取{len(selected)}只小市值股票"

        except Exception as e:
            return False, None, f"小市值选股失败: {str(e)}"

    # ========== 净利增长 ==========
    def get_profit_growth_stocks(self, top_n: int = 5) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        获取净利增长股票
        策略: 净利润增长率>=10% + 深圳A股
        """
        try:
            query = (
                "净利润增长率(净利润同比增长率)≥10%，"
                "非科创板，非创业板，非ST，"
                "深圳A股，"
                "成交额由小至大排名"
            )

            result = pywencai.get(query=query, loop=True)
            if result is None or result.empty:
                return False, None, "未找到符合条件的股票"

            selected = result.head(top_n) if len(result) > top_n else result
            return True, selected, f"成功获取{len(selected)}只净利增长股票"

        except Exception as e:
            return False, None, f"净利增长选股失败: {str(e)}"

    # ========== 低估值策略 ==========
    def get_value_stocks(self, top_n: int = 10) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        获取低估值优质股票
        策略: PE<=20 + PB<=1.5 + 股息率>=1% + 资产负债率<=30%
        """
        try:
            query = (
                "市盈率小于等于20，"
                "市净率小于等于1.5，"
                "股息率大于等于1%，"
                "资产负债率小于等于30%，"
                "非st，非科创板，非创业板，"
                "按流通市值由小到大排名"
            )

            result = pywencai.get(query=query, loop=True)
            if result is None:
                return False, None, "问财接口返回None"

            df = self._to_dataframe(result)
            if df is None or df.empty:
                return False, None, "未获取到符合条件的股票"

            selected = df.head(top_n) if len(df) > top_n else df
            return True, selected, f"成功筛选出{len(selected)}只低估值优质股票"

        except Exception as e:
            return False, None, f"低估值选股失败: {str(e)}"

    # ========== 工具方法 ==========
    def _to_dataframe(self, result) -> Optional[pd.DataFrame]:
        """将pywencai返回结果转换为DataFrame"""
        try:
            if isinstance(result, pd.DataFrame):
                return result
            elif isinstance(result, dict):
                if 'tableV1' in result:
                    table = result['tableV1']
                    if isinstance(table, pd.DataFrame):
                        return table
                    elif isinstance(table, list):
                        return pd.DataFrame(table)
                return pd.DataFrame([result]) if result else None
            elif isinstance(result, list):
                return pd.DataFrame(result)
            return None
        except Exception:
            return None

    def _find_column(self, df: pd.DataFrame, patterns: List[str]) -> Optional[str]:
        """查找匹配的列名"""
        for pattern in patterns:
            for col in df.columns:
                if pattern in col:
                    return col
        return None

    def _clean_code(self, code) -> str:
        """清理股票代码"""
        if isinstance(code, str):
            return code.split('.')[0]
        return str(code)

    def df_to_dict_list(self, df: Optional[pd.DataFrame], top_n: int = None) -> List[Dict]:
        """将DataFrame转换为字典列表"""
        if df is None or df.empty:
            return []

        result = []
        for idx, row in df.head(top_n if top_n else len(df)).iterrows():
            item = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    item[col] = None
                else:
                    item[col] = val
            result.append(item)
        return result


# 全局实例
_custom_strategy_data: Optional[CustomStrategyData] = None


def get_custom_strategy_data() -> CustomStrategyData:
    """获取策略数据实例"""
    global _custom_strategy_data
    if _custom_strategy_data is None:
        _custom_strategy_data = CustomStrategyData()
    return _custom_strategy_data
