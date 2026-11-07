# 投资报告 Agent API（invest-reports）

对应 PRD：`docs/prd/invest-reports.md`。统一前缀 `/api/v1/invest-reports`，JWT Bearer 鉴权，
响应遵循 `{code, data, message}`（`.claude/rules/api.md`）。

## 0. 错误码

| 码 | 常量 | 含义 |
|----|------|------|
| 2040 | IR_PARAM_INVALID | 参数错误（通用） |
| 2041 | IR_NOT_FOUND | 范本/项目/章节/资料/引用不存在 |
| 2042 | IR_TEMPLATE_NOT_READY | 该类型模板未学习（建项目/拆章前置校验） |
| 2043 | IR_SOURCE_UNPARSEABLE | 资料无法解析（损坏/不支持的格式） |
| 2044 | IR_CHAPTER_BUSY | 章节正在研究/更新中，拒绝编辑或重复入队 |
| 2045 | IR_EXPORT_BLOCKED | 导出被阻止：存在未处理的「待补充」 |
| 2046 | IR_CONFIRM_REQUIRED | 需确认：增量更新命中有未保存编辑的章节 |
| 5001 | IR_UPSTREAM_FAILED | LLM/检索上游失败（撞号惯例，同 AV_UPSTREAM_FAILED） |
| 5002 | IR_UPSTREAM_QUOTA | OpenRouter 余额/Key 全局错误 → 研究队列整体暂停 |
| 5004 | IR_EXPORT_FAILED | docx 生成失败 |

## 1. 核心数据形态

```jsonc
// Template（每类型至多一份）
{ "type": "advice",                  // advice=投资建议书 | dd=尽调报告
  "status": "ready",                 // none | learning | ready | failed
  "chapters": [ { "key": "industry", "title": "三、行业分析",
                  "brief": "市场规模与增速、驱动因素、政策…" } ],
  "style_notes": "数据先行，每章末有小结…",
  "learned_from": [3,5,8], "error": null, "updated_at": "…" }

// Sample（范本文件）
{ "id": 3, "type": "advice", "filename": "XX智造投资建议书_终版.docx",
  "parse_state": "ready",            // parsing | ready | failed
  "uploaded_at": "…" }

// Project 摘要（列表用）
{ "id": 1, "title": "云帆科技 · A 轮", "type": "advice",
  "status": "researching",           // draft | researching | partial_failed | completed
  "chapters_done": 3, "chapters_total": 9, "tbd_count": 2, "updated_at": "…" }

// Source（项目资料）
{ "id": 11, "kind": "file",          // file | url
  "filename": "BP_云帆科技.pdf", "url": null,
  "parse_state": "ready",            // pending | parsing | ready | failed
  "quality": "ok",                   // ok | low（扫描件置信度低）
  "uploaded_at": "…" }

// Chapter 详情（编辑器用）
{ "id": 21, "key": "industry", "title": "三、行业分析",
  "state": "done",                   // pending | researching | done | failed | stale | updating
  "error": null, "version": 4,
  "paragraphs": [
    { "id": "p1",
      "text": "…2025 年国内公有云市场规模达到 4,562 亿元⟦c:101⟧，其中…⟦tbd:7⟧…",
      // 正文内联标记：⟦c:引用id⟧ 引用角标、⟦tbd:id⟧ 待补充胶囊，前端解析渲染
    } ],
  "citations": [
    { "id": 101, "n": 1, "source_type": "web",   // web | file | manual
      "title": "IDC · 中国公有云市场跟踪", "url": "https://…",
      "source_id": null, "page": null,
      "quote": "2025 年中国公有云服务整体市场规模达 4,562.1 亿元…",
      "captured_at": "2026-09" } ],
  "tbds": [
    { "id": 7, "reason": "未找到竞对最新估值的可靠来源",
      "value": null, "resolved": false } ] }

// FeedEvent（研究进度流）
{ "id": 901, "chapter_id": 22, "kind": "search",   // search | read_url | read_source | extract | write | done | error
  "text": "检索「工业软件 SaaS 竞品 融资」",
  "ref": { "url": "https://…", "source_id": null, "page": null }, "ts": "…" }
```

## 2. 范本库与模板

### 2.1 范本库总览
`GET /library`
→ `{"advice": {"template": Template|null, "samples": [Sample]}, "dd": {…}}`

### 2.2 上传范本（可分批、可多文件）
`POST /samples`（multipart：`type`=advice|dd，`files[]`，仅 .docx，单文件 ≤ 50MB）
→ `{"samples": [Sample]}`，解析异步，前端轮询 2.1

### 2.3 删除范本
`DELETE /samples/{sample_id}` → `data: null`（被已学习模板引用的可删，模板不受影响）

### 2.4 学习生成模板（异步）
`POST /templates/{type}/learn`，body `{"sample_ids": [3,5,8]}`（缺省=该类型全部已解析范本）
→ `data: null`；模板进入 `learning`，完成/失败经 2.1 轮询。范本数为 1 也可学习。

### 2.5 微调模板
`PUT /templates/{type}`，body `{"chapters": [{"key","title","brief"}], "style_notes"}`
→ `{"template": Template}`。`status != ready` 时返回 2041。

## 3. 报告项目

### 3.1 项目列表
`GET /projects?page=1&page_size=12` → `{"items": [Project摘要], "total": 25}`

### 3.2 新建项目
`POST /projects`，body `{"title": "云帆科技 · A 轮", "type": "advice"}`
→ `{"project": {…, "checklist": ["商业计划书 BP", "财务明细", "天眼查导出：工商信息/股权结构/涉诉记录"]}}`
对应模板未 ready → **2042**。创建即按模板章节骨架生成全部 Chapter（state=pending）。

