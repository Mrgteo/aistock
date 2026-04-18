"""
股票分析 Agents 服务 - 多分析师团队
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.services.llm_service import get_llm_service, LLMService


# 全局线程池，避免创建过多线程
_executor = ThreadPoolExecutor(max_workers=6)


class AnalysisAgents:
    """多分析师团队"""

    def __init__(self):
        self.llm = get_llm_service()

    def run_multi_agent_analysis(
        self,
        stock_info: Dict,
        indicators: Dict,
        financial_data: Dict = None,
        fund_flow_data: Dict = None,
        sentiment_data: Dict = None,
        news_data: str = None,
        risk_data: Dict = None,
        enabled_analysts: Dict = None
    ) -> Dict[str, Dict]:
        """
        运行多分析师分析（同步版本）

        Args:
            stock_info: 股票基本信息
            indicators: 技术指标
            financial_data: 财务数据
            fund_flow_data: 资金流数据
            sentiment_data: 情绪数据
            news_data: 新闻文本
            risk_data: 风险数据
            enabled_analysts: 启用的分析师 dict

        Returns:
            各分析师结果 dict
        """
        if enabled_analysts is None:
            enabled_analysts = {
                'technical': True,
                'fundamental': True,
                'fund_flow': True,
                'risk': True,
                'sentiment': True,
                'news': True
            }

        agents_results = {}
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 技术分析师
        if enabled_analysts.get('technical', True):
            try:
                analysis = self.llm.technical_analysis(stock_info, indicators)
            except Exception as e:
                analysis = f"技术分析失败: {str(e)}"
            agents_results['technical'] = {
                'agent_name': '技术分析师',
                'agent_role': '技术指标分析、图表形态识别',
                'focus_areas': ['趋势', '支撑阻力', '指标', 'MACD', 'RSI'],
                'timestamp': timestamp,
                'analysis': analysis
            }

        # 基本面分析师
        if enabled_analysts.get('fundamental', True):
            try:
                analysis = self.llm.fundamental_analysis(stock_info, financial_data)
            except Exception as e:
                analysis = f"基本面分析失败: {str(e)}"
            agents_results['fundamental'] = {
                'agent_name': '基本面分析师',
                'agent_role': '公司财务分析、行业研究',
                'focus_areas': ['盈利能力', '成长性', '估值', '财务健康'],
                'timestamp': timestamp,
                'analysis': analysis
            }

        # 资金面分析师
        if enabled_analysts.get('fund_flow', True):
            try:
                analysis = self.llm.fund_flow_analysis(stock_info, indicators)
            except Exception as e:
                analysis = f"资金面分析失败: {str(e)}"
            agents_results['fund_flow'] = {
                'agent_name': '资金面分析师',
                'agent_role': '资金流向分析、主力行为研究',
                'focus_areas': ['资金流向', '成交量', '主力行为'],
                'timestamp': timestamp,
                'analysis': analysis
            }

        # 风险管理师
        if enabled_analysts.get('risk', True):
            try:
                analysis = self.llm.risk_analysis(stock_info, risk_data)
            except Exception as e:
                analysis = f"风险分析失败: {str(e)}"
            agents_results['risk'] = {
                'agent_name': '风险管理师',
                'agent_role': '风险识别与评估',
                'focus_areas': ['风险识别', '风险评估', '风险控制'],
                'timestamp': timestamp,
                'analysis': analysis
            }

        # 市场情绪分析师
        if enabled_analysts.get('sentiment', True):
            try:
                analysis = self.llm.sentiment_analysis(stock_info, sentiment_data)
            except Exception as e:
                analysis = f"情绪分析失败: {str(e)}"
            agents_results['sentiment'] = {
                'agent_name': '市场情绪分析师',
                'agent_role': '市场情绪研究',
                'focus_areas': ['情绪状态', '投资者情绪', '趋势判断'],
                'timestamp': timestamp,
                'analysis': analysis
            }

        # 新闻分析师
        if enabled_analysts.get('news', True):
            try:
                analysis = self.llm.news_analysis(stock_info, news_data)
            except Exception as e:
                analysis = f"新闻分析失败: {str(e)}"
            agents_results['news'] = {
                'agent_name': '新闻分析师',
                'agent_role': '新闻事件分析、舆情研究',
                'focus_areas': ['新闻影响', '舆情方向', '投资注意'],
                'timestamp': timestamp,
                'analysis': analysis
            }

        return agents_results

    async def run_multi_agent_analysis_async(
        self,
        stock_info: Dict,
        indicators: Dict,
        financial_data: Dict = None,
        fund_flow_data: Dict = None,
        sentiment_data: Dict = None,
        news_data: str = None,
        risk_data: Dict = None,
        enabled_analysts: Dict = None
    ) -> Dict[str, Dict]:
        """
        运行多分析师分析（异步版本，使用 httpx 异步HTTP请求）

        Args:
            stock_info: 股票基本信息
            indicators: 技术指标
            financial_data: 财务数据
            fund_flow_data: 资金流数据
            sentiment_data: 情绪数据
            news_data: 新闻文本
            risk_data: 风险数据
            enabled_analysts: 启用的分析师 dict

        Returns:
            各分析师结果 dict
        """
        if enabled_analysts is None:
            enabled_analysts = {
                'technical': True,
                'fundamental': True,
                'fund_flow': True,
                'risk': True,
                'sentiment': True,
                'news': True
            }

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tasks = []

        # 技术分析师
        if enabled_analysts.get('technical', True):
            tasks.append(('technical', self.llm.technical_analysis_async(stock_info, indicators)))

        # 基本面分析师
        if enabled_analysts.get('fundamental', True):
            tasks.append(('fundamental', self.llm.fundamental_analysis_async(stock_info, financial_data)))

        # 资金面分析师
        if enabled_analysts.get('fund_flow', True):
            tasks.append(('fund_flow', self.llm.fund_flow_analysis_async(stock_info, indicators)))

        # 风险管理师
        if enabled_analysts.get('risk', True):
            tasks.append(('risk', self.llm.risk_analysis_async(stock_info, risk_data)))

        # 市场情绪分析师
        if enabled_analysts.get('sentiment', True):
            tasks.append(('sentiment', self.llm.sentiment_analysis_async(stock_info, sentiment_data)))

        # 新闻分析师
        if enabled_analysts.get('news', True):
            tasks.append(('news', self.llm.news_analysis_async(stock_info, news_data)))

        # 并行执行所有任务
        agent_keys = [t[0] for t in tasks]
        coroutines = [t[1] for t in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # 组装结果
        agents_results = {}
        agent_info = {
            'technical': {
                'agent_name': '技术分析师',
                'agent_role': '技术指标分析、图表形态识别',
                'focus_areas': ['趋势', '支撑阻力', '指标', 'MACD', 'RSI']
            },
            'fundamental': {
                'agent_name': '基本面分析师',
                'agent_role': '公司财务分析、行业研究',
                'focus_areas': ['盈利能力', '成长性', '估值', '财务健康']
            },
            'fund_flow': {
                'agent_name': '资金面分析师',
                'agent_role': '资金流向分析、主力行为研究',
                'focus_areas': ['资金流向', '成交量', '主力行为']
            },
            'risk': {
                'agent_name': '风险管理师',
                'agent_role': '风险识别与评估',
                'focus_areas': ['风险识别', '风险评估', '风险控制']
            },
            'sentiment': {
                'agent_name': '市场情绪分析师',
                'agent_role': '市场情绪研究',
                'focus_areas': ['情绪状态', '投资者情绪', '趋势判断']
            },
            'news': {
                'agent_name': '新闻分析师',
                'agent_role': '新闻事件分析、舆情研究',
                'focus_areas': ['新闻影响', '舆情方向', '投资注意']
            }
        }

        for i, key in enumerate(agent_keys):
            result = results[i]
            if isinstance(result, Exception):
                analysis = f"{agent_info[key]['agent_name']}分析失败: {str(result)}"
            else:
                analysis = result

            agents_results[key] = {
                **agent_info[key],
                'timestamp': timestamp,
                'analysis': analysis
            }

        return agents_results

    def make_final_decision(
        self,
        agents_results: Dict,
        stock_info: Dict,
        indicators: Dict
    ) -> Dict[str, Any]:
        """综合决策（同步版本）"""
        return self.llm.final_decision(agents_results, stock_info, indicators)

    async def make_final_decision_async(
        self,
        agents_results: Dict,
        stock_info: Dict,
        indicators: Dict
    ) -> Dict[str, Any]:
        """综合决策（异步版本，使用 httpx 异步HTTP请求）"""
        return await self.llm.final_decision_async(agents_results, stock_info, indicators)

    def conduct_team_discussion(
        self,
        agents_results: Dict,
        stock_info: Dict,
        indicators: Dict
    ) -> str:
        """进行团队讨论（同步版本）"""
        return self.llm.team_discussion(agents_results, stock_info, indicators)

    async def conduct_team_discussion_async(
        self,
        agents_results: Dict,
        stock_info: Dict,
        indicators: Dict
    ) -> str:
        """进行团队讨论（异步版本，使用 httpx 异步HTTP请求）"""
        return await self.llm.team_discussion_async(agents_results, stock_info, indicators)


# 单例模式
_analysis_agents: Optional[AnalysisAgents] = None


def get_analysis_agents() -> AnalysisAgents:
    """获取分析 Agents 单例"""
    global _analysis_agents
    if _analysis_agents is None:
        _analysis_agents = AnalysisAgents()
    return _analysis_agents