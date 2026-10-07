"""
依頁面內容分割 PDF：偵測到分類關鍵字即視為新文件起點，
直到下一個關鍵字前的頁面歸為同一份文件。
例：A1 B123 → A1 一個檔，B23 一個檔
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter

# ---------- 分類規則（依優先順序檢查） ----------

RULES: dict[str, re.Pattern] = {
    "INV": re.compile(r"COMMERCIAL.*", re.IGNORECASE),
    "BL": re.compile(r"BILL\s*OF\s*LADING", re.IGNORECASE),
    "PL": re.compile(r"^H52194", re.IGNORECASE),
}


@dataclass
class Segment:
    doc_type: str
    start_page: int  # 0-indexed
    end_page: int    # inclusive


def detect_page_type(text: str) -> str | None:
    """回傳該頁命中的分類，皆未命中回傳 None（代表延續前一份文件）"""
    if not text:
        return None
    for doc_type, pattern in RULES.items():
        if pattern.search(text):
            return doc_type
    return None


def build_segments(reader: PdfReader) -> list[Segment]:
    """逐頁掃描，依關鍵字出現位置切分文件區段"""
    segments: list[Segment] = []
    current_type: str | None = None
    current_start: int = 0

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""  # None 防護
        detected = detect_page_type(text)

        if detected is not None and detected != current_type:
            # 遇到新關鍵字 → 前一個區段在此頁之前結束
            if current_type is not None:
                segments.append(Segment(current_type, current_start, i - 1))
            elif i > 0:
                # 開頭尚未遇到關鍵字的頁面，歸為 UNKNOWN
                segments.append(Segment("UNKNOWN", 0, i - 1))
            current_type = detected
            current_start = i

    # 收尾：最後一個區段
    if current_type is not None:
        segments.append(Segment(current_type, current_start, len(reader.pages) - 1))
    elif reader.pages:
        # 全文件都沒偵測到任何關鍵字
        segments.append(Segment("UNKNOWN", 0, len(reader.pages) - 1))

    return segments


def split_pdf(src_path: str, dst_dir: str) -> list[Path]:
    src = Path(src_path)
    dst = Path(dst_dir)
    dst.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(src))
    segments = build_segments(reader)

    # 同分類出現多次時，檔名加流水號避免覆蓋（如 INV 出現兩段）
    type_counter: dict[str, int] = {}
    output_files: list[Path] = []

    for seg in segments:
        type_counter[seg.doc_type] = type_counter.get(seg.doc_type, 0) + 1
        suffix = f"_{type_counter[seg.doc_type]}" if type_counter[seg.doc_type] > 1 else ""
        out_name = f"{src.stem}_{seg.doc_type}{suffix}.pdf"
        out_path = dst / out_name

        writer = PdfWriter()
        for page_idx in range(seg.start_page, seg.end_page + 1):
            writer.add_page(reader.pages[page_idx])

        with open(out_path, "wb") as f:
            writer.write(f)

        output_files.append(out_path)
        print(f"{out_name}: page {seg.start_page + 1} ~ {seg.end_page + 1}")

    return output_files


if __name__ == "__main__":
    SRC_PDF = r"C:\Users\FBTWUser\Documents\UiPath\FormXAPI\Tokyo\H52194 DOC.pdf"
    SRC_PDF = Path(r"C:\Users\FBTWUser\Documents\UiPath\FormXAPI\Tokyo\input_pdfs\H52194 DOC.pdf")
    DST_DIR = "./classified_pdfs"

    split_pdf(SRC_PDF, DST_DIR)