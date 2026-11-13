#!/usr/bin/env python
"""Generate Meridian's editable Word report, dynamic indexes, diagrams and PDF.

Run from this directory with its isolated Python environment. The local demo
must be available at http://127.0.0.1:5010/ to refresh the genuine UI captures.
"""
from __future__ import annotations

import argparse
import base64
from io import BytesIO
import re
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image


ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
BRANDING = ASSETS / "branding"
DIAGRAMS = ASSETS / "diagrams"
CHARTS = ASSETS / "charts"
SCREENSHOTS = ASSETS / "screenshots"
REPORT_STEM = "Meridian_Logistics_Platform_Project_Report_Rishabh_Singh_25BCS11466"
DOCX_PATH = ROOT / f"{REPORT_STEM}.docx"
PDF_PATH = ROOT / f"{REPORT_STEM}.pdf"
STUDENT_NAME = "Rishabh Singh"
STUDENT_UID = "25BCS11466"
STUDENT_CLASS = "25BCS-707-A"
BLUE = "#163b5b"
BLUE2 = "#2d6d97"
CYAN = "#5ba2bb"
GOLD = "#d99132"
PALE = "#edf3f7"
GREY = "#5e6c77"
TABLE_RE = re.compile(r"^\*\*Table\s+([A-Za-z0-9.]+)\s*[–-]\s*(.+?)\*\*$")
FIGURE_RE = re.compile(r"^!\[(Figure\s+([A-Za-z0-9.]+):\s*.+?)\]\((.+?)\)$")
PAGE_REF_RE = re.compile(r"\{\{PAGEREF:([A-Za-z0-9_]+)\}\}")
STANDARD_BOOKMARKS = {
    "std_json": "4.1.2 Flask Application and API Layer",
    "std_quality": "3.1 Evaluation and Selection of Specifications / Features",
}
PAGE_BREAK_TITLES = {
    "Bonafide Certificate",
    "Table of Contents",
    "Graphical Abstract",
    "Abbreviations",
    "Symbols",
    "CHAPTER 1. INTRODUCTION",
    "CHAPTER 2. LITERATURE REVIEW / BACKGROUND STUDY",
    "CHAPTER 3. DESIGN FLOW / PROCESS",
    "CHAPTER 4. RESULTS ANALYSIS AND VALIDATION",
    "CHAPTER 5. CONCLUSION AND FUTURE WORK",
    "REFERENCES",
    "APPENDIX",
    "USER MANUAL",
}


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _box(ax, xy, width, height, text, face=PALE, edge=BLUE, fontsize=9, weight="normal"):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), width, height, boxstyle="round,pad=0.025,rounding_size=0.04",
        facecolor=face, edgecolor=edge, linewidth=1.2,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center",
            fontsize=fontsize, color=BLUE, weight=weight, wrap=True)


def _arrow(ax, start, end, color=BLUE2, style="-|>", width=1.5, connection="arc3"):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=11,
                                 linewidth=width, color=color, connectionstyle=connection))


