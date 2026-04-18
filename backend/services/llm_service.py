"""
LLM 服务 - DeepSeek API 封装
"""
import json
import re
from typing import Dict, List, Any, Optional
import requests
import httpx

from backend.core.config import settings


class LLMService:
    """DeepSeek API 客户端"""

    def __init__(self, model: str = None):
        self.model = model or settings.DEFAULT_MODEL_NAME
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL

    def call_api(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """调用 DeepSeek API (同步版本)"""
        model_to_use = model or self.model

        # reasoner 模型需要更多 tokens
        if "reasoner" in model_to_use.lower() and max_tokens <= 2000:
            max_tokens = 8000

        data = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.base_url + "/chat/completions",
                json=data,
                headers=headers,
                timeout=(10, 180)  # (连接超时, 读取超时)
            )
            response.raise_for_status()
            res_json = response.json()
            message = res_json["choices"][0]["message"]

            # 处理 reasoner 模型的响应
            result = ""
            reasoning = message.get('reasoning_content') or ''
            if reasoning:
                result += f"【推理过程】\n{reasoning}\n\n"
            content = message.get('content') or ''
            if content:
                result += content

            return result if result else "API返回空响应"

        except requests.exceptions.RequestException as e:
            return f"API调用失败: {str(e)}"

    async def call_api_async(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                             temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """调用 DeepSeek API (异步版本，使用 httpx) """
        model_to_use = model or self.model

        # reasoner 模型需要更多 tokens
        if "reasoner" in model_to_use.lower() and max_tokens <= 2000:
            max_tokens = 8000

        data = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
                response = await client.post(
                    self.base_url + "/chat/completions",
                    json=data,
                    headers=headers
                )
                response.raise_for_status()
                res_json = response.json()
                message = res_json["choices"][0]["message"]

                # 处理 reasoner 模型的响应
                result = ""
                reasoning = message.get('reasoning_content') or ''
                if reasoning:
                    result += f"【推理过程】\n{reasoning}\n\n"
                content = message.get('content') or ''
                if content:
                    result += content

                return result if result else "API返回空响应"

        except httpx.HTTPError as e:
            return f"API调用失败: {str(e)}"

    def technical_analysis(self, stock_info: Dict, indicators: Dict) -> str:
        """技术面分析"""
        prompt = f"""
你是一名资深的技术分析师。请基于以下股票数据进行专业的技术面分析：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 涨跌幅：{stock_info.get('change_percent', 'N/A')}%

最新技术指标：
- 收盘价：{indicators.get('price', 'N/A')}
- MA5：{indicators.get('ma5', 'N/A')}
- MA10：{indicators.get('ma10', 'N/A')}
- MA20：{indicators.get('ma20', 'N/A')}
- MA60：{indicators.get('ma60', 'N/A')}
- RSI：{indicators.get('rsi14', 'N/A')}
- MACD：{indicators.get('macd', 'N/A')}
- MACD信号线：{indicators.get('macd_dif', 'N/A')}
- MACD柱：{indicators.get('macd_hist', 'N/A')}

请从以下角度进行分析：
1. 趋势分析（均线系统、价格走势）
2. 超买超卖分析（RSI）
3. 动量分析（MACD）
4. 成交量分析
5. 短期、中期、长期技术判断

请给出专业、详细的技术分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票技术分析师，具有深厚的技术分析功底。"},
            {"role": "user", "content": prompt}
        ]

        return self.call_api(messages, max_tokens=3000)

    def fundamental_analysis(self, stock_info: Dict, financial_data: Dict = None) -> str:
        """基本面分析"""
        financial_section = ""
        if financial_data and not financial_data.get('error'):
            ratios = financial_data.get('financial_ratios', {})
            if ratios:
                financial_section = f"""
详细财务指标：
- 市盈率(PE)：{stock_info.get('pe_ratio', 'N/A')}
- 市净率(PB)：{stock_info.get('pb_ratio', 'N/A')}
- 市值(亿)：{stock_info.get('market_cap', 'N/A')}
"""

        prompt = f"""
你是一名资深的基本面分析师。请基于以下信息进行基本面分析：

【基本信息】
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 市值：{stock_info.get('market_cap', 'N/A')}
- 行业：{stock_info.get('sector', 'N/A')}
{financial_section}

请从以下维度进行分析：
1. 公司质地和行业地位
2. 盈利能力分析
3. 成长性分析
4. 估值分析
5. 投资价值判断

请给出专业、详细的基本面分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票基本面分析师，擅长公司财务分析和行业研究。"},
            {"role": "user", "content": prompt}
        ]

        return self.call_api(messages, max_tokens=3000)

    def fund_flow_analysis(self, stock_info: Dict, indicators: Dict) -> str:
        """资金面分析"""
        prompt = f"""
你是一名资深的资金面分析师。请基于以下数据进行资金面分析：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 量比：{indicators.get('volume_ratio', 'N/A')}

请分析：
1. 资金流向趋势
2. 成交量变化
3. 主力行为推测
4. 投资建议

请给出专业、详细的资金面分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名经验丰富的资金面分析师，擅长市场资金流向和主力行为分析。"},
            {"role": "user", "content": prompt}
        ]

        return self.call_api(messages, max_tokens=3000)

    def risk_analysis(self, stock_info: Dict, risk_data: Dict = None) -> str:
        """风险分析"""
        risk_section = ""
        if risk_data:
            risk_section = f"""
