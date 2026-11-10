# -*- coding: utf-8 -*-
"""build_docx.py —— 从 markdown 生成四份投稿件
  1 <名>_匿名主稿.docx
  2 <名>_标题页.docx
  3 <名>_CoverLetter.docx
  4 <名>_图注表.docx
并清理文档属性（生成器名 / 缩略图 / 修订痕迹）。
用法：python build_docx.py [输入目录] [输出目录]
需要：python-docx（本机已装；若报 ModuleNotFoundError，双击 安装依赖.bat）
"""
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
except ModuleNotFoundError:
    print("缺少 python-docx。请双击：工具\\安装依赖.bat")
    sys.exit(2)

APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
    '<Application>Microsoft Office Word</Application><DocSecurity>0</DocSecurity>'
    '<ScaleCrop>false</ScaleCrop><LinksUpToDate>false</LinksUpToDate>'
    '<SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged>'
    '<AppVersion>16.0000</AppVersion></Properties>'
)


def read_cfg():
    cfg = {"title": "", "author": "", "affiliation": "", "email": "", "orcid": "",
           "funding": "", "journal": "", "editor": "", "anonymize": "1",
           "acknowledgements": "", "anon_extra": ""}
    p = ROOT / "docx_config.txt"
    if p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def read_any(p):
    if p.suffix.lower() == ".docx":
        import html as _html
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        xml = xml.replace("</w:p>", "\n").replace("</w:tr>", "\n").replace("</w:tc>", " ")
        return _html.unescape(re.sub(r"<[^>]+>", "", xml))
    return p.read_text(encoding="utf-8-sig", errors="replace")


def inline_runs(par, text):
    """把 **粗体** / *斜体* 写进段落"""
    for token in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not token:
            continue
        if token.startswith("**") and token.endswith("**") and len(token) > 4:
            r = par.add_run(token[2:-2])
            r.bold = True
        elif token.startswith("*") and token.endswith("*") and len(token) > 2:
            r = par.add_run(token[1:-1])
            r.italic = True
        else:
            par.add_run(token)


def is_caption(line):
    s = line.strip()
    return bool(re.match(r"^(figure|fig\.?|table|图|表)\s*\d+", s, re.I)) or \
        bool(re.match(r"^\*\*(figure|fig\.?|table|图|表)\s*\d+", s, re.I))


def parse_md(text):
    """返回 blocks: (type, payload)"""
    text = re.sub(r"(?s)^---\n.*?\n---\n", "", text)   # 去掉 YAML 头
    lines = text.splitlines()
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not re.match(r"^[\s:\-|]+$", "|".join(row)):
                    rows.append(row)
                i += 1
            blocks.append(("table", rows))
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            blocks.append(("h", (len(m.group(1)), m.group(2).strip())))
            i += 1
            continue
        if re.match(r"^[-*]\s+", s):
            blocks.append(("li", re.sub(r"^[-*]\s+", "", s)))
            i += 1
            continue
        if re.match(r"^\d+[\.\)]\s+", s):
            blocks.append(("li", re.sub(r"^\d+[\.\)]\s+", "", s)))
            i += 1
            continue
        if s.startswith(">"):
            blocks.append(("quote", s.lstrip("> ").strip()))
            i += 1
            continue
        blocks.append(("p", s))
        i += 1
    return blocks


def setup(doc):
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.5


def add_table(doc, rows):
    if not rows:
        return
    cols = max(len(r) for r in rows)
    t = doc.add_table(rows=len(rows), cols=cols)
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j in range(cols):
            cell = t.cell(i, j)
            cell.text = row[j] if j < len(row) else ""
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)


def render(blocks, doc, skip_ack=False, allow_title=True):
    skipping = False
    for kind, payload in blocks:
        if kind == "h":
            level, title = payload
            if skip_ack and re.search(r"acknowledg|致谢", title, re.I):
                skipping = True
                continue
            skipping = False
            if level == 1 and allow_title:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(title)
                r.bold = True
                r.font.size = Pt(16)
                doc.core_properties.title = title
            else:
                doc.add_heading(title, level=min(level, 4) - 1 if level > 1 else 1)
        elif kind == "table":
            if not skipping:
                add_table(doc, payload)
        elif kind == "li":
            if not skipping:
                p = doc.add_paragraph(style="List Bullet")
                inline_runs(p, payload)
        elif kind == "quote":
            if not skipping:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.8)
                inline_runs(p, payload)
        else:
            if not skipping:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                inline_runs(p, payload)


def scrub(src, dst, title, author, subject=""):
    """读 src，写 dst：去缩略图、去悬空关系、换 app.xml"""
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            name = item.filename
            if name == "docProps/thumbnail.jpeg":
                continue
            data = zin.read(name)
            if name == "docProps/app.xml":
                data = APP_XML.encode("utf-8")
            if name == "_rels/.rels":
                txt = data.decode("utf-8")
                txt = re.sub(r'<Relationship[^>]*thumbnail[^>]*/>', "", txt)
                data = txt.encode("utf-8")
            zout.writestr(item, data)


def style_meta(doc, author, title, subject=""):
    cp = doc.core_properties
    cp.author = author
    cp.last_modified_by = author
    cp.title = title
    cp.subject = subject
    cp.comments = ""
    cp.category = ""
    cp.created = datetime.now()
    cp.modified = datetime.now()