def create_diagrams() -> None:
    for folder in (BRANDING, DIAGRAMS, CHARTS, SCREENSHOTS):
        folder.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 2.8))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 2.4)
    ax.axis("off")
    labels = [
        ("Logistics need", "Facilities and\ntransport links"),
        ("Graph model", "Directed vertices,\nweighted edges"),
        ("Algorithms", "Heap / array\nDijkstra; Bellman–Ford"),
        ("Route result", "Metric-specific path\nand hop totals"),
        ("Evaluation", "Connectivity, tests\nand benchmarks"),
    ]
    xs = [0.2, 2.38, 4.56, 6.74, 8.92]
    for i, (title, body) in enumerate(labels):
        _box(ax, (xs[i], 0.62), 1.85, 1.12, f"{title}\n{body}", face="#f4f8fa",
             edge=BLUE2, fontsize=8.5, weight="bold")
        if i < len(xs) - 1:
            _arrow(ax, (xs[i] + 1.88, 1.18), (xs[i + 1] - 0.06, 1.18), color=GOLD)
    ax.text(5.5, 2.08, "MERIDIAN • GRAPH-BASED ROUTE OPTIMIZATION",
            ha="center", va="center", fontsize=12, weight="bold", color=BLUE)
    _save(fig, DIAGRAMS / "graphical_abstract.png")

    fig, ax = plt.subplots(figsize=(8, 2.6))
    phases = [
        ("Problem & model", 0.0, 1.0, BLUE),
        ("Algorithms & data", 1.0, 1.0, BLUE2),
        ("Application", 2.0, 1.0, CYAN),
        ("Validation & report", 3.0, 1.0, GOLD),
    ]
    for i, (label, start, duration, color) in enumerate(phases):
        ax.barh(i, duration, left=start, height=0.46, color=color, alpha=0.9)
        ax.text(start + duration / 2, i, label, ha="center", va="center",
                color="white", fontsize=8, weight="bold")
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_xlim(-0.15, 4.15)
    ax.set_ylim(-0.6, 3.6)
    ax.set_title("Indicative phase sequence (no project dates asserted)", color=BLUE, fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", color="#dce5eb", linewidth=0.6)
    _save(fig, DIAGRAMS / "project_timeline.png")

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    _box(ax, (3.8, 5.0), 2.4, 0.62, "Browser UI\nHTML • CSS • JavaScript", face="#e9f2f8", fontsize=9, weight="bold")
    _box(ax, (3.8, 3.95), 2.4, 0.62, "Flask API\nroutes / JSON / errors", face="#e9f2f8", fontsize=9, weight="bold")
    _box(ax, (3.8, 2.9), 2.4, 0.62, "Services\nrouting • analytics • network", face="#e9f2f8", fontsize=9, weight="bold")
    _box(ax, (0.5, 1.45), 2.5, 0.78, "Graph algorithms\nheap / array Dijkstra\nBellman–Ford • analysis", face="#f7f5eb", edge=GOLD, fontsize=8.5)
    _box(ax, (3.75, 1.45), 2.5, 0.78, "Repository layer\nparameterized SQL\nnetwork / location / route", face="#edf6f1", edge="#42846a", fontsize=8.5)
    _box(ax, (7.0, 1.45), 2.5, 0.78, "SQLite\nnetworks • locations\nroutes • runs", face="#f7f5eb", edge=GOLD, fontsize=8.5)
    for y0, y1 in ((5.0, 4.58), (3.95, 3.53), (2.9, 2.27)):
        _arrow(ax, (5, y0), (5, y1))
    _arrow(ax, (3.8, 3.0), (2.8, 2.25), connection="arc3,rad=0.04")
    _arrow(ax, (5.0, 2.9), (5.0, 2.25))
    _arrow(ax, (6.2, 1.84), (6.95, 1.84))
    _arrow(ax, (7.0, 1.55), (6.25, 1.55), color=GOLD)
    ax.text(5, 0.68, "Layering keeps HTTP, persistence, algorithm logic and presentation distinct.",
            ha="center", fontsize=9, color=GREY)
    ax.set_title("Layered application architecture", color=BLUE, fontsize=12, weight="bold")
    _save(fig, DIAGRAMS / "system_architecture.png")

    fig, axes = plt.subplots(1, 3, figsize=(11, 4.1))
    panels = [
        ("Heap Dijkstra", ["Initialize d, pred", "Push source", "Pop min; skip stale", "Relax outgoing edges", "Queue empty → paths"]),
        ("Array Dijkstra", ["Initialize d, pred", "Scan remaining min", "Stop if min = ∞", "Relax outgoing edges", "Repeat until settled"]),
        ("Bellman–Ford", ["Initialize d, pred", "Repeat edge scans ≤ V−1", "Stop if no change", "Extra scan for cycle", "Reconstruct / mark affected"]),
    ]
    for ax, (title, steps) in zip(axes, panels):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title(title, fontsize=10, color=BLUE, weight="bold", pad=8)
        ys = [0.82, 0.65, 0.48, 0.31, 0.14]
        for i, (y, label) in enumerate(zip(ys, steps)):
            _box(ax, (0.08, y - 0.055), 0.84, 0.11, label, face="#f1f6f9", fontsize=7.6)
            if i < len(ys) - 1:
                _arrow(ax, (0.5, y - 0.065), (0.5, ys[i + 1] + 0.065), width=0.9)
    fig.suptitle("Algorithm control flow and relaxation", fontsize=12, color=BLUE, weight="bold")
    _save(fig, DIAGRAMS / "algorithm_flow.png")

    fig, ax = plt.subplots(figsize=(9, 2.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    xs = [0.25, 2.25, 4.25, 6.25, 8.25]
    boxes = ["UI request\nsource, target,\nmetric", "Flask API\nvalidate JSON\nand IDs", "Graph service\nload vertices +\nweighted edges", "Algorithm\ndistances +\npredecessors", "Result JSON\npath, totals,\nstatus, counters"]
    for i, (x, text) in enumerate(zip(xs, boxes)):
        _box(ax, (x, 1.0), 1.5, 1.0, text, face="#edf4f8", fontsize=8, weight="bold")
        if i < 4:
            _arrow(ax, (x + 1.52, 1.5), (xs[i + 1] - 0.05, 1.5), color=GOLD)
    _box(ax, (3.5, 0.04), 3.0, 0.55, "SQLite repository: networks, locations, routes, runs", face="#f4f4ec", edge=GOLD, fontsize=8)
    _arrow(ax, (5, 1.0), (5, 0.62), color="#42846a", style="<->", width=1.3)
    ax.text(5, 2.55, "Route calculation and presentation data flow", ha="center",
            fontsize=12, color=BLUE, weight="bold")
    _save(fig, DIAGRAMS / "data_flow.png")

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), gridspec_kw={"width_ratios": [1.2, 1.05, 1.0]})
    ax = axes[0]
    coords = {"CAI": (0.12, 0.5), "MIL": (0.38, 0.78), "FRA": (0.62, 0.78), "HAM": (0.84, 0.6)}
    for name, (x, y) in coords.items():
        ax.add_patch(Circle((x, y), 0.065, facecolor="#e8f1f6", edgecolor=BLUE2, lw=1.1))
        ax.text(x, y, name, ha="center", va="center", fontsize=7, weight="bold", color=BLUE)
    for a, b, label in [
        ("CAI", "MIL", "sea • 2070"), ("MIL", "FRA", "rail • 934"),
        ("FRA", "HAM", "rail • 769"),
    ]:
        _arrow(ax, coords[a], coords[b], width=1.0)
        mx = (coords[a][0] + coords[b][0]) / 2
        my = (coords[a][1] + coords[b][1]) / 2 + 0.1
        ax.text(mx, my, label, fontsize=6.2, ha="center", color=GREY)
    ax.set_xlim(0, 1)
    ax.set_ylim(0.25, 1)
    ax.axis("off")
    ax.set_title("Directed weighted subgraph", fontsize=8, color=BLUE)
    axes[1].axis("off")
    axes[1].set_title("Adjacency-list view", fontsize=8, color=BLUE)
    axes[1].text(0.02, 0.75, "CAI: [(MIL, 2070)]\nMIL: [(FRA, 934)]\nFRA: [(HAM, 769)]\nHAM: […]",
                 family="monospace", fontsize=7.4, va="top", color=BLUE)
    axes[2].axis("off")
    axes[2].set_title("Matrix view (theoretical)", fontsize=8, color=BLUE)
    matrix = axes[2].table(cellText=[["0", "2070", "∞", "∞"], ["∞", "0", "934", "∞"],
                                    ["∞", "∞", "0", "769"], ["∞", "∞", "∞", "0"]],
                           rowLabels=["CAI", "MIL", "FRA", "HAM"],
                           colLabels=["CAI", "MIL", "FRA", "HAM"], cellLoc="center", loc="center")
    matrix.auto_set_font_size(False)
    matrix.set_fontsize(6.6)
    matrix.scale(0.95, 1.3)
    fig.suptitle("Illustrative representation: stored edge list → adjacency list; matrix shown for comparison",
                 color=BLUE, fontsize=10, weight="bold")
    _save(fig, DIAGRAMS / "graph_representation.png")

    fig, ax = plt.subplots(figsize=(10.5, 2.5))
    route = ["CAI", "MIL", "FRA", "HAM", "NYC", "HOU", "MEX"]
    modes = ["Sea", "Rail", "Rail", "Sea", "Road", "Road"]
    costs = [2070, 934, 769, 3689, 5282, 2872]
    ax.set_xlim(-0.35, 6.35)
    ax.set_ylim(-0.5, 1.25)
    ax.axis("off")
    for i, code in enumerate(route):
        ax.add_patch(Circle((i, 0.45), 0.18, facecolor="#eef4f7", edgecolor=BLUE2, linewidth=1.4))
        ax.text(i, 0.45, code, ha="center", va="center", fontsize=8, color=BLUE, weight="bold")
        if i < len(modes):
            _arrow(ax, (i + 0.2, 0.45), (i + 0.8, 0.45), color=GOLD, width=1.4)
            ax.text(i + 0.5, 0.92, f"{modes[i]}\n${costs[i]:,}", ha="center", va="center", fontsize=7, color=GREY)
    ax.text(3, -0.15, "Cost-minimizing path: $15,616 • Distance: 16,770 km • Estimated time: 540.6 h",
            ha="center", fontsize=9, color=BLUE, weight="bold")
    _save(fig, DIAGRAMS / "route_graph.png")

    vertices = [25, 50, 100, 200, 400, 800]
    random_values = {
        "Heap Dijkstra": [0.044, 0.081, 0.184, 0.494, 0.941, 1.728],
        "Array Dijkstra": [0.055, 0.189, 0.402, 1.259, 4.931, 19.645],
        "Bellman–Ford": [0.152, 0.263, 0.532, 1.655, 2.665, 7.924],
    }
    worst_values = {
        "Heap Dijkstra": [0.081, 0.080, 0.167, 0.352, 0.742, 1.677],
        "Array Dijkstra": [0.098, 0.129, 0.392, 1.261, 5.417, 19.827],
        "Bellman–Ford": [0.290, 1.146, 4.773, 20.169, 84.941, 343.631],
    }
    colors = {"Heap Dijkstra": "#2563b8", "Array Dijkstra": "#6f9bd1", "Bellman–Ford": "#b0306e"}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1))
    for ax, values, title in zip(axes, (random_values, worst_values),
                                 ("Random sparse graphs", "Bellman–Ford worst-case ordering")):
        for name, y in values.items():
            ax.plot(vertices, y, marker="o", linewidth=2, markersize=3.5,
                    color=colors[name], label=name)
        ax.set_yscale("log")
        ax.set_xlabel("Vertices (V)")
        ax.set_ylabel("Reported median time (ms, log scale)")
        ax.set_title(title, fontsize=9, color=BLUE)
        ax.grid(True, which="both", color="#dde5ea", linewidth=0.6)
        ax.legend(fontsize=7, frameon=False)
    fig.suptitle("Values supplied in the project brief; not a controlled hardware comparison",
                 fontsize=9.5, color=BLUE, weight="bold")
    _save(fig, CHARTS / "scaling_benchmarks.png")

    fig, ax = plt.subplots(figsize=(7, 3.4))
    labels = ["Heap Dijkstra", "Array Dijkstra", "Bellman–Ford"]
    times = [0.086, 0.116, 0.264]
    bars = ax.bar(labels, times, color=["#2563b8", "#6f9bd1", "#b0306e"], width=0.62)
    ax.set_ylabel("Supplied displayed median (ms)")
    ax.set_title("One Standard-network comparison instance", color=BLUE, fontsize=10)
    ax.grid(axis="y", color="#dde5ea", linewidth=0.6)
    ax.bar_label(bars, fmt="%.3f ms", padding=3, fontsize=8)
    ax.text(0.5, -0.23, "A single observed run does not establish universal superiority.",
            transform=ax.transAxes, ha="center", fontsize=8, color=GREY)
    _save(fig, CHARTS / "algorithm_comparison.png")


