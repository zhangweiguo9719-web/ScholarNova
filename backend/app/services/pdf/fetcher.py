"""
PDF 全文获取器

从合法 OA（Open Access）来源获取 PDF 文件。
支持的来源（按优先级）：
1. 直接 PDF 链接（来自数据源适配器）
2. Unpaywall API（通过 DOI 检测 OA 版本）
3. arXiv 直连（预印本）
4. 会议官网直连（NeurIPS/ICLR/ICML/ACL）
5. PubMed Central（生物医学）
"""

import hashlib
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 下载限制
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
DOWNLOAD_TIMEOUT = 30  # 秒

# Unpaywall API 基础 URL
UNPAYWALL_API = "https://api.unpaywall.org/v2"

# arXiv PDF 基础 URL
ARXIV_PDF_BASE = "https://arxiv.org/pdf"

# 已知会议的 PDF 基础 URL
_CONFERENCE_PATTERNS: dict[str, str] = {
    "neurips": "https://proceedings.neurips.cc/paper_files/paper",
    "nips": "https://proceedings.neurips.cc/paper_files/paper",
    "iclr": "https://openreview.net/pdf",
    "icml": "https://proceedings.mlr.press",
    "acl": "https://aclanthology.org",
    "emnlp": "https://aclanthology.org",
    "naacl": "https://aclanthology.org",
    "aaai": "https://ojs.aaai.org/index.php/AAAI/article/view",
}

# PubMed Central PDF 基础 URL
PMC_PDF_BASE = "https://www.ncbi.nlm.nih.gov/pmc/articles"


@dataclass
class FetchResult:
    """PDF 获取结果"""

    success: bool
    pdf_path: Optional[Path] = None
    source: str = ""  # 获取来源（如 "direct", "unpaywall", "arxiv"）
    url: str = ""
    error: str = ""
    file_size: int = 0


