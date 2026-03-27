"""
市场数据路由 - 实时新闻和全球股指
"""

import json
import re
import time
import requests
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

router = APIRouter(tags=["市场数据"])

# 缓存新闻数据
_news_cache = {
    "cls": {"news": [], "timestamp": 0},
    "ths": {"news": [], "timestamp": 0, "page": 1}
}
CACHE_DURATION = 30  # 30秒缓存


def get_cls_telegraph() -> List[dict]:
    """获取财联社电报"""
    try:
        url = "https://www.cls.cn/nodeapi/telegraphList"
        headers = {
            "Referer": "https://www.cls.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.60"
        }

        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        if data.get("error") == 0 and data.get("data"):
            roll_data = data["data"].get("roll_data", [])
            results = []
            for item in roll_data:
                ctime = item.get("ctime", 0)
                data_time = time.localtime(ctime)
                subjects = item.get("subjects") or []
                subject_list = [s.get("subject_name", "") for s in subjects if s and s.get("subject_name")]

                results.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "time": time.strftime("%H:%M:%S", data_time),
                    "datetime": time.strftime("%Y-%m-%d %H:%M:%S", data_time),
                    "date": time.strftime("%Y-%m-%d", data_time),
                    "timestamp": ctime,
                    "is_red": item.get("level", "C") != "C",
                    "source": "财联社电报",
                    "url": item.get("shareurl", ""),
                    "subjects": subject_list
                })
            return results
        return []
    except Exception as e:
        print(f"Failed to fetch CLS telegraph: {e}")
        return []


def get_ths_news(page: int = 1, page_size: int = 20) -> dict:
    """获取同花顺财经新闻（按页码分页）"""
    try:
        url = "https://news.10jqka.com.cn/tapp/news/push/stock/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.60",
            "Referer": "https://www.10jqka.com.cn/"
        }

        params = {
            "page": page,
            "tag": "",
            "track": "website",
            "pagesize": page_size
        }

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()

        if str(data.get("code")) == "200":
            news_data = data.get("data", {})
            items = news_data.get("list", [])
            total = news_data.get("total", 0)

            results = []
            for item in items:
                # 获取时间戳 - 同花顺使用 ctime 字段
                ctime = item.get("ctime", 0)
                item_time = 0
                if ctime:
                    try:
                        item_time = int(ctime)
                    except:
                        item_time = 0

                # 格式化时间和日期
                if item_time > 0:
                    time_str = time.strftime("%H:%M:%S", time.localtime(item_time))
                    date_str = time.strftime("%Y-%m-%d", time.localtime(item_time))
                else:
                    time_str = ""
                    date_str = ""

                # 处理标签
                tags = item.get("tags", [])
                tag_names = []
                if isinstance(tags, list):
                    tag_names = [t.get("name", "") for t in tags if isinstance(t, dict) and t.get("name")]

                # 检查是否重要新闻 - import=3 或 color=2 表示重要
                import_val = str(item.get("import", "0"))
                color_val = str(item.get("color", "0"))
                is_red = import_val == "3" or color_val == "2"

                results.append({
                    "id": str(item.get("id", "")),
                    "title": item.get("title", ""),
                    "content": item.get("digest", "") or item.get("title", ""),
                    "time": time_str,
                    "datetime": f"{date_str} {time_str}",
                    "date": date_str,
                    "timestamp": item_time,
                    "is_red": is_red,
                    "source": "同花顺财经",
                    "url": item.get("url", ""),
                    "subjects": tag_names
                })

            # 检查是否有更多
            try:
                total_num = int(total) if total else 0
            except:
                total_num = 0
            has_more = len(items) >= page_size and (page * page_size) < total_num

            return {
                "news": results,
                "total": total_num,
                "has_more": has_more,
                "current_page": page,
                "next_page": page + 1 if has_more else page
            }
        return {"news": [], "total": 0, "has_more": False, "current_page": page, "next_page": page}
    except Exception as e:
        print(f"Failed to fetch THS news: {e}")
        return {"news": [], "total": 0, "has_more": False, "current_page": page, "next_page": page}


def get_tx_code_for_index(code: str) -> str:
    """转换代码为腾讯API格式"""
    if code.startswith("sh") or code.startswith("sz"):
        return code
    elif code.startswith("hk"):
        return code  # hkHSI 保持原样
    elif code.startswith("us"):
        return code  # us.DJI 保持原样（含点号）
    return code


def get_yahoo_index_data(symbol: str) -> dict:
    """从Yahoo Finance获取指数数据"""
    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return {}
        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        prev_close = meta.get("chartPreviousClose")

        # 手动计算涨跌幅
        change_pct = 0
        if price and prev_close:
            change_pct = (price - prev_close) / prev_close * 100

        return {
            "price": round(price, 2) if price else "--",
            "change": round(change_pct, 2),
            "prev_close": prev_close
        }
    except Exception as e:
        print(f"Yahoo API failed for {symbol}: {e}")
        return {}