def capture_ui_screenshots() -> None:
    from playwright.sync_api import sync_playwright

    url = "http://127.0.0.1:5010/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1)
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        if response is None or response.status != 200:
            browser.close()
            raise RuntimeError(f"Local Meridian UI did not return HTTP 200: {url}")
        page.locator(".kpi").first.wait_for(timeout=30000)

        def capture(name: str) -> None:
            image = Image.open(BytesIO(page.screenshot(full_page=False))).convert("RGB")
            width, height = image.size
            image.crop((0, 0, width, min(height, 850))).save(SCREENSHOTS / name, format="PNG")

        capture("overview.png")
        overview = Image.open(SCREENSHOTS / "overview.png").convert("RGB")
        overview.crop((0, 0, overview.width, min(600, overview.height))).save(
            SCREENSHOTS / "overview_manual.png", format="PNG")

        page.locator("a[href='#optimizer']").click()
        page.locator("#src").select_option("CAI")
        page.locator("#dst").select_option("MEX")
        page.locator("#algoSeg button[data-a='dijkstra_heap']").click()
        page.locator("#calc").click()
        page.get_by_text("Optimal cost").first.wait_for(timeout=30000)
        capture("optimizer.png")

        page.locator("a[href='#lab']").click()
        page.locator("#run").click()
        page.get_by_text("Median time").first.wait_for(timeout=30000)
        capture("comparison.png")
        page.locator("#sizes").fill("25,50,100,200,400,800")
        page.locator("#bench").click()
        page.get_by_text("Measured times").first.wait_for(timeout=90000)
        page.get_by_text("Measured times").first.scroll_into_view_if_needed()
        capture("scaling.png")

        for nav, filename in (
            ("#manage", "network_manager.png"),
            ("#analytics", "analytics.png"),
            ("#learn", "algorithms_explained.png"),
        ):
            page.locator(f"a[href='{nav}']").click()
            page.locator("#view").wait_for(timeout=30000)
            capture(filename)
        browser.close()

    required = ("overview.png", "optimizer.png", "comparison.png", "scaling.png",
                "network_manager.png", "analytics.png", "algorithms_explained.png")
    missing = [name for name in required if not (SCREENSHOTS / name).is_file()]
    if missing:
        raise FileNotFoundError(f"UI capture did not create required screenshots: {missing}")