风险数据：
- 解禁风险：{risk_data.get('unlock_risk', 'N/A')}
- 减持风险：{risk_data.get('reduce_risk', 'N/A')}
"""

        prompt = f"""
你是一名专业的风险管理师。请分析以下股票的风险：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
{risk_section}

请分析：
1. 潜在风险因素
2. 风险等级评估
3. 风险控制建议

请给出专业的风险分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名专业的风险管理师，擅长风险识别和评估。"},
            {"role": "user", "content": prompt}
        ]

        return self.call_api(messages, max_tokens=3000)

    def sentiment_analysis(self, stock_info: Dict, sentiment_data: Dict = None) -> str:
        """情绪分析"""
        prompt = f"""
你是一名市场情绪分析师。请分析以下股票的市场情绪：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}

请分析：
1. 市场情绪状态
2. 投资者情绪
3. 情绪趋势判断

请给出专业的情绪分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名专业的市场情绪分析师。"},
            {"role": "user", "content": prompt}
        ]

        return self.call_api(messages, max_tokens=3000)

    def news_analysis(self, stock_info: Dict, news_data: str = None) -> str:
        """新闻分析"""
        news_section = news_data if news_data else "暂无新闻数据"

        prompt = f"""
你是一名新闻舆情分析师。请基于以下新闻进行分析：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}

新闻内容：
{news_section}

请分析：
1. 新闻对股价的影响
2. 舆情方向（正面/负面/中性）
3. 投资注意事项

