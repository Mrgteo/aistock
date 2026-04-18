"""
股票分析历史记录数据库 - stock_trade 专用
"""
import sqlite3
import json
import os
from datetime import datetime

# stock_trade 专用数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'stock_analysis.db')


class AnalysisDB:
    """股票分析历史记录数据库"""

    def __init__(self, db_path=None):
        """初始化数据库连接"""
        self.db_path = db_path or DB_PATH
        # 确保数据库所在目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self.init_database()

    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建分析记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                stock_name TEXT,
                analysis_date TEXT NOT NULL,
                period TEXT NOT NULL,
                stock_info TEXT,
                indicators TEXT,
                agents_results TEXT,
                final_decision TEXT,
                discussion_result TEXT,
                news_link TEXT,
                fund_link TEXT,
                created_at TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def save_analysis(self, symbol, stock_name, period='day', stock_info=None, indicators=None,
                     agents_results=None, final_decision=None, discussion_result=None, news_link='', fund_link=''):
        """保存分析记录到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 准备数据
        analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_at = datetime.now().isoformat()

        # 将复杂对象转换为JSON字符串
        stock_info_json = json.dumps(stock_info or {}, ensure_ascii=False, default=str)
        indicators_json = json.dumps(indicators or {}, ensure_ascii=False, default=str)
        agents_results_json = json.dumps(agents_results or {}, ensure_ascii=False, default=str)
        final_decision_json = json.dumps(final_decision or {}, ensure_ascii=False, default=str)
        # discussion_result 是字符串，直接存储或转为JSON字符串
        discussion_result_json = json.dumps(discussion_result) if discussion_result else ''

        cursor.execute('''
            INSERT INTO analysis_records
            (symbol, stock_name, analysis_date, period, stock_info, indicators, agents_results, final_decision, news_link, fund_link, created_at, discussion_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, stock_name, analysis_date, period, stock_info_json, indicators_json,
              agents_results_json, final_decision_json, news_link, fund_link, created_at, discussion_result_json))

        conn.commit()
        record_id = cursor.lastrowid
        conn.close()

        return record_id

    def get_all_records(self, limit=100, offset=0):
        """获取所有分析记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, symbol, stock_name, analysis_date, period, stock_info, final_decision, created_at
            FROM analysis_records
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        records = cursor.fetchall()
        conn.close()

        result = []
        for record in records:
            final_decision = {}
            stock_info = {}
            try:
                final_decision = json.loads(record[6]) if record[6] else {}
            except:
                pass
            try:
                stock_info = json.loads(record[5]) if record[5] else {}
            except:
                pass
            rating = final_decision.get('rating', '未知') if isinstance(final_decision, dict) else '未知'

            # 优先从 stock_info 获取公司名称，其次用数据库存储的 stock_name，最后用 symbol
            company_name = stock_info.get('name', record[2] or record[1]) if isinstance(stock_info, dict) else (record[2] or record[1])

            result.append({
                'id': record[0],
                'symbol': record[1],
                'stock_name': company_name,
                'analysis_date': record[3],
                'period': record[4],
                'rating': rating,
                'confidence_level': final_decision.get('confidence_level', '') if isinstance(final_decision, dict) else '',
                'created_at': record[7]
            })

        return result

    def search_records(self, keyword, limit=50):
        """搜索分析记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        search_pattern = f'%{keyword}%'
        cursor.execute('''
            SELECT id, symbol, stock_name, analysis_date, period, stock_info, final_decision, created_at
            FROM analysis_records
            WHERE symbol LIKE ? OR stock_name LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, limit))

        records = cursor.fetchall()
        conn.close()

        result = []
        for record in records:
            final_decision = {}
            stock_info = {}
            try:
                final_decision = json.loads(record[6]) if record[6] else {}
            except:
                pass
            try:
                stock_info = json.loads(record[5]) if record[5] else {}
            except:
                pass
            rating = final_decision.get('rating', '未知') if isinstance(final_decision, dict) else '未知'

            # 优先从 stock_info 获取公司名称，其次用数据库存储的 stock_name，最后用 symbol
            company_name = stock_info.get('name', record[2] or record[1]) if isinstance(stock_info, dict) else (record[2] or record[1])

            result.append({
                'id': record[0],
                'symbol': record[1],
                'stock_name': company_name,
                'analysis_date': record[3],
                'period': record[4],
                'rating': rating,
                'confidence_level': final_decision.get('confidence_level', '') if isinstance(final_decision, dict) else '',
                'created_at': record[7]
            })

        return result

    def get_record_count(self):
        """获取记录总数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM analysis_records')
        count = cursor.fetchone()[0]
        conn.close()

        return count

    def get_record_by_id(self, record_id):
        """根据ID获取详细分析记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM analysis_records WHERE id = ?
        ''', (record_id,))

        record = cursor.fetchone()
        conn.close()

        if not record:
            return None

        # record indices: 0=id, 1=symbol, 2=stock_name, 3=analysis_date, 4=period,
        # 5=stock_info, 6=indicators, 7=agents_results, 8=final_decision,
        # 9=news_link, 10=fund_link, 11=created_at, 12=discussion_result

        result = {
            'id': record[0],
            'symbol': record[1],
            'stock_name': record[2],
            'analysis_date': record[3],
            'period': record[4],
            'created_at': record[11]
        }

        try:
            result['stock_info'] = json.loads(record[5]) if record[5] else {}
        except:
            result['stock_info'] = {}

        try:
            result['indicators'] = json.loads(record[6]) if record[6] else {}
        except:
            result['indicators'] = {}

        try:
            result['agents_results'] = json.loads(record[7]) if record[7] else {}
        except:
            result['agents_results'] = {}

        try:
            result['final_decision'] = json.loads(record[8]) if record[8] else {}
        except:
            result['final_decision'] = {}

        result['news_link'] = record[9] or ''
        result['fund_link'] = record[10] or ''

        try:
            # discussion_result 可能是字符串或JSON字符串
            dr = record[12]
            if dr:
                try:
                    result['discussion_result'] = json.loads(dr)
                except:
                    # 如果不是JSON，说明是普通字符串，直接使用
                    result['discussion_result'] = dr
            else:
                result['discussion_result'] = ''
        except:
            result['discussion_result'] = ''

        return result

    def delete_record(self, record_id):
        """删除指定记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM analysis_records WHERE id = ?', (record_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()

        return deleted

    def delete_all_records(self):
        """删除所有记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM analysis_records')
        count_before = cursor.fetchone()[0]

        cursor.execute('DELETE FROM analysis_records')
        conn.commit()
        conn.close()

        return count_before


# 全局数据库实例
db = AnalysisDB()
