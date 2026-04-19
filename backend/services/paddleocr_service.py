"""
PaddleOCR 服务 - 图片PDF文字识别
"""
import os
import json
import time
import requests
from typing import Optional

class PaddleOCRService:
    """PaddleOCR服务类"""

    def __init__(self, token: str = None, api_url: str = None, model: str = None):
        self.token = token or os.getenv("PADDLEOCR_TOKEN")
        self.api_url = api_url or os.getenv("PADDLEOCR_API_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs")
        self.model = model or os.getenv("PADDLEOCR_MODEL", "PaddleOCR-VL-1.5")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
        }
        # 确保token小写（API要求）
        self.headers["Authorization"] = f"bearer {self.token}"

    def extract_text_from_pdf(self, file_data: bytes, filename: str = "document.pdf") -> tuple:
        """
        使用PaddleOCR从PDF提取文本（适合图片型PDF）

        Args:
            file_data: PDF二进制数据
            filename: 文件名

        Returns:
            (完整文本, 每页文本列表)
        """
        import urllib3
        urllib3.disable_warnings()

        try:
            # 1. 提交OCR任务
            data = {
                "model": self.model,
                "optionalPayload": json.dumps({
                    "useDocOrientationClassify": False,
                    "useDocUnwarping": False,
                    "useChartRecognition": False
                })
            }

            files = {"file": (filename, file_data, "application/pdf")}

            # 使用代理（如果有设置）
            proxies = {}
            if os.getenv("HTTP_PROXY"):
                proxies["http"] = os.getenv("HTTP_PROXY")
            if os.getenv("HTTPS_PROXY"):
                proxies["https"] = os.getenv("HTTPS_PROXY")

            print(f"[PaddleOCR] 正在提交任务到 {self.api_url}...")
            job_response = requests.post(
                self.api_url,
                headers=self.headers,
                data=data,
                files=files,
                timeout=120,
                proxies=proxies if proxies else None,
                verify=False
            )

            if job_response.status_code != 200:
                print(f"[PaddleOCR] 提交任务失败: {job_response.status_code}, {job_response.text}")
                return "", []

            job_id = job_response.json()["data"]["jobId"]
            print(f"[PaddleOCR] 任务已提交, job_id: {job_id}")

            # 2. 轮询等待结果
            jsonl_url = ""
            max_retries = 120  # 最多等待10分钟
            retry_count = 0

            while retry_count < max_retries:
                job_result_response = requests.get(
                    f"{self.api_url}/{job_id}",
                    headers=self.headers,
                    timeout=30,
                    proxies=proxies if proxies else None,
                    verify=False
                )

                if job_result_response.status_code != 200:
                    retry_count += 1
                    time.sleep(5)
                    continue

                state = job_result_response.json()["data"]["state"]

                if state == "pending":
                    print("[PaddleOCR] 任务等待中...")
                elif state == "running":
                    try:
                        total_pages = job_result_response.json()["data"]["extractProgress"]["totalPages"]
                        extracted_pages = job_result_response.json()["data"]["extractProgress"]["extractedPages"]
                        print(f"[PaddleOCR] 处理中... 总页数: {total_pages}, 已提取: {extracted_pages}")
                    except KeyError:
                        print("[PaddleOCR] 处理中...")
                elif state == "done":
                    extracted_pages = job_result_response.json()["data"]["extractProgress"]["extractedPages"]
                    start_time = job_result_response.json()["data"]["extractProgress"]["startTime"]
                    end_time = job_result_response.json()["data"]["extractProgress"]["endTime"]
                    try:
                        elapsed_ms = int(end_time) - int(start_time)
                        print(f"[PaddleOCR] 完成, 提取页数: {extracted_pages}, 耗时: {elapsed_ms}ms")
                    except (ValueError, TypeError):
                        print(f"[PaddleOCR] 完成, 提取页数: {extracted_pages}")
                    jsonl_url = job_result_response.json()["data"]["resultUrl"]["jsonUrl"]
                    break
                elif state == "failed":
                    error_msg = job_result_response.json()["data"]["errorMsg"]
                    print(f"[PaddleOCR] 任务失败: {error_msg}")
                    return "", []

                time.sleep(5)
                retry_count += 1

            if not jsonl_url:
                print("[PaddleOCR] 等待超时")
                return "", []

            # 3. 获取结果
            jsonl_response = requests.get(
                jsonl_url,
                timeout=60,
                proxies=proxies if proxies else None,
                verify=False
            )
            jsonl_response.raise_for_status()

            lines = jsonl_response.text.strip().split("\n")

            full_text = []
            pages_text = []

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    result = json.loads(line)["result"]
                    for res in result.get("layoutParsingResults", []):
                        md_text = res["markdown"]["text"]
                        if md_text.strip():
                            full_text.append(md_text)
                            pages_text.append({
                                "page": line_num,
                                "text": md_text.strip()
                            })
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[PaddleOCR] 解析第{line_num}行失败: {e}")
                    continue

            return "\n\n".join(full_text), pages_text

        except Exception as e:
            print(f"[PaddleOCR] 提取失败: {e}")
            return "", []


# 单例模式全局实例
_paddleocr_service: Optional[PaddleOCRService] = None

def get_paddleocr_service() -> PaddleOCRService:
    """获取PaddleOCR服务单例"""
    global _paddleocr_service
    if _paddleocr_service is None:
        _paddleocr_service = PaddleOCRService()
    return _paddleocr_service
