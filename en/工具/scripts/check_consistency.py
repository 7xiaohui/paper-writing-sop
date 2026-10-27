# -*- coding: utf-8 -*-
"""check_consistency.py —— 一致性检查
查四件事：
  1 摘要 / 正文 / 结论 的"发现项数"是否一致
  2 人称是否混用（we/our 与 this study/this paper/the author）
  3 是否出现两处以上的"结论总起句"（双结论）
  4 引用了 Section X，但标题没有编号
用法：python check_consistency.py [输入目录] [输出目录]
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
HEAD = re.compile(r"^(#{1,6})\s*(.+?)\s*$", re.M)
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}


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


def cut_sections(text):
    """按行定位：返回 (abstract, body, conclusion)。body 不含摘要、关键词、结论、文献。"""
    lines = text.splitlines()

    def find(pats, start=0):
        for i in range(start, len(lines)):
            s = lines[i].strip().strip("#").strip()
            for p in pats:
                if re.match(p, s, re.I):
                    return i
        return None

    a = find([r"abstract\b", r"^摘要"])
    k = find([r"key\s*words?\b", r"^关键词"], (a or 0) + 1)
    r = find([r"^(references|bibliography)\b", r"^参考文献"], (a or 0) + 1)
    c = find([r"^(\d+\.?\s*)?conclusions?\b", r"^(\d+\.?\s*)?结\s*论"], (a or 0) + 1)

    def seg(i, j):
        if i is None:
            return ""
        return "\n".join(lines[i + 1:j if j else len(lines)])

    abstract = seg(a, k)
    body = seg(k, c if c is not None else (r or len(lines)))
    conclusion = seg(c, r) if c is not None else ""
    return abstract, body, conclusion


def nums_in(text):
    vals = []
    for p in (r"(?<![\d.])\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
              r"(?:main\s+|key\s+|principal\s+|core\s+)?findings?\b",
              r"(?<![\d.])\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
              r"(?:theoretical\s+|empirical\s+)?contributions?\b"):
        for m in re.finditer(p, text, re.I):
            w = m.group(1).lower()
            v = NUM_WORDS.get(w)
            if v is None and w.isdigit():
                v = int(w)
            if v:
                vals.append(v)
    for m in re.finditer(r"(\d+|[一二三四五六七八九十])\s*(?:项|个)\s*(?:主要)?(?:发现|贡献)", text):
        w = m.group(1)
        v = NUM_WORDS.get(w)
        if v is None and w.isdigit():
            v = int(w)
        if v:
            vals.append(v)
    return vals


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
        abstract, body, conclusion = cut_sections(text)

        # 1 发现项数
        a_nums, b_nums, c_nums = nums_in(abstract), nums_in(body), nums_in(conclusion)
        a_set, b_set, c_set = set(a_nums), set(b_nums), set(c_nums)
        if a_set and b_set:
            found_ok = not (a_set - b_set)
        elif a_set and c_set:
            found_ok = not (a_set - c_set)
        else:
            found_ok = True

        # 2 人称（"us" 多为修辞用法，只作 WARN，不计入 FAIL）
        we = len(re.findall(r"\b(we|our)\b", body, re.I))
        imp = len(re.findall(r"\b(this study|this paper|this article|the author|the present study)\b",
                             body, re.I))
        person_fail = we >= 2 and imp > 0
        person_warn = 0 < we < 2 and imp > 0

        # 3 双结论
        concl_starts = len(re.findall(r"conclusions?\s+(?:follow|are drawn)|以下(?:三|几|四)点结论",
                                      text, re.I))
        concl_ok = concl_starts <= 1

        # 4 交叉引用 vs 编号
        numbered = bool(re.search(r"(?m)^\s*\d+(?:\.\d+)*\.?\s+[A-Z\u4e00-\u9fff]", text))
        sec_ref = bool(re.search(r"\bSections?\s+\d|第\d+[章节]", text))
        xref_ok = (not sec_ref) or numbered

        ok = found_ok and not person_fail and concl_ok and xref_ok
        all_ok = all_ok and ok

        rep = ["# 一致性检查报告", "", "文件：`%s`" % f.name, "",
               "## 1 发现项数", ""]
        rep.append("| 位置 | 识别到的数字 |")
        rep.append("|---|---|")
        rep.append("| 摘要 | %s |" % (a_nums or "—"))
        rep.append("| 正文 | %s |" % (b_nums or "—"))
        rep.append("| 结论 | %s |" % (c_nums or "—"))
        rep.append("")
        rep.append("**%s**%s" % ("PASS" if found_ok else "FAIL",
                                 "" if found_ok else "：摘要里的数字在正文中找不到对应"))
        rep += ["", "## 2 人称", ""]
        rep.append("- we/our/us：%d 次；this study/paper/the author：%d 次" % (we, imp))
        rep.append("- **%s**%s" % ("PASS" if not person_fail else "FAIL",
                                   "" if not person_fail else "：两种人称混用，单作者应统一"))
        if person_warn:
            rep.append("- WARN：出现 1 次 we，请确认是否为修辞用法（例如 we know that…）")
        rep += ["", "## 3 结论总起句", ""]
        rep.append("- 命中 %d 次（应 ≤1）→ **%s**" % (concl_starts, "PASS" if concl_ok else "FAIL"))
        rep += ["", "## 4 交叉引用与编号", ""]
        rep.append("- 标题有编号：%s；正文引用 Section/章：%s" % ("是" if numbered else "否",
                                                              "是" if sec_ref else "否"))
        rep.append("- **%s**%s" % ("PASS" if xref_ok else "FAIL",
                                   "" if xref_ok else "：引用了编号，但标题没有编号"))
        rep += ["", "**总结论：%s**" % ("PASS" if ok else "FAIL"), ""]

        (outp / ("report_consistency_%s.md" % f.stem)).write_text("\n".join(rep), encoding="utf-8")
        print("\n".join(rep))

    print("\n==== 汇总：%s ====" % ("全部 PASS" if all_ok else "有 FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