请给出专业的新闻舆情分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名专业的新闻舆情分析师。"},
            {"role": "user", "content": prompt}
        ]

        return self.call_api(messages, max_tokens=3000)

    def team_discussion(self, agents_results: Dict, stock_info: Dict, indicators: Dict = None) -> str:
        """团队讨论 - 综合各分析师观点进行讨论"""
        # 收集参与分析的分析师名单和报告
        participants = []
        reports = []

        agent_names = {
            'technical': '技术分析师',
            'fundamental': '基本面分析师',
            'fund_flow': '资金面分析师',
            'risk': '风险管理师',
            'sentiment': '市场情绪分析师',
            'news': '新闻分析师'
        }

        for key, name in agent_names.items():
            if key in agents_results and agents_results[key].get('analysis'):
                participants.append(name)
                analysis = agents_results[key]['analysis']
                # 截断过长的分析报告
                if len(analysis) > 2000:
                    analysis = analysis[:2000] + "..."
                reports.append(f"【{name}报告】\n{analysis}")

        if not participants:
            return "暂无参与讨论的分析师"

        all_reports = "\n\n".join(reports)
        participants_text = "、".join(participants)

        prompt = f"""现在进行投资决策团队会议，参会人员包括：{participants_text}。

股票：{stock_info.get('name', 'N/A')} ({stock_info.get('symbol', 'N/A')})
当前价格：{stock_info.get('current_price', 'N/A')}
涨跌幅：{stock_info.get('change_percent', 'N/A')}%

各分析师报告：

{all_reports}

请模拟一场真实的投资决策会议讨论：
1. 各分析师观点的一致性和分歧
2. 不同维度分析的权重考量
3. 风险收益评估
4. 投资时机判断
5. 策略制定思路
6. 达成初步共识

请以对话形式展现讨论过程，体现专业团队的思辨过程。只讨论参与分析的分析师的观点。
"""

        messages = [
            {"role": "system", "content": "你需要模拟一场专业的投资团队讨论会议，体现不同角色的观点碰撞和最终共识形成。"},
            {"role": "user", "content": prompt}
        ]

        return self.call_api(messages, max_tokens=6000)

    def final_decision(self, agents_results: Dict, stock_info: Dict, indicators: Dict = None) -> Dict[str, Any]:
        """综合决策（合并团队讨论）"""
        # 汇总各分析师报告
        reports_summary = []
        for agent_key, result in agents_results.items():
            agent_name = result.get('agent_name', agent_key)
            analysis = result.get('analysis', '')
            reports_summary.append(f"【{agent_name}】\n{analysis}")

        reports_text = "\n\n".join(reports_summary)

        # 先进行团队讨论
        participants = []
        for agent_key, result in agents_results.items():
            agent_name = result.get('agent_name', agent_key)
            participants.append(agent_name)

        discussion_prompt = f"""现在进行投资决策团队会议，参会人员包括：{', '.join(participants)}。

股票：{stock_info.get('name', 'N/A')} ({stock_info.get('symbol', 'N/A')})
当前价格：{stock_info.get('current_price', 'N/A')}
涨跌幅：{stock_info.get('change_percent', 'N/A')}%

各分析师报告：

{reports_text}

请模拟一场真实的投资决策会议讨论：
1. 各分析师观点的一致性和分歧
2. 不同维度分析的权重考量
3. 风险收益评估
4. 投资时机判断
5. 策略制定思路
6. 达成初步共识

请以对话形式展现讨论过程，体现专业团队的思辨过程。只讨论参与分析的分析师的观点。
"""

        discussion_messages = [
            {"role": "system", "content": "你需要模拟一场专业的投资团队讨论会议，体现不同角色的观点碰撞和最终共识形成。"},
            {"role": "user", "content": discussion_prompt}
        ]

        discussion_result = self.call_api(discussion_messages, max_tokens=6000)

        # 基于讨论结果生成最终决策
        decision_prompt = f"""基于团队讨论和分析师报告，请给出最终投资决策：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}

团队讨论结论：
{discussion_result}

请给出最终投资决策，必须包含以下内容：
1. 投资评级：买入/持有/卖出
2. 目标价位
3. 操作建议
4. 进场位置区间
5. 止盈位置
6. 止损位置
7. 持有周期建议
8. 风险提示
9. 信心度(1-10分)

请以JSON格式输出：
{{
    "rating": "买入/持有/卖出",
    "target_price": "目标价位",
    "operation_advice": "操作建议",
    "entry_range": "进场区间",
    "take_profit": "止盈位",
    "stop_loss": "止损位",
    "holding_period": "持有周期",
    "risk_warning": "风险提示",
    "confidence_level": "信心度(1-10分)"
}}
"""

        decision_messages = [
            {"role": "system", "content": "你是一名专业的投资决策专家，需要给出明确、可执行的投资建议。"},
            {"role": "user", "content": decision_prompt}
        ]

        response = self.call_api(decision_messages, temperature=0.3, max_tokens=4000)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decision_json = json.loads(json_match.group())
                # 返回包含讨论和决策的完整结果
                return {
                    "discussion": discussion_result,
                    **decision_json
                }
            else:
                return {
                    "discussion": discussion_result,
                    "decision_text": response
                }
        except:
            return {
                "discussion": discussion_result,
                "decision_text": response
            }

    # ==================== 异步版本方法 ====================

    async def technical_analysis_async(self, stock_info: Dict, indicators: Dict) -> str:
        """技术面分析（异步版本）"""
        prompt = f"""
你是一名资深的技术分析师。请基于以下股票数据进行专业的技术面分析：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 涨跌幅：{stock_info.get('change_percent', 'N/A')}%

最新技术指标：
- 收盘价：{indicators.get('price', 'N/A')}
- MA5：{indicators.get('ma5', 'N/A')}
- MA10：{indicators.get('ma10', 'N/A')}
- MA20：{indicators.get('ma20', 'N/A')}
- MA60：{indicators.get('ma60', 'N/A')}
- RSI：{indicators.get('rsi14', 'N/A')}
- MACD：{indicators.get('macd', 'N/A')}
- MACD信号线：{indicators.get('macd_dif', 'N/A')}
- MACD柱：{indicators.get('macd_hist', 'N/A')}

请从以下角度进行分析：
1. 趋势分析（均线系统、价格走势）
2. 超买超卖分析（RSI）
3. 动量分析（MACD）
4. 成交量分析
5. 短期、中期、长期技术判断

请给出专业、详细的技术分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票技术分析师，具有深厚的技术分析功底。"},
            {"role": "user", "content": prompt}
        ]

        return await self.call_api_async(messages, max_tokens=3000)

    async def fundamental_analysis_async(self, stock_info: Dict, financial_data: Dict = None) -> str:
        """基本面分析（异步版本）"""
        financial_section = ""
        if financial_data and not financial_data.get('error'):
            ratios = financial_data.get('financial_ratios', {})
            if ratios:
                financial_section = f"""