def _add_bookmark(paragraph, name: str, bookmark_id: int) -> None:
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def _field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    result = OxmlElement("w:t")
    result.text = "0"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instr, separate, result, end))


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def _set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def _keep_row_together(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def _bookmark_for_caption(kind: str, number: str) -> str:
    safe = re.sub(r"\W+", "_", number).strip("_").lower()
    return f"{kind}_{safe}"


def _inline(paragraph, text: str, doc: Document, bookmark_counter: list[int]) -> None:
    token_re = re.compile(r"(\{\{PAGEREF:[A-Za-z0-9_]+\}\}|\*\*.+?\*\*|\*.+?\*|`.+?`|\[[^\]]+\]\([^)]+\))")
    pos = 0
    for match in token_re.finditer(text):
        if match.start() > pos:
            paragraph.add_run(text[pos:match.start()])
        token = match.group(0)
        if token.startswith("{{PAGEREF:"):
            ref = PAGE_REF_RE.fullmatch(token).group(1)
            _field(paragraph, f"PAGEREF {ref} \\h")
        elif token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("*"):
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(8.5)
        else:
            link = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
            run = paragraph.add_run(f"{link.group(1)} ({link.group(2)})")
            run.font.color.rgb = RGBColor(35, 94, 135)
        pos = match.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])
    for run in paragraph.runs:
        if run.font.name is None:
            run.font.name = "Times New Roman"
        if run.font.size is None:
            run.font.size = Pt(9.4)


