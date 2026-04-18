"""
定制量化策略引擎
整合5种选股策略：主力选股、低价擒牛、小市值、净利增长、低估值
"""

from backend.services.custom_strategy_data import get_custom_strategy_data, CustomStrategyData
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class CustomStrategyEngine:
    """定制量化策略引擎"""

    def __init__(self):
        self.data = get_custom_strategy_data()
        logger.info("[定制策略] 引擎初始化完成")

    # ========== 主力选股 ==========
    def run_main_force(self, start_date: str = None, days_ago: int = 90,
                       min_market_cap: float = 0, max_market_cap: float = 500,
                       top_n: int = 20) -> Dict[str, Any]:
        """执行主力资金选股"""
        try:
            success, df, msg = self.data.get_main_force_stocks(
                start_date=start_date,
                days_ago=days_ago,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap,
                top_n=top_n
            )
            return {
                "success": success,
                "strategy": "主力选股",
                "message": msg,
                "stocks": self.data.df_to_dict_list(df),
                "total": len(df) if df is not None else 0
            }
        except Exception as e:
            logger.exception(f"主力选股失败: {e}")
            return {"success": False, "strategy": "主力选股", "error": str(e), "stocks": []}

    # ========== 低价擒牛 ==========
    def run_low_price_bull(self, top_n: int = 5) -> Dict[str, Any]:
        """执行低价擒牛选股"""
        try:
            success, df, msg = self.data.get_low_price_stocks(top_n=top_n)
            return {
                "success": success,
                "strategy": "低价擒牛",
                "message": msg,
                "stocks": self.data.df_to_dict_list(df),
                "total": len(df) if df is not None else 0
            }
        except Exception as e:
            logger.exception(f"低价擒牛选股失败: {e}")
            return {"success": False, "strategy": "低价擒牛", "error": str(e), "stocks": []}

    # ========== 小市值策略 ==========
    def run_small_cap(self, top_n: int = 5) -> Dict[str, Any]:
        """执行小市值选股"""
        try:
            success, df, msg = self.data.get_small_cap_stocks(top_n=top_n)
            return {
                "success": success,
                "strategy": "小市值策略",
                "message": msg,
                "stocks": self.data.df_to_dict_list(df),
                "total": len(df) if df is not None else 0
            }
        except Exception as e:
            logger.exception(f"小市值选股失败: {e}")
            return {"success": False, "strategy": "小市值策略", "error": str(e), "stocks": []}

    # ========== 净利增长 ==========
    def run_profit_growth(self, top_n: int = 5) -> Dict[str, Any]:
        """执行净利增长选股"""
        try:
            success, df, msg = self.data.get_profit_growth_stocks(top_n=top_n)
            return {
                "success": success,
                "strategy": "净利增长",
                "message": msg,
                "stocks": self.data.df_to_dict_list(df),
                "total": len(df) if df is not None else 0
            }
        except Exception as e:
            logger.exception(f"净利增长选股失败: {e}")
            return {"success": False, "strategy": "净利增长", "error": str(e), "stocks": []}

    # ========== 低估值策略 ==========
    def run_value_stock(self, top_n: int = 10) -> Dict[str, Any]:
        """执行低估值选股"""
        try:
            success, df, msg = self.data.get_value_stocks(top_n=top_n)
            return {
                "success": success,
                "strategy": "低估值策略",
                "message": msg,
                "stocks": self.data.df_to_dict_list(df),
                "total": len(df) if df is not None else 0
            }
        except Exception as e:
            logger.exception(f"低估值选股失败: {e}")
            return {"success": False, "strategy": "低估值策略", "error": str(e), "stocks": []}

    # ========== 全部策略 ==========
    def run_all_strategies(self,
                           main_force_top_n: int = 20,
                           low_price_top_n: int = 5,
                           small_cap_top_n: int = 5,
                           profit_growth_top_n: int = 5,
                           value_top_n: int = 10,
                           days_ago: int = 90) -> Dict[str, Any]:
        """执行全部5种策略"""
        results = {
            "timestamp": "",
            "all_success": True,
            "strategies": {
                "主力选股": self.run_main_force(top_n=main_force_top_n, days_ago=days_ago),
                "低价擒牛": self.run_low_price_bull(top_n=low_price_top_n),
                "小市值策略": self.run_small_cap(top_n=small_cap_top_n),
                "净利增长": self.run_profit_growth(top_n=profit_growth_top_n),
                "低估值策略": self.run_value_stock(top_n=value_top_n),
            }
        }

        # 检查是否有失败的策略
        for name, res in results["strategies"].items():
            if not res.get("success", False):
                results["all_success"] = False

        return results


# 全局实例
_custom_engine: Optional[CustomStrategyEngine] = None


def get_custom_strategy_engine() -> CustomStrategyEngine:
    """获取策略引擎实例"""
    global _custom_engine
    if _custom_engine is None:
        _custom_engine = CustomStrategyEngine()
    return _custom_engine
