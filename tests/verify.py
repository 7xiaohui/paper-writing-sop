#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复跑两条产线的样本验证。

在仓库根目录执行：

    python tests/verify.py

它做两件事：
  1. 英文线（v5.0）：
     - init_workspace.py 建区后，check_workspace.py 能读出来；
     - check_freeze.py 对干净样本 exit 0、对脏样本 exit 1；
  2. 中文线：用 fixtures/zh 下的干净样本与脏样本，断言 refs / marks / punct
     在干净样本上零命中、在脏样本上能报出问题。

退出码：0 全部通过；1 有失败；2 环境错误。
它只依赖 Python 标准库，不需要安装任何包。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PY = sys.executable

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

EN_TOOLS = ROOT / "en" / "E-工具"
EN_FIXTURES = HERE / "fixtures" / "en"
ZH_SCRIPT = ROOT / "zh" / "工具" / "核对脚本.py"
ZH_FIXTURES = HERE / "fixtures" / "zh"

ENV = dict(os.environ)
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONUTF8"] = "1"

results: list[tuple[str, bool, str]] = []


def run(args: list[object]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, *[str(a) for a in args]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
    )


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else "  <- " + detail))


def tail(text: str, n: int = 240) -> str:
    text = " ".join(text.split())
    return text[-n:]


# ---------- 英文线 ----------

def verify_en() -> None:
    print("\n[英文线 v5.0] 建区 / 进度 / 清稿机检")

    with tempfile.TemporaryDirectory(prefix="sop_en_") as td:
        space = Path(td) / "paper-01"

        proc = run([EN_TOOLS / "init_workspace.py", str(space)])
        check("init_workspace 建区", proc.returncode == 0,
              "exit %d：%s" % (proc.returncode, tail(proc.stdout or proc.stderr)))

        proc = run([EN_TOOLS / "check_workspace.py", str(space)])
        check("check_workspace 读新区", proc.returncode == 0,
              "exit %d：%s" % (proc.returncode, tail(proc.stdout or proc.stderr)))

    for sample, expected in (("clean.md", 0), ("dirty.md", 1)):
        proc = run([EN_TOOLS / "check_freeze.py", EN_FIXTURES / sample])
        ok = proc.returncode == expected
        check("check_freeze <- %s" % sample, ok,
              "期望 exit %d，实际 %d：%s" % (
                  expected, proc.returncode, tail(proc.stdout or proc.stderr)))


# ---------- 中文线 ----------

def verify_zh() -> None:
    print("\n[中文线] refs / marks / punct × 干净样本与脏样本")

    clean = ZH_FIXTURES / "clean.md"
    dirty = ZH_FIXTURES / "dirty.md"
    refs = ZH_FIXTURES / "refs.txt"

    cases = [
        ("refs 干净样本", ["refs", clean, refs], 0),
        ("refs 脏样本（悬空/冗余）", ["refs", dirty, refs], 1),
        ("marks 干净样本", ["marks", clean], 0),
        ("marks 脏样本（残留标记）", ["marks", dirty], 1),
        ("punct 干净样本", ["punct", clean], 0),
        ("punct 脏样本（ASCII 引号）", ["punct", dirty], 1),
    ]
    for name, args, expected in cases:
        proc = run([ZH_SCRIPT, *args])
        ok = proc.returncode == expected
        detail = "期望 exit %d，实际 %d：%s" % (
            expected, proc.returncode, tail(proc.stdout or proc.stderr))
        check("zh/%s" % name, ok, detail)


def main() -> int:
    print("=" * 60)
    print(" 论文写作 SOP · 样本验证")
    print(" 仓库：%s" % ROOT)
    print(" Python：%s" % sys.version.split()[0])
    print("=" * 60)

    for path in (EN_TOOLS, EN_FIXTURES, ZH_SCRIPT, ZH_FIXTURES):
        if not path.exists():
            print("[错误] 找不到：%s" % path)
            return 2

    verify_en()
    verify_zh()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    failed = total - passed

    print("\n" + "=" * 60)
    if failed:
        print("==== 失败 %d/%d ====" % (failed, total))
        for name, ok, detail in results:
            if not ok:
                print("  - %s：%s" % (name, detail))
        return 1

    en_total = 4
    zh_total = total - en_total
    print("==== 全部通过：英文线 %d/%d，中文线 %d/%d ====" % (
        en_total, en_total, zh_total, zh_total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
