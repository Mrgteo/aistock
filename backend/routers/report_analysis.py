"""
研报分析路由 - AI研报分析模块API
"""
import os
import asyncio
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from pydantic import BaseModel

from backend.services.mongodb_service import get_mongodb_service
from backend.services.rag_service import get_rag_service
from backend.services.report_service import get_report_service

router = APIRouter(prefix="/api/report", tags=["研报分析"])


# ========== 请求/响应模型 ==========

class AnalyzeReq(BaseModel):
    report_id: str
    query: str
    use_knowledge_base: bool = True
    use_rag: bool = True
    top_k: int = 5


class AnalyzeResponse(BaseModel):
    success: bool
    analysis_id: Optional[str] = None
    report_title: Optional[str] = None
    mentioned_stocks: Optional[List[dict]] = None
    mentioned_industries: Optional[List[dict]] = None
    ai_analysis: Optional[str] = None
    sources: Optional[List[dict]] = None
    error: Optional[str] = None


class ReportListResponse(BaseModel):
    success: bool
    reports: List[dict]
    total: int


class KnowledgeUploadReq(BaseModel):
    title: str
    tags: List[str] = []


# ========== 研报上传接口 ==========

@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    title: str = Form(...),
    report_type: str = Form("行业报告"),
    industry: str = Form(None),
    publisher: str = Form(None)
):
    """上传研报文件"""
    # 验证文件类型
    allowed_types = ["pdf", "docx", "doc", "txt"]
    file_ext = file.filename.lower().split('.')[-1]

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，仅支持: {', '.join(allowed_types)}"
        )

    # 读取文件内容
    file_content = await file.read()

    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 保存到MongoDB
    try:
        mongodb = get_mongodb_service()
        report_id = mongodb.save_report(
            file_data=file_content,
            filename=file.filename,
            title=title,
            report_type=report_type,
            industry=industry,
            publisher=publisher
        )

        # 后台异步处理
        asyncio.create_task(
            process_report_background(report_id, file_content, file.filename)
        )

        return {
            "success": True,
            "report_id": report_id,
            "message": "上传成功，正在后台处理..."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


async def process_report_background(report_id: str, file_content: bytes, filename: str):
    """后台处理报告（上传分析模块不需要向量化）"""
    try:
        rag_service = get_rag_service()
        await rag_service.process_report(report_id, file_content, filename, do_vectorize=False)
    except Exception as e:
        print(f"[ReportAPI] 后台处理失败: {e}")


# ========== 研报列表接口 ==========

@router.get("/list")
async def list_reports(
    skip: int = 0,
    limit: int = 20,
    report_type: str = None
):
    """获取研报列表"""
    try:
        mongodb = get_mongodb_service()
        reports = mongodb.list_reports(skip=skip, limit=limit, report_type=report_type)
        return {
            "success": True,
            "reports": reports,
            "total": len(reports)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


# ========== 研报详情接口 ==========

@router.get("/{report_id}")
async def get_report(report_id: str):
    """获取研报详情"""
    try:
        mongodb = get_mongodb_service()
        report = mongodb.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        return {
            "success": True,
            "report": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


# ========== 研报分析接口 ==========

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_report(req: AnalyzeReq):
    """分析研报内容"""
    try:
        rag_service = get_rag_service()
        result = await rag_service.analyze_with_rag(
            report_id=req.report_id,
            query=req.query,
            use_knowledge_base=req.use_knowledge_base,
            use_rag=req.use_rag,
            top_k=req.top_k
        )

        if not result.get("success"):
            return AnalyzeResponse(
                success=False,
                error=result.get("error", "分析失败")
            )

        return AnalyzeResponse(
            success=True,
            analysis_id=result.get("analysis_id"),
            report_title=result.get("report_title"),
            mentioned_stocks=result.get("mentioned_stocks"),
            mentioned_industries=result.get("mentioned_industries"),
            ai_analysis=result.get("ai_analysis"),
            sources=result.get("sources")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


# ========== 研报删除接口 ==========

@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """删除研报"""
    try:
        mongodb = get_mongodb_service()

        # 尝试从Chroma删除向量
        try:
            from backend.services.chroma_service import get_chroma_service
            chroma = get_chroma_service()
            chroma.delete_by_report_id("report_chunks", report_id)
        except Exception as e:
            print(f"[ReportAPI] 删除Chroma向量失败: {e}")

        # 删除MongoDB记录
        success = mongodb.delete_report(report_id)

        if not success:
            raise HTTPException(status_code=404, detail="报告不存在")

        return {"success": True, "message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ========== 分析历史接口 ==========

@router.get("/{report_id}/history")
async def get_analysis_history(report_id: str, skip: int = 0, limit: int = 20):
    """获取分析历史"""
    try:
        mongodb = get_mongodb_service()
        history = mongodb.get_analysis_history(report_id, skip=skip, limit=limit)

        return {
            "success": True,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.get("/history/all")
async def list_all_analysis_history(skip: int = 0, limit: int = 50):
    """获取所有分析历史记录"""
    try:
        mongodb = get_mongodb_service()
        history = mongodb.list_all_analysis_history(skip=skip, limit=limit)

        return {
            "success": True,
            "history": history,
            "total": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.get("/history/detail/{analysis_id}")
async def get_analysis_detail(analysis_id: str):
    """获取分析结果详情"""
    try:
        mongodb = get_mongodb_service()
        result = mongodb.get_analysis_result(analysis_id)

        if not result:
            raise HTTPException(status_code=404, detail="分析记录不存在")

        return {
            "success": True,
            "analysis": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")


@router.delete("/history/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """删除分析历史记录"""
    try:
        mongodb = get_mongodb_service()
        success = mongodb.delete_analysis_result(analysis_id)

        if not success:
            raise HTTPException(status_code=404, detail="分析记录不存在")

        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ========== 知识库接口 ==========

@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    title: str = Form(...),
    tags: str = Form("")
):
    """上传知识库文件"""
    allowed_types = ["pdf", "docx", "doc", "txt"]
    file_ext = file.filename.lower().split('.')[-1]

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，仅支持: {', '.join(allowed_types)}"
        )

    file_content = await file.read()

    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        mongodb = get_mongodb_service()
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

        kb_id = mongodb.save_knowledge(
            file_data=file_content,
            filename=file.filename,
            title=title,
            tags=tags_list
        )

        # 不再自动后台处理，等待用户手动点击解析

        return {
            "success": True,
            "kb_id": kb_id,
            "message": "上传成功，请在列表中点击'解析'按钮进行索引"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


async def process_knowledge_background(kb_id: str, file_content: bytes,
                                       filename: str, tags: List[str]):
    """后台处理知识库"""
    mongodb = get_mongodb_service()
    try:
        rag_service = get_rag_service()
        # 传入mongodb实例，避免后台任务中获取失败
        result = await rag_service.process_knowledge(kb_id, file_content, filename, tags, mongodb)
        if not result.get("success"):
            print(f"[ReportAPI] 知识库处理失败: {result.get('error')}")
            mongodb.update_knowledge_status(kb_id, "failed")
    except Exception as e:
        print(f"[ReportAPI] 知识库后台处理失败: {e}")
        import traceback
        traceback.print_exc()
        if mongodb:
            mongodb.update_knowledge_status(kb_id, "failed")


@router.get("/knowledge/list")
async def list_knowledge(skip: int = 0, limit: int = 20):
    """获取知识库列表"""
    try:
        mongodb = get_mongodb_service()
        items = mongodb.list_knowledge(skip=skip, limit=limit)

        return {
            "success": True,
            "items": items,
            "total": len(items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.post("/knowledge/{kb_id}/process")
async def process_knowledge(kb_id: str):
    """手动解析知识库文件"""
    try:
        mongodb = get_mongodb_service()
        kb = mongodb.get_knowledge(kb_id)

        if not kb:
            raise HTTPException(status_code=404, detail="知识库条目不存在")

        # 获取文件内容
        file_data = mongodb.get_knowledge_file(kb_id)
        if not file_data:
            raise HTTPException(status_code=400, detail="文件不存在")

        # 更新状态为处理中，并设置初始进度
        mongodb.update_knowledge_status(kb_id, "processing")
        mongodb.update_knowledge_progress(kb_id, {"stage": "starting", "progress": 0, "message": "正在启动解析..."})

        # 后台处理
        asyncio.create_task(
            process_knowledge_background(kb_id, file_data, kb.get("file_name", "unknown"), kb.get("metadata", {}).get("tags", []))
        )

        return {
            "success": True,
            "message": "开始解析..."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.get("/knowledge/{kb_id}/progress")
async def get_knowledge_progress(kb_id: str):
    """获取知识库解析进度"""
    try:
        mongodb = get_mongodb_service()
        kb = mongodb.get_knowledge(kb_id)
        if kb and kb.get("_progress"):
            return {"success": True, "progress": kb.get("_progress")}
        return {"success": True, "progress": None}
    except Exception as e:
        return {"success": True, "progress": None}


@router.get("/knowledge/{kb_id}/content")
async def get_knowledge_content(kb_id: str):
    """获取知识库文件内容和切片"""
    try:
        mongodb = get_mongodb_service()
        kb = mongodb.get_knowledge(kb_id)

        if not kb:
            raise HTTPException(status_code=404, detail="知识库条目不存在")

        # 获取原始文件（如果有content_text直接返回，否则尝试读取file_id）
        content_text = kb.get("content_text", "")
        chunks = kb.get("chunks", [])

        # 如果没有content_text，尝试从文件提取
        if not content_text:
            try:
                from backend.services.report_service import get_report_service
                report_service = get_report_service()
                file_data = mongodb.get_knowledge_file(kb_id)
                if file_data:
                    content_text, _ = report_service.extract_text(file_data, kb.get("file_name", ""))
            except Exception as e:
                print(f"[ReportAPI] 提取文件内容失败: {e}")

        return {
            "success": True,
            "content": content_text,
            "chunks": chunks,
            "file_name": kb.get("file_name", ""),
            "status": kb.get("status", "unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取内容失败: {str(e)}")


@router.get("/knowledge/{kb_id}/file/preview")
async def preview_knowledge_file(kb_id: str):
    """预览知识库原始文件（浏览器内联显示）"""
    try:
        mongodb = get_mongodb_service()
        kb = mongodb.get_knowledge(kb_id)

        if not kb:
            raise HTTPException(status_code=404, detail="知识库条目不存在")

        file_data = mongodb.get_knowledge_file(kb_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在")

        from fastapi.responses import StreamingResponse
        import io

        filename = kb.get('file_name', 'file')

        # 根据文件类型设置正确的media_type
        if filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.lower().endswith('.docx'):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.lower().endswith('.doc'):
            media_type = "application/msword"
        elif filename.lower().endswith('.txt'):
            media_type = "text/plain; charset=utf-8"
        else:
            media_type = "application/octet-stream"

        # 不设置Content-Disposition，让浏览器内联显示
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=media_type
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览文件失败: {str(e)}")


@router.get("/knowledge/{kb_id}/file")
async def get_knowledge_file(kb_id: str):
    """下载知识库原始文件"""
    try:
        mongodb = get_mongodb_service()
        kb = mongodb.get_knowledge(kb_id)

        if not kb:
            raise HTTPException(status_code=404, detail="知识库条目不存在")

        file_data = mongodb.get_knowledge_file(kb_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在")

        from fastapi.responses import StreamingResponse
        from starlette.datastructures import Headers
        import io
        from urllib.parse import quote

        filename = kb.get('file_name', 'file')

        # 根据文件类型设置正确的media_type
        if filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.lower().endswith('.docx'):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.lower().endswith('.doc'):
            media_type = "application/msword"
        elif filename.lower().endswith('.txt'):
            media_type = "text/plain; charset=utf-8"
        else:
            media_type = "application/octet-stream"

        # 使用RFC 5987格式的filename*进行中文文件名编码
        encoded_filename = quote(filename, safe='')
        disposition = f"attachment; filename*=UTF-8''{encoded_filename}"

        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=media_type,
            headers=Headers({
                "Content-Disposition": disposition,
                "Content-Length": str(len(file_data))
            })
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")


@router.delete("/knowledge/{kb_id}")
async def delete_knowledge(kb_id: str):
    """删除知识库条目"""
    try:
        mongodb = get_mongodb_service()

        # 从Chroma删除
        try:
            from backend.services.chroma_service import get_chroma_service
            chroma = get_chroma_service()
            chroma.delete_by_report_id("knowledge_chunks", kb_id)
        except:
            pass

        success = mongodb.delete_knowledge(kb_id)

        if not success:
            raise HTTPException(status_code=404, detail="知识库条目不存在")

        return {"success": True, "message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/knowledge/search")
async def search_knowledge(query: str = Body(...), top_k: int = Body(5)):
    """检索知识库"""
    try:
        rag_service = get_rag_service()
        results = await rag_service.search_knowledge(query, top_k=top_k)

        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


# ========== LLM综合回答接口 ==========

class SynthesizeReq(BaseModel):
    query: str
    context: str = ""
    references: List[dict] = []
    use_citations: bool = False


@router.post("/knowledge/synthesize")
async def synthesize_answer(req: SynthesizeReq):
    """基于知识库上下文，调用LLM综合回答问题"""
    try:
        rag_service = get_rag_service()
        result = await rag_service.synthesize_answer(
            query=req.query,
            context=req.context,
            references=req.references,
            use_citations=req.use_citations
        )

        if not result.get("success"):
            return {"success": False, "detail": result.get("error", "综合回答失败")}

        return {
            "success": True,
            "answer": result.get("answer"),
            "answer_plain": result.get("answer_plain"),
            "references": result.get("references", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"综合回答失败: {str(e)}")


# ========== AI问答会话接口 ==========

class QASessionReq(BaseModel):
    session_id: str
    title: str
    messages: List[dict]
    updated_at: Optional[str] = None


@router.post("/qa/sessions")
async def save_qa_session(req: QASessionReq):
    """保存或更新AI问答会话"""
    try:
        mongodb = get_mongodb_service()
        mongodb.save_qa_session(req.session_id, req.title, req.messages, req.updated_at)
        return {"success": True, "session_id": req.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存会话失败: {str(e)}")


@router.get("/qa/sessions")
async def list_qa_sessions(skip: int = 0, limit: int = 50):
    """获取会话列表"""
    try:
        mongodb = get_mongodb_service()
        sessions = mongodb.list_qa_sessions(skip=skip, limit=limit)
        return {"success": True, "sessions": sessions, "total": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.get("/qa/sessions/{session_id}")
async def get_qa_session(session_id: str):
    """获取会话详情"""
    try:
        mongodb = get_mongodb_service()
        session = mongodb.get_qa_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"success": True, "session": session}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话失败: {str(e)}")


@router.delete("/qa/sessions/{session_id}")
async def delete_qa_session(session_id: str):
    """删除会话"""
    try:
        mongodb = get_mongodb_service()
        success = mongodb.delete_qa_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


# ========== 股票和行业提取接口 ==========

@router.get("/{report_id}/extract")
async def extract_info(report_id: str):
    """提取报告中的股票和行业信息"""
    try:
        mongodb = get_mongodb_service()
        report = mongodb.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        report_service = get_report_service()

        text = report.get("content_text", "")
        stocks = report_service.extract_stocks_mentioned(text)
        industries = report_service.extract_industries_mentioned(text)

        return {
            "success": True,
            "stocks": stocks,
            "industries": industries
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取失败: {str(e)}")