def main():
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input"
    outp = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "output" / "docx"
    outp.mkdir(parents=True, exist_ok=True)
    cfg = read_cfg()
    anon = cfg.get("anonymize", "1") not in ("0", "false", "no")

    files = sorted(list(inp.glob("*.md")) + list(inp.glob("*.txt")))
    files = [f for f in files if not f.name.lower().startswith(("readme", "_", "~$"))]
    docx_in = [f.name for f in inp.glob("*.docx") if not f.name.startswith("~$")]
    if docx_in:
        print("注意：以下 docx 不参与重建（docx 无法保真还原表格与格式）：")
        for n in docx_in:
            print("  -", n)
        print("请用 md 源稿生成；或先另存为 md。\n")
    if not files:
        print("找不到 md/txt 源稿。请把 .md 放进：%s" % inp)
        return 2

    for f in files:
        text = read_any(f)
        blocks = parse_md(text)
        title = next((p[1] for k, p in blocks if k == "h" and p[0] == 1), cfg.get("title") or f.stem)

        # 匿名替换
        if anon:
            for key, repl in (("author", "[Author]"), ("affiliation", "[Institution]"),
                              ("email", "[Email]"), ("orcid", "[ORCID]"), ("funding", "[Funding]")):
                val = cfg.get(key, "")
                if val:
                    text = text.replace(val, repl)
            # 额外替换词（如自引里的姓氏拼音），逗号分隔
            for token in [x.strip() for x in (cfg.get("anon_extra") or "").split(",") if x.strip()]:
                text = re.sub(r"\b%s\b" % re.escape(token), "[Author]", text)
            blocks = parse_md(text)
            author = ""
        else:
            author = cfg.get("author", "")

        # 1 匿名主稿
        doc = Document()
        setup(doc)
        render(blocks, doc, skip_ack=anon, allow_title=True)
        style_meta(doc, author, title)
        p1 = outp / ("%s_匿名主稿.docx" % f.stem)
        raw = outp / ("~raw1_%s.docx" % f.stem)
        doc.save(raw)
        scrub(raw, p1, title, author)
        raw.unlink(missing_ok=True)

        # 2 标题页
        doc = Document()
        setup(doc)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(cfg.get("title") or title)
        r.bold = True
        r.font.size = Pt(16)
        doc.add_paragraph()
        for label, key in (("Author", "author"), ("Affiliation", "affiliation"),
                           ("Email", "email"), ("ORCID", "orcid"), ("Funding", "funding")):
            val = cfg.get(key, "")
            if val:
                doc.add_paragraph("%s: %s" % (label, val))
        if cfg.get("acknowledgements"):
            doc.add_heading("Acknowledgements", level=2)
            doc.add_paragraph(cfg["acknowledgements"])
        doc.add_heading("Declarations", level=2)
        doc.add_paragraph("Conflict of interest: The author declares no competing interests.")
        doc.add_paragraph("Data availability: Data are available from public sources; "
                          "the corpus and coding scheme can be provided on reasonable request.")
        doc.add_paragraph("Use of generative AI: [to be completed according to the journal's AI "
                          "policy: tool name, version, purpose; the author takes full responsibility]")
        style_meta(doc, cfg.get("author", ""), "Title page")
        p2 = outp / ("%s_标题页.docx" % f.stem)
        raw = outp / ("~raw2_%s.docx" % f.stem)
        doc.save(raw)
        scrub(raw, p2, "Title page", cfg.get("author", ""))
        raw.unlink(missing_ok=True)

        # 3 Cover Letter
        doc = Document()
        setup(doc)
        doc.add_paragraph(datetime.now().strftime("%d %B %Y"))
        doc.add_paragraph()
        doc.add_paragraph("Dear %s," % (cfg.get("editor") or "Editor"))
        doc.add_paragraph()
        doc.add_paragraph(
            "I submit the manuscript entitled \u201c%s\u201d for consideration by %s."
            % (cfg.get("title") or title, cfg.get("journal") or "[Journal]"))
        doc.add_paragraph(
            "The manuscript addresses [the question] and argues that [the claim]. "
            "It draws on [material] and makes [one or two contributions].")
        doc.add_paragraph(
            "I believe the manuscript fits the journal's scope, particularly its interest in "
            "[quote from Aims & Scope].")
        doc.add_paragraph(
            "The manuscript is original, has not been published elsewhere, and is not under "
            "consideration by another journal. The author has approved the submission.")
        doc.add_paragraph()
        doc.add_paragraph("Yours sincerely,")
        doc.add_paragraph(cfg.get("author", "[Author]"))
        doc.add_paragraph(cfg.get("affiliation", "[Institution]"))
        style_meta(doc, cfg.get("author", ""), "Cover letter")
        p3 = outp / ("%s_CoverLetter.docx" % f.stem)
        raw = outp / ("~raw3_%s.docx" % f.stem)
        doc.save(raw)
        scrub(raw, p3, "Cover letter", cfg.get("author", ""))
        raw.unlink(missing_ok=True)

        # 4 图注表
        caps = [l.strip() for l in text.splitlines() if is_caption(l)]
        doc = Document()
        setup(doc)
        doc.add_heading("图注与表注清单", level=1)
        if caps:
            for c in caps:
                p = doc.add_paragraph()
                inline_runs(p, c)
        else:
            doc.add_paragraph("（未在稿件中识别到以 Figure/Table/图/表 开头的题注）")
        style_meta(doc, author, "Captions")
        p4 = outp / ("%s_图注表.docx" % f.stem)
        raw = outp / ("~raw4_%s.docx" % f.stem)
        doc.save(raw)
        scrub(raw, p4, "Captions", author)
        raw.unlink(missing_ok=True)

        words = len(re.findall(r"[A-Za-z][A-Za-z'’\-]*", text))
        print("已生成 4 份文件（源：%s，约 %d 词）：" % (f.name, words))
        for pth in (p1, p2, p3, p4):
            print("  -", pth.name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