详细财务指标：
- 市盈率(PE)：{stock_info.get('pe_ratio', 'N/A')}
- 市净率(PB)：{stock_info.get('pb_ratio', 'N/A')}
- 市值(亿)：{stock_info.get('market_cap', 'N/A')}
"""

        prompt = f"""
你是一名资深的基本面分析师。请基于以下信息进行基本面分析：

【基本信息】
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 市值：{stock_info.get('market_cap', 'N/A')}
- 行业：{stock_info.get('sector', 'N/A')}
{financial_section}

请从以下维度进行分析：
1. 公司质地和行业地位
2. 盈利能力分析
3. 成长性分析
4. 估值分析
5. 投资价值判断

请给出专业、详细的基本面分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名经验丰富的股票基本面分析师，擅长公司财务分析和行业研究。"},
            {"role": "user", "content": prompt}
        ]

        return await self.call_api_async(messages, max_tokens=3000)

    async def fund_flow_analysis_async(self, stock_info: Dict, indicators: Dict) -> str:
        """资金面分析（异步版本）"""
        prompt = f"""
你是一名资深的资金面分析师。请基于以下数据进行资金面分析：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
- 量比：{indicators.get('volume_ratio', 'N/A')}

请分析：
1. 资金流向趋势
2. 成交量变化
3. 主力行为推测
4. 投资建议

请给出专业、详细的资金面分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名经验丰富的资金面分析师，擅长市场资金流向和主力行为分析。"},
            {"role": "user", "content": prompt}
        ]

        return await self.call_api_async(messages, max_tokens=3000)

    async def risk_analysis_async(self, stock_info: Dict, risk_data: Dict = None) -> str:
        """风险分析（异步版本）"""
        risk_section = ""
        if risk_data:
            risk_section = f"""
风险数据：
- 解禁风险：{risk_data.get('unlock_risk', 'N/A')}
- 减持风险：{risk_data.get('reduce_risk', 'N/A')}
"""

        prompt = f"""
你是一名专业的风险管理师。请分析以下股票的风险：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}
{risk_section}

请分析：
1. 潜在风险因素
2. 风险等级评估
3. 风险控制建议

请给出专业的风险分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名专业的风险管理师，擅长风险识别和评估。"},
            {"role": "user", "content": prompt}
        ]

        return await self.call_api_async(messages, max_tokens=3000)

    async def sentiment_analysis_async(self, stock_info: Dict, sentiment_data: Dict = None) -> str:
        """情绪分析（异步版本）"""
        prompt = f"""
你是一名市场情绪分析师。请分析以下股票的市场情绪：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}

请分析：
1. 市场情绪状态
2. 投资者情绪
3. 情绪趋势判断

请给出专业的情绪分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名专业的市场情绪分析师。"},
            {"role": "user", "content": prompt}
        ]

        return await self.call_api_async(messages, max_tokens=3000)

    async def news_analysis_async(self, stock_info: Dict, news_data: str = None) -> str:
        """新闻分析（异步版本）"""
        news_section = news_data if news_data else "暂无新闻数据"

        prompt = f"""
你是一名新闻舆情分析师。请基于以下新闻进行分析：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}

新闻内容：
{news_section}

请分析：
1. 新闻对股价的影响
2. 舆情方向（正面/负面/中性）
3. 投资注意事项

请给出专业的新闻舆情分析报告。
"""

        messages = [
            {"role": "system", "content": "你是一名专业的新闻舆情分析师。"},
            {"role": "user", "content": prompt}
        ]

        return await self.call_api_async(messages, max_tokens=3000)

    async def team_discussion_async(self, agents_results: Dict, stock_info: Dict, indicators: Dict = None) -> str:
        """团队讨论（异步版本）"""
        participants = []
        reports = []

        agent_names = {
            'technical': '技术分析师',
            'fundamental': '基本面分析师',
            'fund_flow': '资金面分析师',
            'risk': '风险管理师',
            'sentiment': '市场情绪分析师',
            'news': '新闻分析师'
        }

        for key, name in agent_names.items():
            if key in agents_results and agents_results[key].get('analysis'):
                participants.append(name)
                analysis = agents_results[key]['analysis']
                if len(analysis) > 2000:
                    analysis = analysis[:2000] + "..."
                reports.append(f"【{name}报告】\n{analysis}")

        if not participants:
            return "暂无参与讨论的分析师"

        all_reports = "\n\n".join(reports)
        participants_text = "、".join(participants)

        prompt = f"""现在进行投资决策团队会议，参会人员包括：{participants_text}。