### 3.3 项目详情
`GET /projects/{id}` → `{"project": {…摘要字段, "chapters": [{id,key,title,state,error,tbd_count}], "sources": [Source]}}`

### 3.4 删除项目
`DELETE /projects/{id}` → `data: null`（级联删章节/资料/引用/对话）

## 4. 资料库

### 4.1 上传资料（多文件）
`POST /projects/{id}/sources`（multipart `files[]`：.docx/.pdf/.xlsx/.png/.jpg，单文件 ≤ 50MB）
→ `{"sources": [Source]}`；解析异步（扫描 PDF/图片走多模态 OCR，置信度低标 `quality: "low"`）

### 4.2 添加 URL 资料
`POST /projects/{id}/sources/url`，body `{"url": "https://…"}` → `{"source": Source}`

### 4.3 资料列表 / 删除 / 原文件
`GET /projects/{id}/sources` → `{"sources": [Source]}`
`DELETE /projects/{id}/sources/{sid}` → `data: null`
`GET /projects/{id}/sources/{sid}/file` → 原文件流（预览用）

### 4.4 影响分析（增量更新第一步）
`POST /projects/{id}/sources/{sid}/impact`
→ `{"affected": [{"chapter_id": 22, "title": "四、竞争格局", "reason": "新资料含竞对融资信息"}]}`
仅对已有成稿章节有意义；随后用 5.1 的 `chapter_ids` 发起更新。

## 5. 研究与生成（异步队列）

### 5.1 发起研究 / 重研究 / 增量更新
`POST /projects/{id}/research`，body `{"chapter_ids": [22,25]}`（缺省=全部非 done 章节）
→ `{"enqueued": [22,25]}`
- 章节已在队列/研究中 → 该章跳过（不报错，响应不含它）
- 命中「有未保存编辑」语义由前端本地判断并先行确认（**2046** 预留给后端兜底校验，body 加 `"confirm": true` 跳过）
- 入队自动解除配额暂停（同 ai-videos 语义）

### 5.2 取消队列
`POST /projects/{id}/queue/cancel` → `{"cancelled": 3}`（研究中的跑完为止）

### 5.3 状态轮询（含研究进度流增量）
`GET /projects/{id}/status?feed_after=901`
→ ```jsonc
{ "status": "researching",
  "queue": { "pending": 2, "running": 1, "paused": false, "paused_reason": null },
  "chapters": [ { "id": 21, "state": "done", "tbd_count": 1, "version": 4, "error": null } ],
  "tbd_count": 2,
  "feed": [FeedEvent]        // id > feed_after 的增量，最多 100 条
}
```

## 6. 章节与编辑

### 6.1 章节详情
`GET /projects/{id}/chapters/{cid}` → `{"chapter": Chapter详情}`

### 6.2 手动编辑段落
`PUT /projects/{id}/chapters/{cid}/paragraphs/{pid}`，body `{"text": "…（可含既有 ⟦c:x⟧/⟦tbd:x⟧ 标记）"}`
→ `{"chapter": Chapter详情}`；删除标记即移除对应引用关联。章节 researching/updating → **2044**

### 6.3 段落重写（同步，Agent 直接落稿）
`POST /projects/{id}/chapters/{cid}/paragraphs/{pid}/rewrite`，body `{"instruction": "更简洁，补一句与竞品的对比"}`
→ `{"chapter": Chapter详情}`；重写段只允许沿用本章既有引用（P0 不触发新检索，未知标记剔除）。章节忙 → **2044**

### 6.4 待补充处理
`POST /projects/{id}/tbds/{tid}/resolve`，body `{"value": "约 12-15 亿元（人工提供）"}`
→ `{"chapter": Chapter详情}`；正文 ⟦tbd⟧ 原位替换为 value，citation 记 `source_type: "manual"`

## 7. Agent 对话

### 7.1 历史
`GET /projects/{id}/chat?limit=50` → `{"messages": [{"id","role","content","chapter_id","updated_chapter_ids",ts}]}`

### 7.2 发送（同步，可直接改稿）
`POST /projects/{id}/chat`，body `{"message": "第八章风险讲得太轻了，补充客户集中度风险", "chapter_id": 26}`
→ `{"reply": "已补充：前五大客户营收占比 61%⟦c:188⟧ …", "updated_chapter_ids": [26]}`
被改章节 version+1，前端按 updated_chapter_ids 重拉 6.1。目标章节忙 → **2044**

## 8. 导出

### 8.1 生成 Word（同步）
`POST /projects/{id}/export`
- 存在未 resolve 的 tbd → **2045**，`data: {"pending": [{"tbd_id","chapter_id","reason"}]}`
- 成功 → `{"download_url": "/api/v1/invest-reports/projects/{id}/download"}`
- 产物为**干净稿**：无引用角标、无参考资料清单，样式按模板（标题层级/字体/表格）

### 8.2 下载
`GET /projects/{id}/download` → .docx 文件流（无成稿 → 2041）

## 9. 异步与轮询约定

- 范本解析、模板学习、资料解析、章节研究均为异步；前端统一 3s 轮询（2.1 / 3.3 / 5.3）
- 章节状态机：`pending → researching → done | failed`；成稿后被增量更新标 `stale → updating → done`
- 失败单章重试（5.1 传该章 id），不连坐
- `IR_UPSTREAM_QUOTA` → 队列全局暂停，`status.queue.paused_reason` 透出；新入队自动恢复
