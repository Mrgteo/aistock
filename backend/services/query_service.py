"""
Query 服务 - 查询预处理、扩展、同义词、关键词提取
"""
import re
from typing import List, Dict, Tuple


class QueryService:
    """Query预处理服务"""

    def __init__(self):
        # 同义词词典（可扩展）
        self.synonyms = {
            "AI": ["人工智能", "机器学习", "深度学习"],
            "人工智能": ["AI", "机器学习", "深度学习"],
            "康养": ["养老", "护理", "健康"],
            "养老": ["康养", "老年", "老龄"],
            "机器人": ["机械臂", "人形机器人", "智能机器人"],
            "市场": ["市场规模", "市场容量", "份额"],
            "投资": ["投资机会", "标的", "配置"],
            "增长": ["增速", "增长率", "发展空间"],
        }

        # 停用词
        self.stopwords = {
            '的', '了', '和', '是', '在', '有', '与', '对', '为', '以及',
            '等', '或', '由', '其', '于', '上', '下', '中', '内', '外',
            '将', '把', '被', '会', '能', '可', '也', '都', '而',
            '这', '那', '但', '却', '更', '又', '如果', '因为', '所以',
            '我们', '你们', '他们', '一个', '一些', '一种', '进行', '通过',
            '主要', '重要', '可能', '需要', '应该', '一定', '非常', '比较',
            '特别', '目前', '现在', '当前', '今天', '今年', '去年', '明年',
            '包括', '其中', '如下', '上述', '公司', '企业', '行业', '市场'
        }

    def preprocess(self, query: str) -> str:
        """
        预处理查询文本

        Args:
            query: 原始查询

        Returns:
            预处理后的查询
        """
        # 繁简体转换
        query = self.traditional_to_simplified(query)

        # 全角转半角
        query = self.fullwidth_to_halfwidth(query)

        # 移除特殊字符
        query = re.sub(r'[ :|\r\n\t,，。？?/`!！&^%%()\[\]{}<>]+', ' ', query)

        # 移除多余空格
        query = ' '.join(query.split())

        return query.strip()

    def traditional_to_simplified(self, text: str) -> str:
        """繁体转简体"""
        # 常用繁简对照表
        mapping = {
            '為': '为', '與': '与', '義': '义', '機': '机', '業': '业',
            '開': '开', '關': '关', '會': '会', '學': '学', '們': '们',
            '國': '国', '產': '产', '經': '经', '濟': '济', '動': '动',
            '發': '发', '陳': '陈', '術': '术', '網': '网', '資': '资',
            '軟': '软', '場': '场', '運': '运', '營': '营', '據': '据',
            '點': '点', '義': '义', '變': '变', '環': '环', '境': '境',
            '問': '问', '題': '题', '護': '护', '療': '疗', '療': '疗',
        }
        for trad, simp in mapping.items():
            text = text.replace(trad, simp)
        return text

    def fullwidth_to_halfwidth(self, text: str) -> str:
        """全角转半角"""
        result = []
        for char in text:
            code = ord(char)
            if code == 0x3000:  # 全角空格
                result.append(' ')
            elif 0xFF01 <= code <= 0xFF5E:  # 全角ASCII
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        return ''.join(result)

    def extract_keywords(self, query: str) -> List[str]:
        """
        提取查询关键词

        Args:
            query: 查询文本

        Returns:
            关键词列表
        """
        query = self.preprocess(query)
        query_lower = query.lower()

        # 提取中文词（2-6字）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', query_lower)

        # 提取英文词
        english_words = re.findall(r'[a-zA-Z]{2,20}', query_lower)

        # 提取股票代码（6位数字）
        stock_codes = re.findall(r'\b\d{6}\b', query_lower)

        # 过滤停用词
        keywords = []
        for word in chinese_words + english_words:
            if word not in self.stopwords and len(word) >= 2:
                keywords.append(word)

        keywords.extend(stock_codes)

        return list(set(keywords))[:20]  # 去重，最多20个

    def expand_with_synonyms(self, query: str) -> List[str]:
        """
        使用同义词扩展查询

        Args:
            query: 查询文本

        Returns:
            扩展后的查询列表
        """
        query = self.preprocess(query)
        keywords = self.extract_keywords(query)

        expanded_queries = [query]  # 保留原始查询

        # 对每个关键词尝试同义词替换
        for keyword in keywords:
            if keyword in self.synonyms:
                for syn in self.synonyms[keyword]:
                    if syn != keyword:
                        expanded_query = query.replace(keyword, syn)
                        if expanded_query not in expanded_queries:
                            expanded_queries.append(expanded_query)

        return expanded_queries[:5]  # 最多5个扩展查询

    def expand_query(self, query: str) -> Tuple[str, List[str]]:
        """
        完整查询扩展

        Args:
            query: 原始查询

        Returns:
            (主查询, 扩展查询列表)
        """
        query = self.preprocess(query)
        keywords = self.extract_keywords(query)

        # 构建扩展查询
        expanded = [query]

        # 1. 添加关键同义词
        for kw in keywords[:5]:
            if kw in self.synonyms:
                for syn in self.synonyms[kw][:2]:
                    new_query = query + ' ' + syn
                    if new_query not in expanded:
                        expanded.append(new_query)

        # 2. 添加关键概念
        for kw in keywords[:3]:
            if kw in self.synonyms:
                for syn in self.synonyms[kw][:1]:
                    if syn not in query:
                        new_query = query + ' ' + syn
                        if new_query not in expanded:
                            expanded.append(new_query)

        return query, expanded[:5]

    def reformulate_query(self, query: str) -> List[str]:
        """
        多角度查询改写

        Args:
            query: 原始查询

        Returns:
            多个不同角度的查询
        """
        query = self.preprocess(query)
        queries = [query]

        # 添加角度变体
        angles = [
            ("请问", "关于"),
            ("介绍", "分析", "讲解"),
            ("有哪些", "有什么", "什么"),
            ("怎么样", "如何", "好吗"),
            ("前景", "趋势", "展望"),
            ("投资机会", "标的", "推荐"),
        ]

        # 尝试不同的提问方式
        for prefixes in angles[:2]:
            for prefix in prefixes:
                if prefix not in query and len(query) > 2:
                    new_q = prefix + query[0] + query[1:] if len(query) > 2 else prefix + query
                    if new_q not in queries:
                        queries.append(new_q)

        return queries[:5]


# 单例模式
_query_service = None


def get_query_service() -> QueryService:
    """获取Query服务单例"""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service