def _add_table(doc: Document, rows: list[list[str]], bookmark_counter: list[int]) -> None:
    if not rows:
        return
    cols = max(map(len, rows))
    table = doc.add_table(rows=1, cols=cols)
    table.style = "Table Grid"
    table.autofit = True
    for ridx, values in enumerate(rows):
        row = table.rows[0] if ridx == 0 else table.add_row()
        _keep_row_together(row)
        for col in range(cols):
            cell = row.cells[col]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _inline(p, values[col] if col < len(values) else "", doc, bookmark_counter)
            for run in p.runs:
                run.font.size = Pt(7.7)
                if ridx == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
            if ridx == 0:
                _set_cell_shading(cell, "163B5B")
            elif ridx % 2 == 0:
                _set_cell_shading(cell, "F1F5F8")
        if ridx == 0:
            _set_repeat_table_header(row)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.space_before = Pt(0)


def _parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            rows.append(cells)
        index += 1
    return rows, index


def _read_markdown_sections(files: list[Path]) -> tuple[list[tuple[Path, str, str]], list[tuple[str, Path]], list[tuple[str, Path]]]:
    sections = []
    figures = []
    tables = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            fig = FIGURE_RE.fullmatch(line.strip())
            if fig:
                image_path = (path.parent / fig.group(3)).resolve()
                if image_path.is_file():
                    figures.append((fig.group(1), image_path))
                else:
                    raise FileNotFoundError(f"Missing figure asset referenced by {path.name}: {image_path}")
            table = TABLE_RE.fullmatch(line.strip())
            if table:
                tables.append((f"Table {table.group(1)} – {table.group(2)}", path))
        sections.append((path, path.name, text))
    return sections, figures, tables


def _add_list_entry(doc: Document, caption: str, kind: str, number: str,
                    bookmark_counter: list[int]) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.55), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    p.add_run(caption)
    p.add_run("\t")
    _field(p, f"PAGEREF {_bookmark_for_caption(kind, number)} \\h")
    p.paragraph_format.keep_together = True


