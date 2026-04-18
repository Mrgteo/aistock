"""
股票分析路由 - AI分析功能
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import requests
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.core.config import settings
from backend.routers.stock import get_code_type, get_ifzq_kline, get_indicators, merge_realtime_kline
from backend.routers.analysis_db import db

router = APIRouter(tags=["股票分析"])

# 通用线程池，用于执行同步阻塞操作
_executor = ThreadPoolExecutor(max_workers=8)


def get_stock_name(qt_data, default_name=''):
    """从qt_data中提取股票名称"""
    if not qt_data:
        return default_name
    for key in qt_data:
        if isinstance(qt_data[key], list) and len(qt_data[key]) > 1:
            name = qt_data[key][1]
            if name:
                return name
    return default_name


class ChatReq(BaseModel):
    mode: str
    symbol: str = None
    messages: list = None


def get_news(code):
    """获取股票新闻"""
    try:
        if ".SS" in code:
            sid = "1." + code.replace(".SS", "")
        elif ".SZ" in code:
            sid = "0." + code.replace(".SZ", "")
        else:
            sid = "105." + code

        url = "https://np-anotice-stock.eastmoney.com/api/security/ann?cb=jQuery&secid=" + sid + "&page_index=1&page_size=5"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        link = "https://data.eastmoney.com/notices/stock/" + code[0:6] + ".html"

        s = r.text
        start = s.find("(") + 1
        end = s.rfind(")")
        json_str = s[start:end]

        data = json.loads(json_str)
        arr = []
        for x in data["data"]["list"]:
            arr.append(x["title"] + " " + x["notice_date"][:10])

        return "\n".join(arr), link
    except Exception as e:
        return "没爬到新闻", ""


def get_fund(code):
    """获取股票基本面"""
    try:
        from backend.routers.stock import get_tx_code
        tx_code = get_tx_code(code)
        url = "http://qt.gtimg.cn/q=" + tx_code
        r = requests.get(url, timeout=10)
        link = "https://finance.sina.com.cn/realstock/company/" + tx_code[2:] + "/nc.shtml"

        arr = r.text.split("~")
        pe = arr[39]
        pb = arr[46]
        sz = arr[45]
        hs = arr[38]

        res = "PE: " + pe + "\nPB: " + pb + "\n市值(亿): " + sz + "\n换手率: " + hs + "%"
        return res, link
    except Exception as e:
        return "没爬到基本面", ""


@router.post("/chat")
async def chat_with_ai(req: ChatReq):
    """与AI对话或进行股票分析"""
    if req.mode == "analysis":
        code, market = get_code_type(req.symbol)
        # 使用同步函数获取K线数据
        df, qt_data = get_ifzq_kline(code, period='day', days=500)
        if df is None:
            raise HTTPException(status_code=404, detail=f"无法获取 {req.symbol} 的K线数据")
        if qt_data:
            df = merge_realtime_kline(df, code, qt_data)
        m = get_indicators(df)

        news_text, news_link = get_news(code)
        fund_text, fund_link = get_fund(code)

        # 构建分析提示
        prompt = "股票：" + req.symbol + "\n"
        prompt += "价格：" + str(m["price"]) + " 涨跌：" + str(m["change_pct"]) + "%\n"
        prompt += "MA5: " + str(m["ma5"]) + " MA20: " + str(m["ma20"]) + "\n"
        prompt += "RSI: " + str(m["rsi14"]) + "\n"
        prompt += "MACD柱: " + str(m["macd_hist"]) + "\n"
        prompt += "新闻：\n" + news_text + "\n"
        prompt += "基本面：\n" + fund_text + "\n\n"
        prompt += "请分析这只股票，按JSON格式输出，字段包含：technical, news, fundamental, conclusion, risk, advice。不要输出别的废话！"

        data = {
            "model": settings.DEFAULT_MODEL_NAME,
            "messages": [
                {"role": "system", "content": "你是股票分析助手"},
                {"role": "user", "content": prompt}
            ]
        }

        api_key = settings.DEEPSEEK_API_KEY or "sk-8cb3bfe75b94480a8005a87362306526"
        headers = {"Authorization": "Bearer " + api_key}

        try:
            r = requests.post(
                settings.DEEPSEEK_BASE_URL + "/chat/completions",
                json=data,
                headers=headers,
                timeout=30
            )
            res_json = r.json()
            ans = res_json["choices"][0]["message"]["content"]

            # 处理AI返回的格式
            ans = ans.replace("```json", "").replace("```", "").strip()
            try:
                d = json.loads(ans)
                d["news_link"] = news_link
                d["fund_link"] = fund_link
                return {"structured": True, "data": d}
            except:
                return {"structured": False, "reply": ans}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")

    else:
        # 普通聊天
        data = {
            "model": settings.DEFAULT_MODEL_NAME,
            "messages": [{"role": "system", "content": "你是助手"}] + req.messages
        }

        api_key = settings.DEEPSEEK_API_KEY or "sk-8cb3bfe75b94480a8005a87362306526"
        headers = {"Authorization": "Bearer " + api_key}

        try:
            r = requests.post(
                settings.DEEPSEEK_BASE_URL + "/chat/completions",
                json=data,
                headers=headers,
                timeout=30
            )
            ans = r.json()["choices"][0]["message"]["content"]
            return {"reply": ans}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI响应失败: {str(e)}")


# ========== 多分析师团队 API ==========

class SingleAnalysisReq(BaseModel):
    symbol: str
    enabled_analysts: Optional[Dict[str, bool]] = None


@router.post("/analysis/single")
async def single_stock_analysis(req: SingleAnalysisReq):
    """单股深度分析 - 多分析师团队"""
    try:
        # 获取股票代码和市场
        code, market = get_code_type(req.symbol)

        # 获取K线数据
        df, qt_data = get_ifzq_kline(code, period='day', days=500)
        if df is None:
            raise HTTPException(status_code=404, detail=f"无法获取 {req.symbol} 的K线数据")

        # 合并实时数据
        if qt_data:
            df = merge_realtime_kline(df, code, qt_data)

        # 获取技术指标
        indicators = get_indicators(df)

        # 构建股票信息
        stock_info = {
            'symbol': req.symbol,
            'code': code,
            'market': market,
            'name': get_stock_name(qt_data, req.symbol),
            'current_price': str(indicators.get('price', 'N/A')),
            'change_percent': str(indicators.get('change_pct', 0)),
        }

        # 获取新闻
        news_text, news_link = get_news(code)
        fund_text, fund_link = get_fund(code)

        # 添加基本面信息到 stock_info
        try:
            if qt_data:
                stock_info['pe_ratio'] = qt_data.get('pe', 'N/A')
                stock_info['pb_ratio'] = qt_data.get('pb', 'N/A')
                stock_info['market_cap'] = qt_data.get('sz', 'N/A')
        except:
            pass

        # 默认启用的分析师
        if req.enabled_analysts is None:
            req.enabled_analysts = {
                'technical': True,
                'fundamental': True,
                'fund_flow': True,
                'risk': True,
                'sentiment': True,
                'news': True
            }

        # 运行多分析师分析（使用异步版本，避免阻塞事件循环）
        from backend.services.analysis_agents import get_analysis_agents
        agents = get_analysis_agents()

        agents_results = await agents.run_multi_agent_analysis_async(
            stock_info=stock_info,
            indicators=indicators,
            news_data=news_text,
            enabled_analysts=req.enabled_analysts
        )

        # 生成综合决策（使用异步版本，包含团队讨论）
        final_decision = await agents.make_final_decision_async(agents_results, stock_info, indicators)

        # 从 final_decision 中提取讨论结果
        discussion_result = final_decision.get('discussion', '') if isinstance(final_decision, dict) else ''

        # 保存到历史记录
        saved_record_id = None
        try:
            indicators_data = {
                'price': indicators.get('price'),
                'change_pct': indicators.get('change_pct'),
                'ma5': indicators.get('ma5'),
                'ma10': indicators.get('ma10'),
                'ma20': indicators.get('ma20'),
                'ma60': indicators.get('ma60'),
                'rsi14': indicators.get('rsi14'),
                'macd_dif': indicators.get('macd_dif'),
                'macd_dea': indicators.get('macd_dea'),
                'macd_hist': indicators.get('macd_hist'),
            }
            saved_record_id = db.save_analysis(
                symbol=req.symbol,
                stock_name=stock_info.get('name', req.symbol),
                period='day',
                stock_info=stock_info,
                indicators=indicators_data,
                agents_results=agents_results,
                final_decision=final_decision,
                discussion_result=discussion_result,
                news_link=news_link,
                fund_link=fund_link
            )
            print(f"✅ 历史记录保存成功, ID: {saved_record_id}")
        except Exception as db_err:
            print(f"❌ 保存历史记录失败: {db_err}")

        return {
            "success": True,
            "stock_info": stock_info,
            "indicators": {
                'price': indicators.get('price'),
                'change_pct': indicators.get('change_pct'),
                'ma5': indicators.get('ma5'),
                'ma10': indicators.get('ma10'),
                'ma20': indicators.get('ma20'),
                'ma60': indicators.get('ma60'),
                'rsi14': indicators.get('rsi14'),
                'macd_dif': indicators.get('macd_dif'),
                'macd_dea': indicators.get('macd_dea'),
                'macd_hist': indicators.get('macd_hist'),
            },
            "agents_results": agents_results,
            "final_decision": final_decision,
            "discussion_result": discussion_result,
            "news_link": news_link,
            "fund_link": fund_link,
            "saved_record_id": saved_record_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


class BatchAnalysisReq(BaseModel):
    symbols: List[str]
    enabled_analysts: Optional[Dict[str, bool]] = None
    analysis_mode: str = "sequential"  # "sequential" or "parallel"


def _analyze_single_stock(symbol: str, enabled_analysts: Dict[str, bool]) -> Dict[str, Any]:
    """分析单只股票的内部函数（同步版本）"""
    from backend.services.analysis_agents import get_analysis_agents

    agents = get_analysis_agents()

    try:
        # 获取股票代码和市场
        code, market = get_code_type(symbol)

        # 获取K线数据
        df, qt_data = get_ifzq_kline(code, period='day', days=500)
        if df is None:
            return {
                "symbol": symbol,
                "success": False,
                "error": f"无法获取K线数据"
            }

        # 合并实时数据
        if qt_data:
            df = merge_realtime_kline(df, code, qt_data)

        # 获取技术指标
        indicators = get_indicators(df)

        # 构建股票信息
        stock_info = {
            'symbol': symbol,
            'code': code,
            'market': market,
            'name': get_stock_name(qt_data, symbol),
            'current_price': str(indicators.get('price', 'N/A')),
            'change_percent': str(indicators.get('change_pct', 0)),
        }

        # 添加基本面信息到 stock_info
        try:
            if qt_data:
                stock_info['pe_ratio'] = qt_data.get('pe', 'N/A')
                stock_info['pb_ratio'] = qt_data.get('pb', 'N/A')
                stock_info['market_cap'] = qt_data.get('sz', 'N/A')
        except:
            pass

        # 获取新闻
        news_text, _ = get_news(code)

        # 默认启用的分析师
        if enabled_analysts is None:
            enabled_analysts = {
                'technical': True,
                'fundamental': True,
                'fund_flow': True,
                'risk': True,
                'sentiment': True,
                'news': True
            }

        # 运行多分析师分析（同步版本）
        agents_results = agents.run_multi_agent_analysis(
            stock_info=stock_info,
            indicators=indicators,
            news_data=news_text,
            enabled_analysts=enabled_analysts
        )

        # 生成综合决策（包含团队讨论，同步版本）
        final_decision = agents.make_final_decision(agents_results, stock_info, indicators)

        return {
            "symbol": symbol,
            "success": True,
            "stock_info": stock_info,
            "indicators": {
                'price': indicators.get('price'),
                'change_pct': indicators.get('change_pct'),
                'ma5': indicators.get('ma5'),
                'ma10': indicators.get('ma10'),
                'ma20': indicators.get('ma20'),
                'ma60': indicators.get('ma60'),
                'rsi14': indicators.get('rsi14'),
            },
            "agents_results": agents_results,
            "final_decision": final_decision,
            "agents_count": len(agents_results)
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "success": False,
            "error": str(e)
        }


async def _analyze_single_stock_async(symbol: str, enabled_analysts: Dict[str, bool]) -> Dict[str, Any]:
    """分析单只股票的内部函数（异步版本，使用httpx异步HTTP）"""
    from backend.services.analysis_agents import get_analysis_agents

    agents = get_analysis_agents()

    try:
        # 获取股票代码和市场
        code, market = get_code_type(symbol)

        # 获取K线数据（同步函数，放到线程池执行）
        loop = asyncio.get_event_loop()
        df, qt_data = await loop.run_in_executor(
            _executor, get_ifzq_kline, code, 'day', 500
        )
        if df is None:
            return {
                "symbol": symbol,
                "success": False,
                "error": f"无法获取K线数据"
            }

        # 合并实时数据（同步函数，放到线程池执行）
        if qt_data:
            df = await loop.run_in_executor(
                _executor, merge_realtime_kline, df, code, qt_data
            )

        # 获取技术指标（同步函数，放到线程池执行）
        indicators = await loop.run_in_executor(
            _executor, get_indicators, df
        )

        # 构建股票信息
        stock_info = {
            'symbol': symbol,
            'code': code,
            'market': market,
            'name': get_stock_name(qt_data, symbol),
            'current_price': str(indicators.get('price', 'N/A')),
            'change_percent': str(indicators.get('change_pct', 0)),
        }

        # 添加基本面信息到 stock_info
        try:
            if qt_data:
                stock_info['pe_ratio'] = qt_data.get('pe', 'N/A')
                stock_info['pb_ratio'] = qt_data.get('pb', 'N/A')
                stock_info['market_cap'] = qt_data.get('sz', 'N/A')
        except:
            pass

        # 获取新闻（同步函数，放到线程池执行）
        news_text, _ = await loop.run_in_executor(
            _executor, get_news, code
        )

        # 默认启用的分析师
        if enabled_analysts is None:
            enabled_analysts = {
                'technical': True,
                'fundamental': True,
                'fund_flow': True,
                'risk': True,
                'sentiment': True,
                'news': True
            }

        # 运行多分析师分析（异步版本，使用httpx）
        agents_results = await agents.run_multi_agent_analysis_async(
            stock_info=stock_info,
            indicators=indicators,
            news_data=news_text,
            enabled_analysts=enabled_analysts
        )

        # 生成综合决策（异步版本，使用httpx）
        final_decision = await agents.make_final_decision_async(agents_results, stock_info, indicators)

        return {
            "symbol": symbol,
            "success": True,
            "stock_info": stock_info,
            "indicators": {
                'price': indicators.get('price'),
                'change_pct': indicators.get('change_pct'),
                'ma5': indicators.get('ma5'),
                'ma10': indicators.get('ma10'),
                'ma20': indicators.get('ma20'),
                'ma60': indicators.get('ma60'),
                'rsi14': indicators.get('rsi14'),
            },
            "agents_results": agents_results,
            "final_decision": final_decision,
            "agents_count": len(agents_results)
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "success": False,
            "error": str(e)
        }


# 批量分析专用的线程池
_batch_executor = ThreadPoolExecutor(max_workers=4)


@router.post("/analysis/batch")
async def batch_stock_analysis(req: BatchAnalysisReq):
    """批量股票分析（使用子进程隔离，避免阻塞）"""
    import subprocess
    import sys
    import os
    import tempfile

    # 将请求数据写入临时文件，避免shell转义问题
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        input_data = {
            'symbols': req.symbols,
            'enabled_analysts': req.enabled_analysts
        }
        json.dump(input_data, f)
        input_file = f.name

    try:
        # 运行子进程脚本
        script = '''
import sys
import os
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 读取输入数据
with open(sys.argv[1], 'r') as f:
    data = json.load(f)

symbols = data['symbols']
enabled_analysts = data.get('enabled_analysts', {})

def analyze_one(symbol, enabled_analysts):
    from backend.routers.analysis import _analyze_single_stock
    return _analyze_single_stock(symbol, enabled_analysts)

# 使用线程池并行分析
with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as executor:
    futures = {executor.submit(analyze_one, s, enabled_analysts): s for s in symbols}
    results = []
    for future in futures:
        symbol = futures[future]
        try:
            result = future.result(timeout=180)  # 每个股票3分钟超时
            results.append(result)
        except Exception as e:
            results.append({"symbol": symbol, "success": False, "error": str(e)})

print("BATCH_RESULT:" + json.dumps(results))
'''
        result = subprocess.run(
            [sys.executable, '-c', script, input_file],
            capture_output=True,
            text=True,
            timeout=600,  # 10分钟超时
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # 解析子进程输出
        processed_results = []
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.startswith('BATCH_RESULT:'):
                    processed_results = json.loads(line[len('BATCH_RESULT:'):])

        if not processed_results and result.stderr:
            print(f"❌ 批量分析子进程错误: {result.stderr[:500]}")

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="批量分析超时（10分钟）")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")
    finally:
        # 清理临时文件
        try:
            os.unlink(input_file)
        except:
            pass

    # 保存成功的分析结果到历史记录
    saved_count = 0
    try:
        for result_item in processed_results:
            if result_item.get('success') and result_item.get('stock_info'):
                final_dec = result_item.get('final_decision', {})
                discussion_res = final_dec.get('discussion', '') if isinstance(final_dec, dict) else ''
                db.save_analysis(
                    symbol=result_item.get('symbol'),
                    stock_name=result_item.get('stock_info', {}).get('name', result_item.get('symbol')),
                    period='day',
                    stock_info=result_item.get('stock_info'),
                    indicators=result_item.get('indicators'),
                    agents_results=result_item.get('agents_results'),
                    final_decision=final_dec,
                    discussion_result=discussion_res
                )
                saved_count += 1
        print(f"✅ 批量分析: 成功保存 {saved_count} 条历史记录")
    except Exception as db_err:
        print(f"❌ 批量保存历史记录失败: {db_err}")

    return {
        "success": True,
        "total": len(req.symbols),
        "analysis_mode": req.analysis_mode,
        "results": processed_results,
        "saved_count": saved_count
    }


class AnalystConfigReq(BaseModel):
    enabled_analysts: Dict[str, bool]


# 分析师配置（内存存储，简单实现）
_analyst_config = {
    'technical': True,
    'fundamental': True,
    'fund_flow': True,
    'risk': True,
    'sentiment': True,
    'news': True
}


@router.get("/analysis/config")
async def get_analyst_config():
    """获取分析师配置"""
    return {"enabled_analysts": _analyst_config}


@router.post("/analysis/config")
async def set_analyst_config(req: AnalystConfigReq):
    """设置分析师配置"""
    global _analyst_config
    _analyst_config = req.enabled_analysts
    return {"success": True, "enabled_analysts": _analyst_config}


@router.get("/hot_strategies")
async def get_hot_strategies():
    """获取热门选股策略"""
    return {
        "data": [
            {"rank": 1, "question": "MA5>MA10; 价>MA20"},
            {"rank": 2, "question": "MACD金叉; 涨幅>2%"},
            {"rank": 3, "question": "RSI14<30"}
        ]
    }


class ScreenReq(BaseModel):
    query: str
    universe: str = "ALL"


@router.post("/simple_screen")
async def simple_screen(req: ScreenReq):
    """简单选股筛选"""
    from backend.routers.stock import get_kline_data, get_indicators

    q = req.query.upper()
    test_stocks = ["600519", "000001", "0700.HK", "AAPL", "MSFT"]

    res_list = []
    for s in test_stocks:
        try:
            code, mkt = get_code_type(s)
            df = get_kline_data(code)
            m = get_indicators(df)

            ok = True
            reasons = []

            if "MA5>MA10" in q:
                if m["ma5"] > m["ma10"]:
                    reasons.append("MA5>MA10")
                else:
                    ok = False
            if "价>MA20" in q:
                if m["price"] > m["ma20"]:
                    reasons.append("价>MA20")
                else:
                    ok = False
            if "MACD金叉" in q:
                if m["macd_dif"] > m["macd_dea"] and m["macd_hist"] > 0:
                    reasons.append("MACD金叉")
                else:
                    ok = False

            if ok:
                res_list.append({
                    "input": s, "market": mkt, "metrics": m, "reasons": reasons
                })
        except:
            pass

    return {"items": res_list}
