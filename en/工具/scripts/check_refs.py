# -*- coding: utf-8 -*-
"""check_refs.py —— 参考文献检查（闭合 + 字段）
用法：python check_refs.py [输入目录] [输出目录]

判法说明（重要）：
  · "未引用" = 文献表里该作者名在正文中一次都没出现（按整词匹配）。
    这是保守判法：宁可漏报，不制造大量假阳性。
  · "正文引了但表中没有" = 正文出现"某某 (年份)"，但文献表里找不到该姓氏。
  · 结果是候选清单，仍需人工确认。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
YEAR = r"(?:19|20)\d{2}"
HEAD = re.compile(r"^(#{1,6})\s*(.+?)\s*$", re.M)
NAME = r"[A-Z][A-Za-z\u00C0-\u024F'\-]{1,}"
STOP = {"the", "this", "that", "these", "those", "in", "a", "an", "it", "we", "they",
        "however", "yet", "but", "and", "from", "with", "for", "on", "of", "to", "as",
        "table", "figure", "section", "journal", "vol", "no", "note", "see", "also",
        "appendix", "chapter", "part", "study", "paper", "article"}


def read_any(p):
    if p.suffix.lower() == ".docx":
        import zipfile
        import html as _html
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        xml = xml.replace("</w:p>", "\n").replace("</w:tr>", "\n").replace("</w:tc>", " ")
        return _html.unescape(re.sub(r"<[^>]+>", "", xml))
    return p.read_text(encoding="utf-8-sig", errors="replace")


def normalize(text):
    text = re.sub(r"(?im)^[ \t]*(abstract|摘要)[ \t]*[:：]?[ \t]*",
                  lambda m: "\n## " + m.group(1) + "\n", text, count=1)
    text = re.sub(r"(?im)^[ \t]*(references|bibliography|参考文献)[ \t]*[:：]?[ \t]*$",
                  lambda m: "\n## " + m.group(1) + "\n", text, count=1)
    return text


def split_refs(text):
    marks = [(m.start(), m.end(), m.group(2)) for m in HEAD.finditer(text)]
    for i, (s, e, title) in enumerate(marks):
        if re.search(r"reference|bibliography|参考文献", title, re.I):
            nxt = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            return text[:s], text[e:nxt]
    return text, ""


def parse_entries(body):
    # 到附录就停
    cut = len(body)
    for m in re.finditer(r"(?im)^[ \t]*(appendix|appendices|附录)\b.*$", body):
        cut = m.start()
        break
    body = body[:cut]

    lines = [l.rstrip() for l in body.splitlines()]
    if len([l for l in lines if re.match(r"^\s*(\d+[\.\)]|\[\d+\])\s+", l)]) >= 2:
        entries, cur = [], []
        for l in lines:
            if re.match(r"^\s*(\d+[\.\)]|\[\d+\])\s+", l):
                if cur:
                    entries.append(" ".join(cur).strip())
                cur = [re.sub(r"^\s*(\d+[\.\)]|\[\d+\])\s+", "", l).strip()]
            elif l.strip():
                if cur:
                    cur.append(l.strip())
        if cur:
            entries.append(" ".join(cur).strip())
        return [e for e in entries if e]

    blocks = re.split(r"\n\s*\n", body)
    out = []
    for b in blocks:
        b = " ".join(x.strip() for x in b.splitlines() if x.strip())
        if b:
            out.append(b)
    return out


def first_key(entry):
    s = re.sub(r"^\s*(\d+[\.\)]|\[\d+\])\s*", "", entry)
    m = re.match(r"([A-Z][A-Za-z\u00C0-\u024F'\-]{1,})", s)
    return m.group(1) if m else ""


def entry_year(entry):
    m = re.search(r"\((%s)[a-z]?\)" % YEAR, entry) or re.search(r"\b(%s)\b" % YEAR, entry)
    return m.group(1) if m else ""


def cited_names(body):
    """正文里被引到的姓氏（含 et al. 与所有格）"""
    found = set()
    for m in re.finditer(r"(%s)(?:'s)?\s+(?:et\s+al\.?\s*)?\(%s[a-z]?\)" % (NAME, YEAR), body):
        found.add(m.group(1).lower())
    for m in re.finditer(r"\(([^()]{1,200}?(?:%s)[a-z]?[^()]{0,100})\)" % YEAR, body):
        chunk = m.group(1)
        for w in re.findall(NAME, chunk):
            if w.lower() not in STOP:
                found.add(w.lower())
    found = {re.sub(r"'s$", "", w) for w in found}
    return {w for w in found if w not in STOP}


def main():
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input"
    outp = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "output"
    outp.mkdir(parents=True, exist_ok=True)
    files = sorted(list(inp.glob("*.md")) + list(inp.glob("*.txt")) + list(inp.glob("*.docx")))
    files = [f for f in files if not f.name.lower().startswith(("readme", "_", "~$"))]
    if not files:
        print("找不到稿件。请把 .md / .txt / .docx 放进：%s" % inp)
        return 2

    all_ok = True
    for f in files:
        text = normalize(read_any(f))
        body, ref_body = split_refs(text)
        entries = parse_entries(ref_body)
        body_low = body.lower()

        uncited, no_doi, dup, seen = [], [], [], set()
        for e in entries:
            key = first_key(e)
            if key and not re.search(r"\b%s\b" % re.escape(key), body_low, re.I):
                uncited.append(e)
            if not (re.search(r"10\.\d{4,9}/", e) or "doi" in e.lower()):
                no_doi.append(e)
            norm = re.sub(r"\W+", "", e.lower())[:100]
            if norm in seen:
                dup.append(e)
            seen.add(norm)

        refs_low = ref_body.lower()
        missing = sorted(n for n in cited_names(body)
                         if not re.search(r"\b%s\b" % re.escape(n), refs_low, re.I))

        ok = not uncited and not missing and not no_doi and not dup
        all_ok = all_ok and ok

        rep = ["# 参考文献检查报告", "", "文件：`%s`" % f.name, "",
               "- 文献条目：%d" % len(entries),
               "- 正文识别到的姓氏：%d" % len(cited_names(body)), "",
               "## 1 文献表中未在正文出现（疑似未引用）：%d" % len(uncited), ""]
        rep += (["- " + e[:120] for e in uncited] or ["无。"])
        rep += ["", "## 2 正文引了但表中找不到姓氏：%d" % len(missing), ""]
        rep += (["- " + m for m in missing] or ["无。"])
        rep += ["", "## 3 缺 DOI：%d" % len(no_doi), ""]
        rep += (["- " + e[:120] for e in no_doi] or ["无。"])
        rep += ["", "## 4 疑似重复条目：%d" % len(dup), ""]
        rep += (["- " + e[:120] for e in dup] or ["无。"])
        rep += ["", "> 保守判法，用于缩小人工核对范围；请逐条确认。", "",
                "**%s**" % ("PASS" if ok else "FAIL"), ""]

        (outp / ("report_refs_%s.md" % f.stem)).write_text("\n".join(rep), encoding="utf-8")
        print("\n".join(rep))

    print("\n==== 汇总：%s ====" % ("全部 PASS" if all_ok else "有 FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