def _add_cover(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(55)
    p.paragraph_format.space_after = Pt(24)
    run = p.add_run("MERIDIAN – GRAPH-BASED LOGISTICS NETWORK AND ROUTE OPTIMIZATION PLATFORM")
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(18)
    for text, size, bold, italic, after in (
        ("A PROJECT REPORT", 14, True, False, 22),
        ("Submitted by", 14, True, True, 12),
        (f"{STUDENT_NAME} ({STUDENT_UID})", 16, True, False, 20),
        ("in partial fulfilment for the award of the degree of", 14, True, True, 15),
        ("BACHELOR OF ENGINEERING", 16, True, False, 8),
        ("IN", 12, True, False, 6),
        ("Computer Science Engineering", 14, False, False, 14),
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(after)
        r = p.add_run(text)
        r.bold, r.italic = bold, italic
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)
    logo = BRANDING / "chandigarh_university_logo.png"
    if not logo.is_file():
        raise FileNotFoundError(f"University logo is missing: {logo}")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.add_run().add_picture(str(logo), width=Inches(2.55))
    for text, size, bold in (
        ("Chandigarh University", 14, True),
        ("November 2026", 12, False),
        ("Advanced Data Structure  •  25CSH-202  •  3rd Semester", 10, False),
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(5)
        r = p.add_run(text)
        r.bold = bold
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)


def _add_page_number_footer(section) -> None:
    section.different_first_page_header_footer = True
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(f"{STUDENT_NAME}  |  UID {STUDENT_UID}  |  Page ")
    r.font.name = "Times New Roman"
    r.font.size = Pt(8)
    _field(p, "PAGE")


def _setup_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.52)
    section.left_margin = Inches(0.72)
    section.right_margin = Inches(0.68)
    section.header_distance = Inches(0.32)
    section.footer_distance = Inches(0.32)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(9)
    normal.font.color.rgb = RGBColor(28, 40, 50)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.space_after = Pt(1.5)
    for style_name, size, color in (
        ("Heading 1", 15, BLUE),
        ("Heading 2", 11.5, BLUE),
        ("Heading 3", 9.8, BLUE2),
    ):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
        style.paragraph_format.space_before = Pt(4 if style_name != "Heading 1" else 0)
        style.paragraph_format.space_after = Pt(1.5)
        style.paragraph_format.keep_with_next = True
    caption_style = doc.styles["Caption"]
    caption_style.font.name = "Times New Roman"
    caption_style.font.size = Pt(8.3)
    caption_style.font.italic = True
    caption_style.font.color.rgb = RGBColor(75, 88, 99)
    caption_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_style.paragraph_format.space_before = Pt(1)
    caption_style.paragraph_format.space_after = Pt(3)
    _add_page_number_footer(section)


def _add_image(doc: Document, path: Path, caption: str, counter: list[int]) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing figure: {path}")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(1)
    with Image.open(path) as im:
        width, height = im.size
    max_width, max_height = 6.62, (2.2 if caption.startswith("Figure U.") else 2.55)
    ratio = min(max_width / width, max_height / height)
    p.add_run().add_picture(str(path), width=Inches(width * ratio), height=Inches(height * ratio))
    cp = doc.add_paragraph(style="Caption")
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.keep_with_next = False
    cp.add_run(caption)
    match = re.match(r"Figure\s+([A-Za-z0-9.]+):", caption)
    if match:
        counter[0] += 1
        _add_bookmark(cp, _bookmark_for_caption("fig", match.group(1)), counter[0])


def _add_table_caption(doc: Document, caption: str, counter: list[int]) -> None:
    p = doc.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run(caption)
    match = re.match(r"Table\s+([A-Za-z0-9.]+)", caption)
    if match:
        counter[0] += 1
        _add_bookmark(p, _bookmark_for_caption("tab", match.group(1)), counter[0])