股票：{stock_info.get('name', 'N/A')} ({stock_info.get('symbol', 'N/A')})
当前价格：{stock_info.get('current_price', 'N/A')}
涨跌幅：{stock_info.get('change_percent', 'N/A')}%

各分析师报告：

{all_reports}

请模拟一场真实的投资决策会议讨论：
1. 各分析师观点的一致性和分歧
2. 不同维度分析的权重考量
3. 风险收益评估
4. 投资时机判断
5. 策略制定思路
6. 达成初步共识

请以对话形式展现讨论过程，体现专业团队的思辨过程。只讨论参与分析的分析师的观点。
"""

        messages = [
            {"role": "system", "content": "你需要模拟一场专业的投资团队讨论会议，体现不同角色的观点碰撞和最终共识形成。"},
            {"role": "user", "content": prompt}
        ]

        return await self.call_api_async(messages, max_tokens=6000)

    async def final_decision_async(self, agents_results: Dict, stock_info: Dict, indicators: Dict = None) -> Dict[str, Any]:
        """综合决策（异步版本，合并团队讨论）"""
        reports_summary = []
        for agent_key, result in agents_results.items():
            agent_name = result.get('agent_name', agent_key)
            analysis = result.get('analysis', '')
            reports_summary.append(f"【{agent_name}】\n{analysis}")

        reports_text = "\n\n".join(reports_summary)

        participants = []
        for agent_key, result in agents_results.items():
            agent_name = result.get('agent_name', agent_key)
            participants.append(agent_name)

        discussion_prompt = f"""现在进行投资决策团队会议，参会人员包括：{', '.join(participants)}。

股票：{stock_info.get('name', 'N/A')} ({stock_info.get('symbol', 'N/A')})
当前价格：{stock_info.get('current_price', 'N/A')}
涨跌幅：{stock_info.get('change_percent', 'N/A')}%

各分析师报告：

{reports_text}

请模拟一场真实的投资决策会议讨论：
1. 各分析师观点的一致性和分歧
2. 不同维度分析的权重考量
3. 风险收益评估
4. 投资时机判断
5. 策略制定思路
6. 达成初步共识

请以对话形式展现讨论过程，体现专业团队的思辨过程。只讨论参与分析的分析师的观点。
"""

        discussion_messages = [
            {"role": "system", "content": "你需要模拟一场专业的投资团队讨论会议，体现不同角色的观点碰撞和最终共识形成。"},
            {"role": "user", "content": discussion_prompt}
        ]

        discussion_result = await self.call_api_async(discussion_messages, max_tokens=6000)

        decision_prompt = f"""基于团队讨论和分析师报告，请给出最终投资决策：

股票信息：
- 股票代码：{stock_info.get('symbol', 'N/A')}
- 股票名称：{stock_info.get('name', 'N/A')}
- 当前价格：{stock_info.get('current_price', 'N/A')}

团队讨论结论：
{discussion_result}

请给出最终投资决策，必须包含以下内容：
1. 投资评级：买入/持有/卖出
2. 目标价位
3. 操作建议
4. 进场位置区间
5. 止盈位置
6. 止损位置
7. 持有周期建议
8. 风险提示
9. 信心度(1-10分)

请以JSON格式输出：
{{
    "rating": "买入/持有/卖出",
    "target_price": "目标价位",
    "operation_advice": "操作建议",
    "entry_range": "进场区间",
    "take_profit": "止盈位",
    "stop_loss": "止损位",
    "holding_period": "持有周期",
    "risk_warning": "风险提示",
    "confidence_level": "信心度(1-10分)"
}}
"""

        decision_messages = [
            {"role": "system", "content": "你是一名专业的投资决策专家，需要给出明确、可执行的投资建议。"},
            {"role": "user", "content": decision_prompt}
        ]

        response = await self.call_api_async(decision_messages, temperature=0.3, max_tokens=4000)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decision_json = json.loads(json_match.group())
                return {
                    "discussion": discussion_result,
                    **decision_json
                }
            else:
                return {
                    "discussion": discussion_result,
                    "decision_text": response
                }
        except:
            return {
                "discussion": discussion_result,
                "decision_text": response
            }


# 单例模式
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
