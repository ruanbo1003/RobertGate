# Git 提交

## 流程

1. 运行 `git status` 查看所有变更和新增文件
2. 运行 `git diff --staged` 和 `git diff` 查看具体修改内容
3. 将所有变更文件（修改 + 新增）加入暂存区
4. 分析所有变更，用中文总结修改点，按 1、2、3、4 编号列出
5. 生成 commit message，格式如下：

```
<一句话概括本次提交>

变更内容：
1. xxx
2. xxx
3. xxx
```

6. 提交 commit
7. 运行 `git status` 确认提交成功

## 注意
- commit message 使用中文
- 不要 push 到远程
- 不要提交 .env、credentials 等敏感文件
- 不要提交 node_modules、.venv、__pycache__、*.db 等被 .gitignore 忽略的文件