def _render_section(doc: Document, path: Path, text: str, figure_index, table_index,
                    bookmark_counter: list[int], heading_count: list[int]) -> None:
    lines = text.splitlines()
    i = 0
    cover_done = False
    current_top = ""
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            title = line[2:].strip()
            if title == "Cover Page":
                _add_cover(doc)
                cover_done = True
                heading_count[0] += 1
                current_top = title
                i += 1
                while i < len(lines) and not lines[i].startswith("# "):
                    i += 1
                continue
            if heading_count[0] > 0 and title in PAGE_BREAK_TITLES:
                doc.add_page_break()
            heading_count[0] += 1
            current_top = title
            p = doc.add_paragraph(style="Heading 1")
            p.paragraph_format.keep_with_next = True
            p.add_run(title)
            if title == "Bonafide Certificate":
                logo = BRANDING / "chandigarh_university_logo.png"
                p_logo = doc.add_paragraph()
                p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_logo.add_run().add_picture(str(logo), width=Inches(2.4))
            elif title == "Table of Contents":
                p_field = doc.add_paragraph()
                _field(p_field, 'TOC \\o "1-3" \\h \\z \\u')
                while i + 1 < len(lines) and not lines[i + 1].startswith("# "):
                    i += 1
            elif title == "List of Figures":
                for caption, image_path in figure_index:
                    match = re.match(r"Figure\s+([A-Za-z0-9.]+):", caption)
                    if match:
                        _add_list_entry(doc, caption, "fig", match.group(1), bookmark_counter)
                while i + 1 < len(lines) and not lines[i + 1].startswith("# "):
                    i += 1
            elif title == "List of Tables":
                for caption, _ in table_index:
                    match = re.match(r"Table\s+([A-Za-z0-9.]+)", caption)
                    if match:
                        _add_list_entry(doc, caption, "tab", match.group(1), bookmark_counter)
                while i + 1 < len(lines) and not lines[i + 1].startswith("# "):
                    i += 1
            i += 1
            continue
        if line == "## BONAFIDE CERTIFICATE":
            i += 1
            continue
        if line.startswith("## "):
            heading = line[3:].strip()
            style = "Heading 2"
            p = doc.add_paragraph(style=style)
            p.add_run(heading)
            if heading == STANDARD_BOOKMARKS["std_json"]:
                bookmark_counter[0] += 1
                _add_bookmark(p, "std_json", bookmark_counter[0])
            if heading == STANDARD_BOOKMARKS["std_quality"]:
                bookmark_counter[0] += 1
                _add_bookmark(p, "std_quality", bookmark_counter[0])
            i += 1
            continue
        if line.startswith("### "):
            heading = line[4:].strip()
            p = doc.add_paragraph(style="Heading 3")
            p.add_run(heading)
            for bookmark, target_heading in STANDARD_BOOKMARKS.items():
                if heading == target_heading:
                    bookmark_counter[0] += 1
                    _add_bookmark(p, bookmark, bookmark_counter[0])
            i += 1
            continue
        fig_match = FIGURE_RE.fullmatch(line)
        if fig_match:
            image_path = (path.parent / fig_match.group(3)).resolve()
            _add_image(doc, image_path, fig_match.group(1), bookmark_counter)
            i += 1
            continue
        table_match = TABLE_RE.fullmatch(line)
        if table_match:
            caption = f"Table {table_match.group(1)} – {table_match.group(2)}"
            _add_table_caption(doc, caption, bookmark_counter)
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                rows, i = _parse_table(lines, i + 1)
                _add_table(doc, rows, bookmark_counter)
            else:
                i += 1
            continue
        if line.startswith("|"):
            rows, i = _parse_table(lines, i)
            _add_table(doc, rows, bookmark_counter)
            continue
        if line.startswith("---"):
            i += 1
            continue
        if line.startswith("- ") or re.match(r"^\d+\.\s", line):
            ordered = not line.startswith("- ")
            p = doc.add_paragraph(style="List Bullet" if not ordered else "Normal")
            p.paragraph_format.space_after = Pt(2 if not ordered else 1.4)
            p.paragraph_format.line_spacing = 1.0 if ordered else 1.08
            body = line[2:] if not ordered else re.sub(r"^\d+\.\s*", "", line)
            if ordered:
                number = re.match(r"^(\d+)\.\s", line).group(1)
                p.paragraph_format.left_indent = Inches(0.25)
                p.paragraph_format.first_line_indent = Inches(-0.25)
                p.add_run(f"{number}. ")
            _inline(p, body, doc, bookmark_counter)
            i += 1
            continue
        p = doc.add_paragraph()
        p.paragraph_format.widow_control = True
        if current_top == "Cover Page" and not cover_done:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _inline(p, line, doc, bookmark_counter)
        i += 1


