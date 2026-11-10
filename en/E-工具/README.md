# E-工具

> 5 个脚本，按步骤用。全部只读命令行参数指定的目录，不写死路径。

## 脚本清单

| 脚本 | 干什么 | 哪一步 |
|---|---|---|
| `init_workspace.py` | 一键建出 16 目录 24 文件的空工作区（幂等） | 第 1 步 |
| `check_workspace.py` | 三态检查 missing / stub / ok，告诉你卡在哪一步 | 每步 |
| `check_freeze.py` | 清稿六类正则机检（待定/内部语/投稿策略/版本尾注/回迁语/审稿痕迹） | 第 7 步 |
| `build_docx.py` | 从 md 生成四份投稿件（匿名主稿/标题页/CoverLetter/图注表） | 第 10 步 |
| `scrub_meta.py` | 清 docx 生成器痕迹（缩略图/python-docx 字样/2013 日期），清完自检 | 第 10 步 |

## 典型用法（在仓库根目录）

```powershell
# 第 1 步：在 paper-01/ 建工作区
python E-工具\init_workspace.py paper-01

# 每步：看进度
python E-工具\check_workspace.py paper-01

# 第 7 步：清稿后机检
python E-工具\check_freeze.py paper-01\06-清稿\中文-冻结-v1.md

# 第 10 步：先生成 docx（输入是英文定稿 md，输出到投稿包）
# 首次用：把 docx_config.example.txt 复制成 docx_config.txt 并填作者信息
python E-工具\build_docx.py paper-01\07-英译 paper-01\09-投稿包

# 再清元数据（build 之后跑）
python E-工具\scrub_meta.py paper-01\09-投稿包
```

## 依赖

- 全部只需 Python 3；
- `build_docx.py` / `scrub_meta.py` 需要 **python-docx**，没装时：
  ```powershell
  python -m pip install python-docx
  ```
- 其余三个脚本零依赖。

## 不在这里做的事

以下检查是 md 文本层，靠 `A-检查清单` 和 `D-提示词` 里的 S2/D9 完成，不脚本化：数字对账、术语命中、引用闭合、字数。脚本只做**文件层**（目录、docx、元数据）和**六类痕迹**这两件机器比人靠谱的事。

---

*v2 样张 ｜ 2026-11-10*
