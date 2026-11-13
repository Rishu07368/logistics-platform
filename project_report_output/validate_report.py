#!/usr/bin/env python
"""Validate Meridian report structure, identifiers, captions, images and pagination."""
from __future__ import annotations

import json
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import pymupdf
from docx import Document
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
STEM = "Meridian_Logistics_Platform_Project_Report_Rishabh_Singh_25BCS11466"
PDF = ROOT / f"{STEM}.pdf"
DOCX = ROOT / f"{STEM}.docx"
QC = ROOT / "quality_control" / STEM
FIGURE_RE = re.compile(r"^!\[(Figure\s+([A-Za-z0-9.]+):\s*.+?)\]\((.+?)\)$")
TABLE_RE = re.compile(r"^\*\*Table\s+([A-Za-z0-9.]+)\s*[–-]\s*(.+?)\*\*$")
REQUIRED = [
    "Bonafide Certificate", "Table of Contents", "List of Figures",
    "List of Tables", "List of Standards", "Abstract", "Graphical Abstract",
    "Abbreviations", "Symbols",
    "CHAPTER 1. INTRODUCTION", "1.1 Identification of Client", "1.2 Identification of Problem",
    "1.3 Identification of Tasks", "1.4 Timeline", "1.5 Organization of the Report",
    "CHAPTER 2. LITERATURE REVIEW", "2.1 Timeline of the Reported Problem",
    "2.2 Existing Solutions", "2.3 Bibliometric Analysis", "2.4 Review Summary",
    "2.5 Problem Definition", "2.6 Goals / Objectives",
    "CHAPTER 3. DESIGN FLOW", "3.1 Evaluation and Selection", "3.2 Design Constraints",
    "3.3 Analysis of Features", "3.4 Design Flow", "3.5 Design Selection",
    "3.6 Implementation Plan",
    "CHAPTER 4. RESULTS ANALYSIS AND VALIDATION", "4.1 Implementation of Solution",
    "4.1.1 Overall System Architecture", "4.1.2 Flask Application and API Layer",
    "4.1.3 Graph Construction and Representation", "4.1.4 Database and Data Handling",
    "4.1.5 Dijkstra's Binary-Heap Implementation", "4.1.6 Array-Based Dijkstra Implementation",
    "4.1.7 Bellman–Ford Implementation", "4.1.8 Algorithm Dispatch and Route Reconstruction",
    "4.1.9 Network Manager", "4.1.10 Route Optimizer", "4.1.11 Comparison Lab",
    "4.1.12 Scaling Benchmark", "4.1.13 Analytics Dashboard",
    "4.1.14 User Interface and Application Workflow", "4.1.15 Testing and Validation",
    "4.1.16 Results and Discussion",
    "CHAPTER 5. CONCLUSION AND FUTURE WORK", "5.1 Conclusion", "5.2 Future Work",
    "REFERENCES", "APPENDIX", "USER MANUAL",
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace("–", "-").replace("−", "-").casefold()


def _render_contact_sheet(pdf: pymupdf.Document) -> None:
    QC.mkdir(parents=True, exist_ok=True)
    thumbs = []
    for index, page in enumerate(pdf):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        image.thumbnail((220, 300))
        tile = Image.new("RGB", (230, 325), "white")
        tile.paste(image, ((230 - image.width) // 2, 18))
        ImageDraw.Draw(tile).text((7, 2), f"Page {index + 1}", fill="black")
        tile.save(QC / f"page_{index + 1:02d}.png")
        thumbs.append(tile)
    columns = 5
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 230, rows * 325), (225, 230, 235))
    for index, tile in enumerate(thumbs):
        sheet.paste(tile, ((index % columns) * 230, (index // columns) * 325))
    sheet.save(QC / "final_contact_sheet.jpg", quality=92)


def validate(student_name: str, student_uid: str, student_class: str) -> dict:
    errors = []
    if not PDF.is_file() or not DOCX.is_file():
        raise FileNotFoundError("Both final PDF and editable DOCX must exist before validation.")
    docx = Document(DOCX)
    if len(docx.paragraphs) < 70 or len(docx.tables) < 10:
        errors.append("DOCX content is unexpectedly sparse.")
    pdf = pymupdf.open(PDF)
    pages = len(pdf)
    if pages > 24:
        errors.append(f"PDF page count is {pages}; expected no more than 24.")
    all_text = "\n".join(page.get_text() for page in pdf)
    normalized = _norm(all_text)
    for heading in REQUIRED:
        if _norm(heading) not in normalized:
            errors.append(f"Required heading/text not found: {heading}")
    for value in (student_name, student_uid, student_class,
                  "Advanced Data Structure", "25CSH-202", "3rd Semester",
                  "Bachelor of Engineering", "Computer Science Engineering",
                  "Chandigarh University",
                  "GRAPH-BASED LOGISTICS NETWORK AND ROUTE OPTIMIZATION PLATFORM"):
        if _norm(value) not in normalized:
            errors.append(f"Required student/academic detail missing: {value}")
    for forbidden in ("John Doe", "Jane Doe", "To be generated", "PAGEREF"):
        if forbidden.casefold() in all_text.casefold():
            errors.append(f"Unresolved sample/field content found: {forbidden}")
    if "Error! Bookmark not defined." in all_text:
        errors.append("A dynamic cross-reference bookmark did not resolve.")
    chapter_numbers = set(re.findall(r"CHAPTER\s+(\d+)\s*\.", all_text, re.IGNORECASE))
    if chapter_numbers != {"1", "2", "3", "4", "5"}:
        errors.append(f"Main chapter set is {sorted(chapter_numbers)} rather than exactly 1–5.")
    page_text = [page.get_text() for page in pdf]
    for index, text in enumerate(page_text[1:], start=2):
        if f"Page {index}" not in text:
            errors.append(f"Page-number footer missing or incorrect on page {index}.")
    image_count = sum(len(page.get_images(full=True)) for page in pdf)
    if image_count < 14:
        errors.append(f"Only {image_count} embedded images found; expected diagrams and UI evidence.")
    layout_errors = []
    for index, page in enumerate(pdf, start=1):
        rect = page.rect
        for block in page.get_text("blocks"):
            x0, y0, x1, y1 = block[:4]
            if x0 < -1 or y0 < -1 or x1 > rect.width + 1 or y1 > rect.height + 1:
                layout_errors.append(f"Text block outside page {index} bounds.")
                break
    errors.extend(layout_errors)

    caption_counts = {"figure": 0, "table": 0}
    for md in sorted(CONTENT.glob("*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            figure = FIGURE_RE.fullmatch(line.strip())
            table = TABLE_RE.fullmatch(line.strip())
            if figure:
                caption_counts["figure"] += 1
                image_path = (md.parent / figure.group(3)).resolve()
                if not image_path.is_file():
                    errors.append(f"Missing figure asset: {image_path}")
                if figure.group(1).split(":", 1)[0].casefold() not in normalized:
                    errors.append(f"Figure caption not found in PDF: {figure.group(1)}")
            if table:
                caption_counts["table"] += 1
                if f"Table {table.group(1)}".casefold() not in all_text.casefold():
                    errors.append(f"Table caption not found in PDF: Table {table.group(1)}")
    if all(not (ASSETS / folder).exists() for folder in ("diagrams", "charts", "screenshots")):
        errors.append("Report asset directories are missing.")
    _render_contact_sheet(pdf)
    summary = {
        "validated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pdf": str(PDF),
        "docx": str(DOCX),
        "pdf_pages": pages,
        "main_chapters": sorted(map(int, chapter_numbers)),
        "embedded_images": image_count,
        "figure_captions": caption_counts["figure"],
        "table_captions": caption_counts["table"],
        "docx_tables": len(docx.tables),
        "document_bytes": {"pdf": PDF.stat().st_size, "docx": DOCX.stat().st_size},
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
    }
    (ROOT / f"validation_record_{STEM}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    for key, value in summary.items():
        if key != "errors":
            print(f"{key}: {value}")
    if errors:
        print("VALIDATION ERRORS:")
        for error in errors:
            print(f"- {error}")
    else:
        print("VALIDATION: PASS")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", default="Rishabh Singh")
    parser.add_argument("--uid", default="25BCS11466")
    parser.add_argument("--class", dest="student_class", default="25BCS-707-A")
    parser.add_argument("--stem", default=STEM)
    args = parser.parse_args()
    STEM = args.stem
    PDF = ROOT / f"{STEM}.pdf"
    DOCX = ROOT / f"{STEM}.docx"
    QC = ROOT / "quality_control" / STEM
    result = validate(args.student, args.uid, args.student_class)
    sys.exit(0 if result["result"] == "PASS" else 1)