def create_docx() -> None:
    markdown_files = [
        CONTENT / "preliminary_pages.md",
        CONTENT / "chapter_1.md",
        CONTENT / "chapter_2.md",
        CONTENT / "chapter_3.md",
        CONTENT / "chapter_4.md",
        CONTENT / "chapter_5.md",
        CONTENT / "references.md",
        CONTENT / "appendices.md",
        CONTENT / "user_manual.md",
    ]
    missing = [p for p in markdown_files if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Required report sections are missing: {missing}")
    sections, figures, tables = _read_markdown_sections(markdown_files)
    replacements = {
        "Rishabh Singh": STUDENT_NAME,
        "25BCS11466": STUDENT_UID,
        "25BCS-707-A": STUDENT_CLASS,
    }
    sections = [
        (path, name, _replace_student_details(text, replacements))
        for path, name, text in sections
    ]
    doc = Document()
    _setup_document(doc)
    doc.core_properties.title = "Meridian – Graph-Based Logistics Network and Route Optimization Platform"
    doc.core_properties.subject = "Advanced Data Structure (25CSH-202) project report"
    doc.core_properties.author = f"{STUDENT_NAME} ({STUDENT_UID})"
    doc.core_properties.keywords = f"Chandigarh University; {STUDENT_UID}; Graphs; Dijkstra; Bellman-Ford"
    bookmark_counter = [10]
    heading_count = [0]
    for path, _name, text in sections:
        _render_section(doc, path, text, figures, tables, bookmark_counter, heading_count)
    doc.save(DOCX_PATH)
    print(f"DOCX_CREATED={DOCX_PATH}")
    print(f"FIGURES={len(figures)} TABLES={len(tables)}")


def _replace_student_details(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def export_pdf_with_word() -> None:
    ps = f"""
$ErrorActionPreference = 'Stop'
$docPath = '{str(DOCX_PATH).replace("'", "''")}'
$pdfPath = '{str(PDF_PATH).replace("'", "''")}'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($docPath)
$doc.Repaginate()
foreach ($story in $doc.StoryRanges) {{
    $current = $story
    while ($null -ne $current) {{
        $current.Fields.Update() | Out-Null
        $current = $current.NextStoryRange
    }}
}}
foreach ($toc in $doc.TablesOfContents) {{ $toc.Update() | Out-Null }}
foreach ($tof in $doc.TablesOfFigures) {{ $tof.Update() | Out-Null }}
$doc.Repaginate()
$doc.Fields.Update() | Out-Null
$doc.Save()
$pages = $doc.ComputeStatistics(2)
$doc.ExportAsFixedFormat($pdfPath, 17)
$doc.Close(0)
$word.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
Write-Output "WORD_PAGES=$pages"
Write-Output "PDF_CREATED=$pdfPath"
"""
    encoded = base64.b64encode(ps.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-EncodedCommand", encoded],
        cwd=ROOT, text=True, capture_output=True, timeout=180,
    )
    if result.returncode:
        raise RuntimeError(f"Microsoft Word PDF export failed:\n{result.stdout}\n{result.stderr}")
    print(result.stdout.strip())


def main() -> None:
    global DOCX_PATH, PDF_PATH, REPORT_STEM, STUDENT_NAME, STUDENT_UID, STUDENT_CLASS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-capture", action="store_true",
                        help="reuse existing verified local screenshots instead of recapturing them")
    parser.add_argument("--student", default=STUDENT_NAME, help="student's full name")
    parser.add_argument("--uid", default=STUDENT_UID, help="student UID")
    parser.add_argument("--class", dest="student_class", default=STUDENT_CLASS, help="student class")
    parser.add_argument("--output-stem", default=REPORT_STEM,
                        help="output filename stem, without extension")
    args = parser.parse_args()
    STUDENT_NAME, STUDENT_UID, STUDENT_CLASS = args.student, args.uid, args.student_class
    REPORT_STEM = args.output_stem
    DOCX_PATH = ROOT / f"{REPORT_STEM}.docx"
    PDF_PATH = ROOT / f"{REPORT_STEM}.pdf"
    create_diagrams()
    logo = BRANDING / "reference_page2_image3.jpeg"
    if not logo.is_file():
        raise FileNotFoundError("Extracted Chandigarh University logo is missing; inspect the local reference PDF first.")
    with Image.open(logo) as original:
        original.convert("RGB").save(BRANDING / "chandigarh_university_logo.png", format="PNG")
    if not args.no_capture:
        capture_ui_screenshots()
    create_docx()
    export_pdf_with_word()
    print(f"PDF={PDF_PATH}")


if __name__ == "__main__":
    main()
