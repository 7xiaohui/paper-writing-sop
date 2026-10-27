# input：放待检查的稿件

- 支持 `.docx / .md / .txt`；
- 可以放多份，脚本会逐份出报告；
- 文件名不要以 `README`、`_`、`~$` 开头（会被跳过）；
- 稿件里的 `Abstract`、`References` 要各占一行，脚本靠它们切节；
- 关键词写成 `Keywords: a; b; c`。

**本目录内容不会提交到仓库**（`.gitignore` 已排除），可以放未发表的稿子。
