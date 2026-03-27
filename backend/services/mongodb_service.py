"""
MongoDB 服务 - GridFS文件存储和元数据管理
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
import gridfs

class MongoDBService:
    """MongoDB服务类，处理GridFS文件存储和集合操作"""

    def __init__(self, connection_url: str = None, database: str = None):
        # 尝试从环境变量或配置读取
        from backend.core.config import settings as app_settings
        self.connection_url = connection_url or os.getenv("MONGODB_URL", "mongodb://admin:tradingagents123@localhost:27017")
        self.database_name = database or os.getenv("MONGODB_DB", "stock_trade_reports")
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._fs: Optional[gridfs.GridFS] = None

    def connect(self):
        """建立MongoDB连接"""
        if self._client is None:
            self._client = MongoClient(self.connection_url, serverSelectionTimeoutMS=5000)
            # 验证连接
            try:
                self._client.admin.command('ping')
            except ConnectionFailure:
                raise Exception(f"MongoDB连接失败: {self.connection_url}")
            self._db = self._client[self.database_name]
            self._fs = gridfs.GridFS(self._db)
            print(f"[MongoDB] 已连接到 {self.database_name}")
        return self

    def disconnect(self):
        """关闭MongoDB连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._fs = None
            print("[MongoDB] 连接已关闭")

    @property
    def fs(self) -> gridfs.GridFS:
        """获取GridFS实例"""
        if self._fs is None:
            self.connect()
        return self._fs

    @property
    def db(self) -> Database:
        """获取数据库实例"""
        if self._db is None:
            self.connect()
        return self._db

    # ========== 研报集合操作 ==========

    def save_report(self, file_data: bytes, filename: str, title: str,
                    report_type: str, industry: str = None,
                    publisher: str = None) -> str:
        """
        保存研报到GridFS并记录元数据

        Args:
            file_data: 文件二进制数据
            filename: 原始文件名
            title: 报告标题
            report_type: 报告类型 (行业报告/公司研报/策略报告)
            industry: 行业分类
            publisher: 发布机构

        Returns:
            str: 报告ID
        """
        # 存储文件到GridFS
        file_id = self.fs.put(
            file_data,
            filename=filename,
            content_type=self._get_content_type(filename),
            metadata={
                "title": title,
                "report_type": report_type,
                "industry": industry,
                "publisher": publisher,
                "upload_time": datetime.utcnow()
            }
        )

        # 记录元数据到reports集合
        report_doc = {
            "title": title,
            "file_name": filename,
            "file_type": self._get_file_type(filename),
            "file_size": len(file_data),
            "file_id": file_id,
            "content_text": "",  # 初始为空，提取后更新
            "chunks": [],
            "metadata": {
                "report_type": report_type,
                "industry": industry,
                "publisher": publisher,
            },
            "upload_time": datetime.utcnow(),
            "uploader": "admin",
            "status": "uploaded"  # uploaded -> processing -> processed -> failed
        }

        result = self.db.reports.insert_one(report_doc)
        report_id = str(result.inserted_id)

        print(f"[MongoDB] 研报已保存: {title} (ID: {report_id})")
        return report_id

    def update_report_content(self, report_id: str, content_text: str,
                              chunks: List[Dict] = None, status: str = "processed"):
        """更新报告内容和分块信息"""
        update_data = {
            "content_text": content_text,
            "status": status
        }
        if chunks is not None:
            update_data["chunks"] = chunks

        self.db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": update_data}
        )
        print(f"[MongoDB] 报告 {report_id} 内容已更新，状态: {status}")

    def get_report(self, report_id: str) -> Optional[Dict]:
        """获取报告详情"""
        try:
            report = self.db.reports.find_one({"_id": ObjectId(report_id)})
            if report:
                report["_id"] = str(report["_id"])
                if "file_id" in report:
                    report["file_id"] = str(report["file_id"])
            return report
        except Exception as e:
            print(f"[MongoDB] 获取报告失败: {e}")
            return None

    def get_report_file(self, report_id: str) -> Optional[bytes]:
        """获取报告文件二进制数据"""
        report = self.get_report(report_id)
        if report and "file_id" in report:
            try:
                file_id = ObjectId(report["file_id"])
                return self.fs.get(file_id).read()
            except Exception as e:
                print(f"[MongoDB] 获取文件失败: {e}")
        return None

    def list_reports(self, skip: int = 0, limit: int = 20,
                     report_type: str = None) -> List[Dict]:
        """获取报告列表"""
        query = {}
        if report_type:
            query["metadata.report_type"] = report_type

        cursor = self.db.reports.find(query).sort("upload_time", -1).skip(skip).limit(limit)
        reports = []
        for r in cursor:
            r["_id"] = str(r["_id"])
            if "file_id" in r:
                r["file_id"] = str(r["file_id"])
            # 不返回完整content_text以节省带宽
            if "content_text" in r and len(r["content_text"]) > 500:
                r["content_text"] = r["content_text"][:500] + "..."
            reports.append(r)
        return reports

    def delete_report(self, report_id: str) -> bool:
        """删除报告及其文件"""
        report = self.get_report(report_id)
        if not report:
            return False

        # 删除GridFS文件
        if "file_id" in report:
            try:
                self.fs.delete(ObjectId(report["file_id"]))
            except Exception:
                pass

        # 删除元数据
        self.db.reports.delete_one({"_id": ObjectId(report_id)})
        print(f"[MongoDB] 报告已删除: {report_id}")
        return True

    def update_report_status(self, report_id: str, status: str):
        """更新报告处理状态"""
        self.db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"status": status}}
        )

    # ========== 知识库集合操作 ==========

    def save_knowledge(self, file_data: bytes, filename: str, title: str,
                       tags: List[str] = None) -> str:
        """保存知识库文件"""
        file_id = self.fs.put(
            file_data,
            filename=filename,
            content_type=self._get_content_type(filename),
            metadata={
                "title": title,
                "tags": tags or [],
                "upload_time": datetime.utcnow()
            }
        )

        kb_doc = {
            "title": title,
            "file_name": filename,
            "file_type": self._get_file_type(filename),
            "file_id": file_id,
            "content_text": "",
            "chunks": [],
            "vector_ids": [],
            "metadata": {
                "source": "manual_upload",
                "tags": tags or []
            },
            "upload_time": datetime.utcnow(),
            "status": "uploaded"
        }

        result = self.db.knowledge_base.insert_one(kb_doc)
        return str(result.inserted_id)

    def update_knowledge_content(self, kb_id: str, content_text: str,
                                 chunks: List[Dict] = None,
                                 vector_ids: List[str] = None,
                                 status: str = "indexed"):
        """更新知识库内容"""
        update_data = {
            "content_text": content_text,
            "status": status
        }
        if chunks is not None:
            update_data["chunks"] = chunks
        if vector_ids is not None:
            update_data["vector_ids"] = vector_ids

        self.db.knowledge_base.update_one(
            {"_id": ObjectId(kb_id)},
            {"$set": update_data}
        )

    def get_knowledge(self, kb_id: str) -> Optional[Dict]:
        """获取知识库条目"""
        try:
            kb = self.db.knowledge_base.find_one({"_id": ObjectId(kb_id)})
            if kb:
                kb["_id"] = str(kb["_id"])
                if "file_id" in kb:
                    kb["file_id"] = str(kb["file_id"])
            return kb
        except Exception:
            return None

    def list_knowledge(self, skip: int = 0, limit: int = 20) -> List[Dict]:
        """获取知识库列表"""
        cursor = self.db.knowledge_base.find({}).sort("upload_time", -1).skip(skip).limit(limit)
        items = []
        for k in cursor:
            k["_id"] = str(k["_id"])
            if "file_id" in k:
                k["file_id"] = str(k["file_id"])
            if "content_text" in k and len(k["content_text"]) > 300:
                k["content_text"] = k["content_text"][:300] + "..."
            items.append(k)
        return items

    def delete_knowledge(self, kb_id: str) -> bool:
        """删除知识库条目"""
        kb = self.get_knowledge(kb_id)
        if not kb:
            return False

        if "file_id" in kb:
            try:
                self.fs.delete(ObjectId(kb["file_id"]))
            except Exception:
                pass

        self.db.knowledge_base.delete_one({"_id": ObjectId(kb_id)})
        return True

    # ========== 分析结果集合操作 ==========

    def save_analysis_result(self, report_id: str, query: str,
                             result: Dict, ai_response: str,
                             report_title: str = None,
                             mentioned_stocks: List[Dict] = None,
                             mentioned_industries: List[Dict] = None) -> str:
        """保存分析结果"""
        doc = {
            "report_id": ObjectId(report_id),
            "report_title": report_title or "",
            "query": query,
            "result": result,
            "ai_response": ai_response,
            "mentioned_stocks": mentioned_stocks or [],
            "mentioned_industries": mentioned_industries or [],
            "created_at": datetime.utcnow()
        }
        result_insert = self.db.analysis_results.insert_one(doc)
        return str(result_insert.inserted_id)

    def get_analysis_history(self, report_id: str = None,
                             skip: int = 0, limit: int = 20) -> List[Dict]:
        """获取分析历史"""
        query = {}
        if report_id:
            query["report_id"] = ObjectId(report_id)

        cursor = self.db.analysis_results.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        for item in cursor:
            item["_id"] = str(item["_id"])
            item["report_id"] = str(item["report_id"])
            items.append(item)
        return items

    def list_all_analysis_history(self, skip: int = 0, limit: int = 20) -> List[Dict]:
        """获取所有分析历史记录（用于研报分析历史面板）"""
        cursor = self.db.analysis_results.find(
            {},
            {"report_id": 1, "report_title": 1, "query": 1, "mentioned_stocks": 1,
             "mentioned_industries": 1, "created_at": 1}
        ).sort("created_at", -1).skip(skip).limit(limit)

        items = []
        for item in cursor:
            item["_id"] = str(item["_id"])
            item["report_id"] = str(item["report_id"])
            # 简化股票和行业信息用于列表展示
            stock_count = len(item.get("mentioned_stocks", []))
            industry_count = len(item.get("mentioned_industries", []))
            item["summary"] = f"涉及 {stock_count} 只股票, {industry_count} 个行业"
            # 移除完整数据以节省带宽
            item.pop("mentioned_stocks", None)
            item.pop("mentioned_industries", None)
            items.append(item)
        return items

    def get_analysis_result(self, analysis_id: str) -> Optional[Dict]:
        """获取单条分析结果详情"""
        try:
            item = self.db.analysis_results.find_one({"_id": ObjectId(analysis_id)})
            if item:
                item["_id"] = str(item["_id"])
                item["report_id"] = str(item["report_id"])
            return item
        except Exception:
            return None

    def delete_analysis_result(self, analysis_id: str) -> bool:
        """删除单条分析结果"""
        try:
            result = self.db.analysis_results.delete_one({"_id": ObjectId(analysis_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    # ========== 辅助方法 ==========

    def _get_content_type(self, filename: str) -> str:
        """根据文件名获取Content-Type"""
        ext = filename.lower().split('.')[-1]
        types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain'
        }
        return types.get(ext, 'application/octet-stream')

    def _get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        ext = filename.lower().split('.')[-1]
        return ext if ext in ['pdf', 'docx', 'doc', 'txt'] else 'unknown'

    def ensure_indexes(self):
        """创建必要的索引"""
        # reports集合索引
        self.db.reports.create_index("upload_time")
        self.db.reports.create_index("status")
        self.db.reports.create_index("metadata.report_type")

        # knowledge_base集合索引
        self.db.knowledge_base.create_index("upload_time")
        self.db.knowledge_base.create_index("status")
        self.db.knowledge_base.create_index("metadata.tags")

        # analysis_results集合索引
        self.db.analysis_results.create_index("report_id")
        self.db.analysis_results.create_index("created_at")

        print("[MongoDB] 索引已创建")


# 单例模式全局实例
_mongodb_service: Optional[MongoDBService] = None

def get_mongodb_service() -> MongoDBService:
    """获取MongoDB服务单例"""
    global _mongodb_service
    if _mongodb_service is None:
        _mongodb_service = MongoDBService().connect()
        _mongodb_service.ensure_indexes()
    return _mongodb_service