class PDFFetcher:
    """
    PDF 全文获取器

    从合法 OA 来源获取 PDF 文件，支持缓存。
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        unpaywall_email: Optional[str] = None,
    ):
        """
        初始化获取器。

        Args:
            cache_dir: PDF 缓存目录。为 None 时使用系统临时目录。
            unpaywall_email: Unpaywall API 邮箱（推荐提供以获得更高速率）。
        """
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "scholar_pdf_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.unpaywall_email = unpaywall_email

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def fetch(
        self,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        pdf_url: Optional[str] = None,
        venue: Optional[str] = None,
        title: Optional[str] = None,
    ) -> FetchResult:
        """
        获取 PDF 文件。按优先级尝试多种来源。

        Args:
            doi: 论文 DOI
            arxiv_id: arXiv ID（如 "2301.12345"）
            pdf_url: 直接 PDF 链接
            venue: 发表场所（用于会议官网直连）
            title: 论文标题（用于缓存键生成）

        Returns:
            FetchResult
        """
        # 检查缓存
        cache_key = self._make_cache_key(doi or arxiv_id or pdf_url or title or "")
        cached = self._check_cache(cache_key)
        if cached:
            logger.info(f"PDF cache hit: {cache_key}")
            return FetchResult(
                success=True,
                pdf_path=cached,
                source="cache",
                file_size=cached.stat().st_size,
            )

        # 1. 直接 PDF 链接
        if pdf_url:
            result = await self._download_pdf(pdf_url, "direct", cache_key)
            if result.success:
                return result

        # 2. Unpaywall API
        if doi:
            result = await self._fetch_from_unpaywall(doi, cache_key)
            if result.success:
                return result

        # 3. arXiv 直连
        if arxiv_id:
            result = await self._fetch_from_arxiv(arxiv_id, cache_key)
            if result.success:
                return result

        # 4. 会议官网直连
        if venue and doi:
            result = await self._fetch_from_conference(venue, doi, cache_key)
            if result.success:
                return result

        # 5. PubMed Central
        if doi:
            result = await self._fetch_from_pmc(doi, cache_key)
            if result.success:
                return result

        logger.warning(
            f"Failed to fetch PDF from any source: doi={doi}, arxiv_id={arxiv_id}"
        )
        return FetchResult(
            success=False,
            error="No OA version found from any source",
        )

    async def fetch_batch(
        self,
        papers: list[dict],
        max_concurrent: int = 5,
    ) -> list[FetchResult]:
        """
        批量获取 PDF。

        Args:
            papers: 论文信息列表，每个元素包含 doi、arxiv_id、pdf_url 等字段
            max_concurrent: 最大并发数

        Returns:
            FetchResult 列表
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _fetch_one(paper: dict) -> FetchResult:
            async with semaphore:
                return await self.fetch(
                    doi=paper.get("doi"),
                    arxiv_id=paper.get("arxiv_id"),
                    pdf_url=paper.get("pdf_url"),
                    venue=paper.get("venue"),
                    title=paper.get("title"),
                )

        tasks = [_fetch_one(p) for p in papers]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # 来源1：直接下载
    # ------------------------------------------------------------------

    async def _download_pdf(
        self, url: str, source: str, cache_key: str
    ) -> FetchResult:
        """
        从 URL 下载 PDF。

        Args:
            url: PDF URL
            source: 来源标识
            cache_key: 缓存键

        Returns:
            FetchResult
        """
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=DOWNLOAD_TIMEOUT
            ) as client:
                # 先检查 Content-Type
                head_resp = await client.head(url)
                content_type = head_resp.headers.get("content-type", "")

                # 如果 HEAD 请求返回了明确的非 PDF 类型，跳过
                if content_type and "pdf" not in content_type.lower():
                    # 但允许 application/octet-stream（某些服务器通用类型）
                    if "octet-stream" not in content_type.lower():
                        logger.debug(
                            f"Skipping {url}: Content-Type={content_type}"
                        )
                        return FetchResult(
                            success=False,
                            source=source,
                            url=url,
                            error=f"Not a PDF: Content-Type={content_type}",
                        )

                # 下载
                resp = await client.get(url)
                resp.raise_for_status()

                # 检查内容是否为 PDF
                if not self._is_pdf_content(resp.content):
                    return FetchResult(
                        success=False,
                        source=source,
                        url=url,
                        error="Downloaded content is not a valid PDF",
                    )

                # 检查文件大小
                if len(resp.content) > MAX_FILE_SIZE:
                    return FetchResult(
                        success=False,
                        source=source,
                        url=url,
                        error=f"File too large: {len(resp.content)} bytes",
                    )

                # 保存到缓存
                pdf_path = self._save_to_cache(cache_key, resp.content)
                logger.info(
                    f"Downloaded PDF from {source}: {url} -> {pdf_path}"
                )
                return FetchResult(
                    success=True,
                    pdf_path=pdf_path,
                    source=source,
                    url=url,
                    file_size=len(resp.content),
                )

        except httpx.TimeoutException:
            logger.warning(f"Timeout downloading PDF from {url}")
            return FetchResult(
                success=False, source=source, url=url, error="Download timeout"
            )
        except Exception as e:
            logger.warning(f"Error downloading PDF from {url}: {e}")
            return FetchResult(
                success=False, source=source, url=url, error=str(e)
            )

    # ------------------------------------------------------------------
    # 来源2：Unpaywall
    # ------------------------------------------------------------------

    async def _fetch_from_unpaywall(
        self, doi: str, cache_key: str
    ) -> FetchResult:
        """
        通过 Unpaywall API 获取 OA 版本 PDF。

        Args:
            doi: 论文 DOI
            cache_key: 缓存键

        Returns:
            FetchResult
        """
        url = f"{UNPAYWALL_API}/{doi}"
        params = {}
        if self.unpaywall_email:
            params["email"] = self.unpaywall_email

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 404:
                    return FetchResult(
                        success=False,
                        source="unpaywall",
                        error=f"DOI not found in Unpaywall: {doi}",
                    )
                resp.raise_for_status()
                data = resp.json()

                # 查找最佳 OA 位置
                best_oa = data.get("best_oa_location")
                if best_oa and best_oa.get("url_for_pdf"):
                    pdf_url = best_oa["url_for_pdf"]
                    return await self._download_pdf(
                        pdf_url, "unpaywall", cache_key
                    )

                # 遍历所有 OA 位置
                for location in data.get("oa_locations", []):
                    pdf_url = location.get("url_for_pdf")
                    if pdf_url:
                        result = await self._download_pdf(
                            pdf_url, "unpaywall", cache_key
                        )
                        if result.success:
                            return result

                return FetchResult(
                    success=False,
                    source="unpaywall",
                    error=f"No OA PDF found for DOI: {doi}",
                )

        except Exception as e:
            logger.warning(f"Unpaywall lookup failed for {doi}: {e}")
            return FetchResult(
                success=False, source="unpaywall", error=str(e)
            )

    # ------------------------------------------------------------------
    # 来源3：arXiv
    # ------------------------------------------------------------------

    async def _fetch_from_arxiv(
        self, arxiv_id: str, cache_key: str
    ) -> FetchResult:
        """
        从 arXiv 直接下载 PDF。

        Args:
            arxiv_id: arXiv ID（如 "2301.12345" 或 "2301.12345v2"）
            cache_key: 缓存键

        Returns:
            FetchResult
        """
        # 清理 arxiv_id（移除版本号用于 PDF URL）
        clean_id = arxiv_id.strip()
        # 移除可能的前缀
        for prefix in ["arxiv:", "arXiv:"]:
            if clean_id.lower().startswith(prefix.lower()):
                clean_id = clean_id[len(prefix) :]

        url = f"{ARXIV_PDF_BASE}/{clean_id}"
        return await self._download_pdf(url, "arxiv", cache_key)

    # ------------------------------------------------------------------
    # 来源4：会议官网
    # ------------------------------------------------------------------

    async def _fetch_from_conference(
        self, venue: str, doi: str, cache_key: str
    ) -> FetchResult:
        """
        从会议官网获取 PDF。

        Args:
            venue: 发表场所
            doi: 论文 DOI
            cache_key: 缓存键

        Returns:
            FetchResult
        """
        venue_lower = venue.lower()
        for conf_key, base_url in _CONFERENCE_PATTERNS.items():
            if conf_key in venue_lower:
                # 尝试构造 PDF URL
                # 这些 URL 模式因会议而异，这里尝试常见模式
                possible_urls = self._guess_conference_pdf_urls(
                    conf_key, base_url, doi
                )
                for url in possible_urls:
                    result = await self._download_pdf(
                        url, f"conference:{conf_key}", cache_key
                    )
                    if result.success:
                        return result

        return FetchResult(
            success=False,
            source="conference",
            error=f"No conference PDF pattern matched for venue: {venue}",
        )

    def _guess_conference_pdf_urls(
        self, conf_key: str, base_url: str, doi: str
    ) -> list[str]:
        """
        根据会议类型猜测可能的 PDF URL。

        Returns:
            可能的 URL 列表
        """
        urls: list[str] = []

        if conf_key in ("neurips", "nips"):
            # NeurIPS: https://proceedings.neurips.cc/paper_files/paper/2023/hash/xxx-Paper-Conference.pdf
            # 难以直接构造，跳过
            pass
        elif conf_key == "iclr":
            # ICLR 使用 OpenReview，需要 paper ID
            pass
        elif conf_key in ("acl", "emnlp", "naacl"):
            # ACL Anthology: https://aclanthology.org/2023.acl-long.123.pdf
            # 从 DOI 提取 anthology ID
            pass

        return urls

    # ------------------------------------------------------------------
    # 来源5：PubMed Central
    # ------------------------------------------------------------------

    async def _fetch_from_pmc(self, doi: str, cache_key: str) -> FetchResult:
        """
        从 PubMed Central 获取 PDF。

        Args:
            doi: 论文 DOI
            cache_key: 缓存键

        Returns:
            FetchResult
        """
        # 通过 NCBI ID converter API 查找 PMC ID
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # 使用 ID 转换 API
                resp = await client.get(
                    "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/",
                    params={"ids": doi, "format": "json"},
                )
                if resp.status_code != 200:
                    return FetchResult(
                        success=False,
                        source="pmc",
                        error=f"NCBI ID converter returned {resp.status_code}",
                    )

                data = resp.json()
                records = data.get("records", [])
                if not records:
                    return FetchResult(
                        success=False,
                        source="pmc",
                        error=f"No PMC record found for DOI: {doi}",
                    )

                pmcid = records[0].get("pmcid")
                if not pmcid:
                    return FetchResult(
                        success=False,
                        source="pmc",
                        error=f"No PMC ID for DOI: {doi}",
                    )

                # 构造 PMC PDF URL
                pmc_id_num = pmcid.replace("PMC", "")
                pdf_url = f"{PMC_PDF_BASE}/{pmcid}/pdf/"
                return await self._download_pdf(pdf_url, "pmc", cache_key)

        except Exception as e:
            logger.warning(f"PMC lookup failed for {doi}: {e}")
            return FetchResult(
                success=False, source="pmc", error=str(e)
            )

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _is_pdf_content(content: bytes) -> bool:
        """检查内容是否为有效的 PDF 文件。"""
        # PDF 文件以 %PDF 开头
        return content[:5] == b"%PDF-"

    @staticmethod
    def _make_cache_key(identifier: str) -> str:
        """生成缓存键。"""
        return hashlib.md5(identifier.encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> Optional[Path]:
        """检查缓存中是否存在。"""
        cache_path = self.cache_dir / f"{cache_key}.pdf"
        if cache_path.exists():
            return cache_path
        return None

    def _save_to_cache(self, cache_key: str, content: bytes) -> Path:
        """保存到缓存。"""
        cache_path = self.cache_dir / f"{cache_key}.pdf"
        cache_path.write_bytes(content)
        return cache_path

    def clear_cache(self) -> int:
        """
        清理缓存。

        Returns:
            删除的文件数
        """
        count = 0
        for pdf_file in self.cache_dir.glob("*.pdf"):
            pdf_file.unlink(missing_ok=True)
            count += 1
        return count