def get_tencent_index_data(code: str) -> dict:
    """从腾讯API获取单个指数数据"""
    try:
        url = f"https://qt.gtimg.cn/q={code}"
        headers = {
            "Referer": "https://finance.qq.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        text = resp.text.strip()

        # 解析腾讯API数据格式
        # 格式: v_sz399006="51~name~code~price~yestclose~open~vol~...~date~change~pchange~..."
        # 字段以~分隔，常见字段位置：
        # [1]=名称, [3]=当前价格, [4]=昨日收盘, [5]=今日开盘, [31]=涨跌额, [32]=涨跌幅(%), [33]=时间戳
        if not text or text == 'null' or '~' not in text:
            return {}

        # 提取~分隔的数据
        import re
        match = re.search(r'v_\w+="([^"]+)"', text)
        if not match:
            return {}

        fields = match.group(1).split('~')
        if len(fields) < 33:
            return {}

        name = fields[1] if fields[1] else ""
        price = fields[3] if fields[3] else "--"
        yestclose = fields[4] if fields[4] else "0"
        open_price = fields[5] if fields[5] else "0"
        # 腾讯字段: [31]=涨跌额, [32]=涨跌幅(%)
        change_str = fields[31] if len(fields) > 31 else "0"
        percent_str = fields[32] if len(fields) > 32 else "0"

        # 转换涨跌额
        try:
            change_val = float(change_str)
        except:
            change_val = 0

        # 转换涨跌幅（已经是数值，如1.30表示1.30%）
        try:
            percent_val = float(percent_str)
        except:
            percent_val = 0

        return {
            'name': name,
            'price': price,
            'open': open_price,
            'yestclose': yestclose,
            'change': change_val,
            'percent': percent_val
        }
    except Exception as e:
        print(f"Failed to fetch Tencent index {code}: {e}")
        return {}


def get_global_indices() -> dict:
    """获取全球股指 - 使用腾讯API单次调用，高效获取所有数据"""
    result = {
        "common": [],
        "cn": [],
        "hk": [],
        "us": [],
        "europe": [],
        "asia": []
    }

    try:
        # 使用腾讯代理API，一次调用获取所有指数数据
        url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/rank/indexRankDetail2"
        headers = {
            "Referer": "https://stockapp.finance.qq.com/mstats",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.60"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        if data.get("code") == 0 or data.get("data"):
            all_data = data.get("data", {})

            # A股常用指数名称（必须精确匹配）
            cn_common_names = ["上证指数", "深证成指", "创业板指", "沪深300", "上证50"]

            # 用于去重的已添加代码集合
            added_codes = {"common": set(), "cn": set(), "hk": set(), "us": set(), "europe": set(), "asia": set()}

            # 第一遍：遍历所有数据，按location分类到各区域
            for region_name, indices in all_data.items():
                if not isinstance(indices, list):
                    continue

                for item in indices:
                    name = item.get("name", "")
                    code = item.get("qtcode", item.get("code", ""))
                    price = item.get("zxj", "--")
                    change = item.get("zdf", "0")
                    location = item.get("location", "")

                    # 转换代码格式（移除s_前缀）
                    api_code = code.replace("s_", "") if code.startswith("s_") else code

                    # 获取开盘价（如果API提供）
                    open_price = item.get("open", item.get("ksc", "--"))

                    # 使用时间基准判断市场状态（更准确）
                    state = is_market_open(api_code)

                    index_info = {
                        "name": name,
                        "code": api_code,
                        "price": price,
                        "open": open_price,
                        "change": float(change) if change else 0,
                        "state": state
                    }

                    # 根据location分发到对应区域（去重）
                    # 排除富时中国A50指数（XIN9），它属于新加坡但location标注为上海
                    exclude_codes = {"XIN9", "ftXIN9", "gzXIN9"}
                    if location in ["上海", "深圳"] and api_code not in exclude_codes:
                        if api_code not in added_codes["cn"]:
                            result["cn"].append(index_info)
                            added_codes["cn"].add(api_code)
                    elif location == "香港":
                        if api_code not in added_codes["hk"]:
                            result["hk"].append(index_info)
                            added_codes["hk"].add(api_code)
                    elif location in ["纽约", "纳斯达克"]:
                        if api_code not in added_codes["us"]:
                            result["us"].append(index_info)
                            added_codes["us"].add(api_code)
                    elif location in ["伦敦", "巴黎", "法兰克福", "米兰", "阿姆斯特丹", "马德里", "欧洲"]:
                        if api_code not in added_codes["europe"]:
                            result["europe"].append(index_info)
                            added_codes["europe"].add(api_code)
                    elif location in ["东京", "首尔", "台湾", "孟买", "新加坡", "吉隆坡"]:
                        if api_code not in added_codes["asia"]:
                            result["asia"].append(index_info)
                            added_codes["asia"].add(api_code)

            # 第二遍：从cn中筛选出5个常用指数到common（按固定顺序）
            common_found = []
            for cn_idx in result["cn"]:
                if cn_idx["name"] in cn_common_names:
                    common_found.append(cn_idx)

            # 如果cn中找到的少于5个，从腾讯API补充缺失的常用指数
            found_names = {idx["name"] for idx in common_found}
            missing_names = [n for n in cn_common_names if n not in found_names]

            if missing_names:
                # 腾讯代码映射：A股常用指数
                code_mapping = {
                    "创业板指": "sz399006",
                    "沪深300": "sh000300",
                    "上证50": "sh000016",
                }

                for name in missing_names:
                    code = code_mapping.get(name)
                    if code:
                        data = get_tencent_index_data(code)
                        if data and data.get('price') and data.get('price') != '--':
                            # 计算涨跌额（基于今日开盘和当前价）
                            open_price = float(data.get('open', 0)) if data.get('open', '0').replace('.', '').isdigit() else 0
                            current_price = float(data.get('price', 0)) if str(data.get('price', '0')).replace('.', '').isdigit() else 0
                            change_amount = current_price - open_price if open_price > 0 else 0

                            index_info = {
                                "name": name,
                                "code": code,
                                "price": data.get('price', '--'),
                                "open": data.get('open', '--'),
                                "change": data.get('percent', 0),  # 使用涨跌幅百分比
                                "change_amount": change_amount,
                                "state": is_market_open(code)
                            }
                            common_found.append(index_info)
                            # 添加到cn区域
                            if code not in added_codes["cn"]:
                                result["cn"].append(index_info)
                                added_codes["cn"].add(code)

            # 按cn_common_names的固定顺序排序
            common_found.sort(key=lambda x: cn_common_names.index(x["name"]) if x["name"] in cn_common_names else 999)
            result["common"] = common_found[:5]  # 确保最多5个

            # 确保恒生科技指数在港股列表中
            hk_names = {idx["name"] for idx in result["hk"]}
            if "恒生科技指数" not in hk_names:
                hktech_data = get_tencent_index_data("hkHSTECH")
                if hktech_data and hktech_data.get('price') and hktech_data.get('price') != '--':
                    index_info = {
                        "name": "恒生科技指数",
                        "code": "hkHSTECH",
                        "price": hktech_data.get('price', '--'),
                        "open": hktech_data.get('open', '--'),
                        "change": hktech_data.get('percent', 0),
                        "state": is_market_open("hkHSTECH")
                    }
                    result["hk"].insert(0, index_info)

    except Exception as e:
        print(f"Failed to fetch global indices: {e}")

    return result


def is_market_open_yahoo(symbol: str) -> str:
    """通过Yahoo Finance判断市场状态"""
    try:
        import pytz
        from datetime import datetime

        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if result:
            meta = result[0].get("meta", {})
            tz_name = meta.get("exchangeTimezoneName", "UTC")
            market_time = meta.get("regularMarketTime")

            if market_time and tz_name:
                tz = pytz.timezone(tz_name)
                now = datetime.now(tz)
                market_dt = datetime.fromtimestamp(market_time, tz)

                # 判断是否周末
                if market_dt.weekday() >= 5:
                    return "closed"

                # 判断数据是否今天
                if market_dt.date() < now.date():
                    return "closed"

                # 根据时区判断当前是否在交易时间内
                hour = now.hour
                minute = now.minute
                current_minutes = hour * 60 + minute

                # 各主要市场交易时间（本地时间）
                market_hours = {
                    "Asia/Tokyo": (9 * 60, 15 * 60),      # 9:00-15:00
                    "Asia/Seoul": (9 * 60, 15 * 60 + 30),  # 9:00-15:30
                    "Asia/Taipei": (9 * 60, 13 * 60 + 30), # 9:00-13:30
                    "Asia/Kolkata": (9 * 60 + 15, 15 * 60 + 30), # 9:15-15:30
                    "Asia/Singapore": (9 * 60, 17 * 60),   # 9:00-17:00
                    "Asia/Shanghai": (9 * 60 + 30, 15 * 60), # 9:30-15:00
                    "Europe/London": (8 * 60, 16 * 60 + 30), # 8:00-16:30
                    "Europe/Frankfurt": (9 * 60, 17 * 60),  # 9:00-17:00
                    "Europe/Paris": (9 * 60, 17 * 60),     # 9:00-17:00
                    "America/New_York": (9 * 60 + 30, 16 * 60), # 9:30-16:00
                }

                if tz_name in market_hours:
                    open_time, close_time = market_hours[tz_name]
                    if open_time <= current_minutes < close_time:
                        return "open"
                    return "closed"
                return "closed"
    except Exception as e:
        print(f"Error checking market state for {symbol}: {e}")
    return "closed"


def is_market_open(code: str) -> str:
    """精确判断市场是否开市，返回 'open' 或 'closed'（使用北京时间）"""
    import datetime
    now = datetime.datetime.now()
    weekday = now.weekday()

    # 周六周日休市
    if weekday >= 5:
        return "closed"

    hour = now.hour
    minute = now.minute
    current_minutes = hour * 60 + minute

    if code.startswith("us"):
        # 美股：北京时间换算（美国东部时间+13小时，冬令时+12小时）
        # 美股交易时间：夏令时 21:30-04:00 北京时间，冬令时 22:30-05:00 北京时间
        # 简化判断：北京时间 21:30-04:00（次日）视为开市
        if hour >= 21 or hour < 4:
            return "open"
        return "closed"
    elif code.startswith("hk"):
        # 港股：北京时间 9:00-9:30（盘前竞价），9:30-12:00，13:00-16:00
        # 9:00-9:30 盘前 + 9:30-12:00 上午 + 13:00-16:00 下午
        if (9 * 60 <= current_minutes < 12 * 60) or (13 * 60 <= current_minutes < 16 * 60):
            return "open"
        return "closed"
    elif code.startswith("sh") or code.startswith("sz"):
        # A股：北京时间 9:15-9:25（盘前竞价），9:30-11:30，13:00-15:00
        # 9:15-9:25 盘前竞价 + 9:30-11:30 上午 + 13:00-15:00 下午
        if (9 * 60 + 15 <= current_minutes < 11 * 60 + 30) or (13 * 60 <= current_minutes < 15 * 60):
            return "open"
        return "closed"
    else:
        # 其他：简单判断工作时间内
        if 9 * 60 + 30 <= current_minutes < 15 * 60:
            return "open"
        return "closed"


@router.get("/telegraph")
async def get_telegraph(
    source: str = Query("cls", description="数据源: cls=财联社, ths=同花顺"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量")
):
    """
    获取实时新闻电报
    - source: cls=财联社电报, ths=同花顺财经
    - page: 页码（仅对ths有效）
    """
    global _news_cache

    if source == "cls":
        # 检查缓存
        if time.time() - _news_cache["cls"]["timestamp"] < CACHE_DURATION:
            return {
                "source": source,
                "news": _news_cache["cls"]["news"],
                "timestamp": int(time.time()),
                "has_more": False
            }

        news = get_cls_telegraph()

        # 更新缓存
        _news_cache["cls"]["news"] = news
        _news_cache["cls"]["timestamp"] = time.time()

        return {
            "source": source,
            "news": news,
            "timestamp": int(time.time()),
            "has_more": False
        }

    elif source == "ths":
        # 同花顺不使用缓存，每次都请求最新数据
        result = get_ths_news(page=page, page_size=page_size)
        news = result.get("news", [])

        return {
            "source": source,
            "news": news,
            "total": result.get("total", 0),
            "timestamp": int(time.time()),
            "has_more": result.get("has_more", False),
            "current_page": result.get("current_page", page),
            "next_page": result.get("next_page", page)
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid source")


@router.get("/telegraph/more")
async def get_telegraph_more(
    source: str = Query("ths", description="数据源: ths=同花顺"),
    page: int = Query(2, description="下一页页码")
):
    """
    获取更多历史新闻（分页）
    """
    if source == "ths":
        result = get_ths_news(page=page)
        return {
            "source": source,
            "news": result.get("news", []),
            "total": result.get("total", 0),
            "has_more": result.get("has_more", False),
            "current_page": result.get("current_page", page),
            "next_page": result.get("next_page", page)
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid source")


@router.get("/global_indices")
async def get_indices():
    """获取全球股指数据"""
    result = get_global_indices()
    return result


@router.get("/news/cls")
async def get_cls_news():
    """获取财联社电报"""
    news = get_cls_telegraph()
    return {
        "news": news,
        "timestamp": int(time.time())
    }


@router.get("/news/ths")
async def get_ths_news_api(
    page: int = Query(1, description="页码")
):
    """获取同花顺财经新闻"""
    result = get_ths_news(page=page)
    return {
        "news": result.get("news", []),
        "total": result.get("total", 0),
        "has_more": result.get("has_more", False),
        "current_page": result.get("current_page", page),
        "next_page": result.get("next_page", page),
        "timestamp": int(time.time())
    }
