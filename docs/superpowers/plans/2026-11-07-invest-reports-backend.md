# invest-reports 后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现投资报告 Agent 的完整后端：范本学习、项目/资料管理、Pydantic AI 逐章研究（带溯源与进度流）、精修编辑、对话改稿、Word 导出。

**Architecture:** 沿用仓库 DDD 分层与 ai-videos 的成熟模式——外层「确定性章节研究队列」（逐章异步、失败不连坐、配额暂停、feed 进度流），内层 Pydantic AI Agent（研究写作 / 对话修改，typed tools + 结构化输出）；章节正文以 JSONB（paragraphs/citations/tbds + 内联标记 ⟦c:id⟧/⟦tbd:id⟧）存于章节行；全部 LLM/检索走 OpenRouter 单 Key，无 Key 整体回落 Mock。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic；pydantic-ai（新增依赖，infrastructure 层）；python-docx（新增，解析范本+导出）；pypdf（已有）；openpyxl（新增）；httpx + MockTransport / pydantic-ai TestModel 做单测。

**Spec:** docs/prd/invest-reports.md + docs/api/invest-reports.md（接口契约以 API 文档为准）

## Global Constraints

- 统一 `/api/v1/invest-reports` 前缀与 `{code,data,message}` 包装；错误码常量进 `domain/errors.py`：IR_PARAM_INVALID=2040、IR_NOT_FOUND=2041、IR_TEMPLATE_NOT_READY=2042、IR_SOURCE_UNPARSEABLE=2043、IR_CHAPTER_BUSY=2044、IR_EXPORT_BLOCKED=2045、IR_CONFIRM_REQUIRED=2046、IR_UPSTREAM_FAILED=5001、IR_UPSTREAM_QUOTA=5002、IR_EXPORT_FAILED=5004
- DDD：domain 无 FastAPI/infrastructure 依赖；routers 只校验+调 service；事务边界在 service；`pydantic-ai` 只出现在 infrastructure
- OpenRouter 单 Key（`OPENROUTER_API_KEY`）；上游 401/402/429+credit → IR_UPSTREAM_QUOTA（队列全局暂停，新入队自动恢复）；未配 Key → MockIrAgent 全链路可跑
- 文件上传 ≤50MB/个；范本仅 .docx；资料 .docx/.pdf/.xlsx/.png/.jpg
- 导出为干净稿：无角标、无参考清单；未 resolve 的 tbd → 2045 带 pending 清单
- 每任务收尾 `uv run pytest tests/unit tests/smoke -q` 全绿再 commit；OpenAPI 快照随 schema 变更重生成（`sort_keys` 版命令见 tests/smoke/test_openapi_snapshot.py 文档串）

## Review Focus

1. Agent 返回的引用编号越界/缺失（如正文含 ⟦c:5⟧ 但只给了 3 条引用）→ 服务端重映射时丢弃无效标记并记 warning，不崩 —— 测试在 Task 2（remap 纯函数）。
2. 研究中途上游 402 → 当前章回退 pending、队列全局暂停、`status.queue.paused_reason` 透出；重新 research 自动恢复 —— 测试在 Task 6。
3. 扫描 PDF（提取文本为空）→ 自动走多模态解析路径且 `quality="low"`，而不是落一个空文本的 "ready" 资料 —— 测试在 Task 4。
4. 删除资料后，既有章节中 `source_type=file` 且指向该资料的引用仍可展示（title/quote 快照自包含），文件预览 404 —— 测试在 Task 5（引用自包含断言）。
5. 对话指定的章节处于 researching → 2044 而不是并发写稿互踩 —— 测试在 Task 7。

---

### Task 1: 领域模型 + 迁移 0009 + 仓储/UoW

**Files:**
- Create: `backend/app/domain/models/invest_report.py`、`backend/app/domain/repositories/invest_report.py`、`backend/app/infrastructure/repositories/invest_report_repo.py`、`backend/app/alembic/versions/0009_invest_reports.py`
- Modify: `backend/app/domain/errors.py`（新增 IR_* 常量）、`backend/app/domain/repositories/uow.py` + `backend/app/infrastructure/repositories/uow.py`（挂 5 个仓储属性）
- Test: `backend/tests/unit/test_domain_invest_report.py`

**Interfaces（Produces）:**
- 实体（SQLAlchemy Mapped，表名前缀 ir_）：
  - `IrSample(id, type, filename, file_path, parse_state, parsed_text(Text), uploaded_at)`
  - `IrTemplate(id, type UNIQUE, status, chapters JSONB, style_notes Text, learned_from JSONB, error, updated_at)`
  - `IrProject(id, title, type, created_at, updated_at)`
  - `IrChapter(id, project_id FK cascade, key, title, order_index, state, error, version, content JSONB NOT NULL DEFAULT '{"paragraphs":[],"citations":[],"tbds":[]}')`
  - `IrSource(id, project_id FK cascade, kind, filename, url, file_path, parse_state, quality, parsed_text Text, uploaded_at)`
  - `IrChatMessage(id, project_id FK cascade, role, content Text, chapter_id, updated_chapter_ids JSONB, created_at)`
- 常量：`ChapterState(StrEnum): PENDING/RESEARCHING/DONE/FAILED/STALE/UPDATING`；`ParseState: PENDING/PARSING/READY/FAILED`；`TemplateStatus: NONE/LEARNING/READY/FAILED`；`REPORT_TYPES=("advice","dd")`
- `IrChapter` 状态机方法：`mark_researching()`（PENDING/FAILED/STALE/DONE→RESEARCHING 或 STALE→UPDATING；RESEARCHING/UPDATING 时抛 ParamException(IR_CHAPTER_BUSY)）、`mark_done(content: dict)`（落 content、version+1、清 error）、`mark_failed(error)`、`mark_pending()`（配额回退）、`mark_stale()`
- 纯函数：`derive_project_status(chapters, queue_active) -> str`（draft/researching/partial_failed/completed，语义同 ai-videos）；`unresolved_tbds(content) -> list[dict]`；`resolve_tbd_in_content(content, tbd_id, value) -> dict`（⟦tbd:id⟧ 原位替换为 value+新 manual 引用标记，返回新 content，找不到抛 ParamException(IR_NOT_FOUND)）；`strip_markers(text) -> str`
- 仓储 Protocol + 实现：`ir_samples/ir_templates/ir_projects/ir_chapters/ir_sources/ir_chats`，方法照抄 ai-videos 仓储风格（find_by_id/list_by_*/add/delete/delete_by_project；templates 另有 `find_by_type`）
- 迁移 0009 建 6 表，`down_revision="0008_av_multiref_video_prompt"`

- [ ] **Step 1: 写失败测试**：chapter 状态机（busy 抛 2044、done 落 content 且 version+1、配额回退 pending）；`derive_project_status` 四态；`resolve_tbd_in_content`（原位替换 + manual 引用 + 未命中抛错）；`strip_markers`
- [ ] **Step 2: RED 确认** → **Step 3: 实现**（错误码/实体/纯函数/仓储/UoW/迁移）→ **Step 4: `uv run alembic upgrade head` 并 psql 验表** → **Step 5: 全量单测+冒烟绿** → **Step 6: Commit**（`feat(invest-reports): 领域模型与迁移 0009`）

### Task 2: 应用层端口 + 内容重映射 + Mock Agent

**Files:**
- Modify: `backend/app/application/ports.py`
- Create: `backend/app/application/services/ir_content.py`（纯函数）、`backend/app/infrastructure/ai/ir_agent_mock.py`
- Test: `backend/tests/unit/test_ir_content.py`

**Interfaces（Produces）:**
- Agent 产出 DTO（pydantic，放 `application/dto/invest_report.py` 一并建）：
  - `DraftCitation(source_type, title, url, source_id, page, quote, captured_at)`
  - `DraftTbd(reason)`
  - `ChapterDraft(paragraphs: list[str], citations: list[DraftCitation], tbds: list[DraftTbd])` —— 段落文本用**局部序号**标记 ⟦c:N⟧/⟦tbd:N⟧（N 从 1 计，指向本次 draft 的列表下标）
  - `TemplateDraft(chapters: list[{key,title,brief}], style_notes: str)`
  - `ChatOutcome(reply: str, updated: bool, paragraphs: list[str] | None)`（updated 时 paragraphs 为目标章节新全文，沿用既有全局 ⟦c:id⟧ 标记）
  - `ImpactDraft(items: list[{chapter_key, reason}])`
- `IrAgent(Protocol)`：
  - `async learn_template(samples_text: list[str], report_type: str) -> TemplateDraft`
  - `async research_chapter(ctx: ResearchContext, on_event: Callable[[str kind, str text, str|None url], None]) -> ChapterDraft`（`ResearchContext(project_title, report_type, chapter_key, chapter_title, chapter_brief, style_notes, sources: list[SourceDoc(id, name, text)], prior_chapter_titles)`）
  - `async rewrite_paragraph(paragraph_text, instruction, citations_catalog: list[dict]) -> str`（只允许沿用全局 ⟦c:id⟧）
  - `async chat(ctx_summary: str, chapter: dict | None, message: str) -> ChatOutcome`
  - `async analyze_impact(source_text: str, done_chapters: list[{key,title}]) -> ImpactDraft`
  - `async parse_image(image_bytes: bytes, hint: str) -> str`（多模态 OCR/描述，供解析器用）
- 纯函数 `ir_content.remap_draft(draft: ChapterDraft, id_alloc: Callable[[], int]) -> dict`：把局部 ⟦c:N⟧/⟦tbd:N⟧ 重映射为全局 id 的 content JSON（paragraphs:[{id:"p1"..}], citations 带 n 序号, tbds）；**越界/未知标记直接移除并继续**
- `MockIrAgent`：确定性产物（2 段正文 + 1 web 引用 + 1 file 引用 + 1 tbd；模板 5 章；chat 指定章节时 updated=True）

- [ ] **Step 1: 写失败测试**：remap 正常映射（全局 id 连续、n 从 1 排）/越界标记被移除/缺引用列表时段落保留纯文本；Mock agent 各方法返回形状
- [ ] **Step 2: RED** → **Step 3: 实现** → **Step 4: 全量绿** → **Step 5: Commit**（`feat(invest-reports): Agent 端口、内容重映射与 Mock`）

### Task 3: 配置/依赖/存储装配

**Files:**
- Modify: `backend/app/config.py`（`IR_DATA_DIR="data/invest-reports"`、`IR_LLM_MODEL="google/gemini-3.8-flash"`、`IR_SEARCH_MODEL="google/gemini-3.8-flash:online"`）、`backend/requirements.txt`（`pydantic-ai-slim[openai]`、`python-docx`、`openpyxl`）、`backend/app/interfaces/api/deps.py`（`get_ir_storage()` 复用 `FsAvStorage(Path(settings.IR_DATA_DIR))`）
- Create: `backend/app/infrastructure/ai/ir_agent_factory.py`（`get_ir_agent()` 单例：有 OPENROUTER_API_KEY → PydanticIrAgent（Task 8 实现，先留 import 延迟）否则 MockIrAgent；`set_ir_agent()` 测试替换——照抄 av_client 工厂模式）
- Test: `backend/tests/unit/test_ir_agent_factory.py`

- [ ] **Step 1: 失败测试**（无 Key → MockIrAgent；set/reset 单例）→ **Step 2: RED** → **Step 3: 实现 + `uv pip install -r requirements.txt`** → **Step 4: 全量绿** → **Step 5: Commit**

### Task 4: 文档解析器

**Files:**
- Create: `backend/app/infrastructure/ir_parsers.py`
- Test: `backend/tests/unit/test_ir_parsers.py`（用 python-docx/openpyxl 现场生成临时测试文件）

**Interfaces（Produces）:**
- `async parse_document(path: Path, agent: IrAgent) -> tuple[str, str]`：返回 `(text, quality)`；按扩展名分发——.docx→python-docx 全文段落+表格；.xlsx→openpyxl 逐 sheet 转「sheet 名 + CSV 行」文本；.pdf→pypdf 逐页提取，**全文 <50 字时**视为扫描件→`agent.parse_image`（逐页渲染不做，直接整文件字节传多模态）且 quality="low"；.png/.jpg→`agent.parse_image` 且 quality="low"；不支持扩展名抛 `ParamException(IR_SOURCE_UNPARSEABLE)`
- `async parse_url(url: str) -> str`：httpx GET（10s 超时）+ 去 script/style 的朴素正文抽取；失败抛 ServerException(IR_UPSTREAM_FAILED)

- [ ] **Step 1: 失败测试**：docx/xlsx 真实小文件解析出关键字；空文本 pdf → 调 fake agent.parse_image 且 quality low；未知扩展 → 2043
- [ ] **Step 2: RED** → **Step 3: 实现** → **Step 4: 全量绿** → **Step 5: Commit**

### Task 5: 范本库与项目/资料服务 + 路由（第一批接口）

**Files:**
- Create: `backend/app/application/services/ir_library_service.py`、`backend/app/application/services/ir_project_service.py`（本任务只做项目/资料部分）、`backend/app/interfaces/api/schemas/invest_reports.py`、`backend/app/interfaces/api/routers/invest_reports.py`（§2/§3/§4 接口）
- Modify: `backend/app/application/dto/invest_report.py`（出参 DTO：SampleOut/TemplateOut/LibraryOut/ProjectSummaryOut/ProjectDetailOut/SourceOut，`file_url` 风格同 ai-videos）、`backend/app/main.py`（挂路由）、deps.py（两个 service 工厂）
- Test: `backend/tests/unit/test_ir_library_service.py`、`backend/tests/unit/test_ir_project_service.py`（fake uow/agent/storage/runner，风格照抄 test_av_service）

**Interfaces（Produces）:**
- `IrLibraryService(uow, agent, storage, runner, uow_factory)`：`get_library()`；`upload_samples(type, files:[(filename, bytes)])`（校验 .docx/50MB→存盘→行 state=parsing→`runner.spawn` 后台解析落 parsed_text/ready|failed）；`delete_sample(id)`；`learn(type, sample_ids|None)`（无就绪范本→2040；置 learning 后 spawn：聚合 parsed_text（每份截前 20k 字）→`agent.learn_template`→ready/failed）；`update_template(type, chapters, style_notes)`（非 ready→2041）
- `IrProjectService`（本批）：`list_projects()/create_project(title,type)`（模板非 ready→**2042**；按模板 chapters 建全部 IrChapter，order_index 从 1；checklist 常量=API 文档三项）`/get_project(id)/delete_project(id)`；`list_sources/upload_sources/add_url_source/delete_source/source_file_path(id,sid)`；`analyze_impact(id,sid)`（resolve chapter_key→id，只报 done/stale 章）
- 路由路径与响应形状严格对 docs/api/invest-reports.md §2-4；multipart 用 `UploadFile`

- [ ] **Step 1: 失败测试**（学习门槛 2040、create_project 模板未 ready→2042、上传后缀/大小校验、删除级联、影响分析只含 done 章；「删资料后引用自包含」断言在 Task 7）
- [ ] **Step 2: RED** → **Step 3: 实现** → **Step 4: 全量绿（冒烟快照先不动，Task 9 统一重生成，故本任务临时允许 smoke 红？否——路由挂载即变快照：**本任务顺手重生成快照**）** → **Step 5: Commit**

### Task 6: 章节研究队列

**Files:**
- Create: `backend/app/application/services/ir_queue.py`
- Modify: deps.py（`get_ir_queue()` 单例，注入 uow_factory/agent/runner）
- Test: `backend/tests/unit/test_ir_queue.py`（MemUow 风格照抄 test_av_queue）

**Interfaces（Produces）:**
- `IrResearchQueue(uow_factory, agent, runner, concurrency=1, poll_interval=1.0)`：
  - `enqueue(project_id, chapter_ids: list[int]) -> list[int]`（已在队/研究中跳过；入队解除暂停；章节行先 mark_researching/updating 并 commit，再入内存 FIFO）
  - `cancel_project(project_id) -> int`（排队中回退 pending）
  - `counts(project_id) -> (pending, running)`、`paused/paused_reason`
  - `feed(project_id, after: int) -> list[FeedEvent dict]`（**内存环形缓冲**，每项目保留最近 500 条，id 进程内单调递增；重启丢失可接受——Ruling 已在 spec 精神内：feed 是过程性展示）
  - 执行：uow 内读齐 ResearchContext（项目、章节、全部 ready 资料的 parsed_text 截断 15k/份、模板 style_notes、已完成章标题）→**关 uow**→`agent.research_chapter(ctx, on_event→feed)`→`remap_draft`（id 分配器用 uow 外计数+落库时二次校正：直接以 `IrCitationSeq`？否——全局 id 用 `genId=时间戳序`？**Pin：citation/tbd 的全局 id 在 remap 时由 `itertools.count(start=章节id*100000)` 生成**，项目内唯一且无需 DB 序列）→新 uow `mark_done(content)`；quota → mark_pending + 全局暂停；其他异常 → mark_failed
- FeedEvent dict：`{id, chapter_id, kind, text, ref:{url,source_id,page}|None, ts}`

- [ ] **Step 1: 失败测试**：成功链（状态流转+feed 事件追加+content 落库）；失败不连坐；quota 暂停+回退 pending+再入队恢复；重复入队跳过；cancel 回退；**agent 调用发生在 uow 关闭后**（沿用 av 的 open-flag 测试手法）
- [ ] **Step 2: RED** → **Step 3: 实现** → **Step 4: 全量绿** → **Step 5: Commit**

### Task 7: 研究/状态/编辑/对话接口（第二批）

**Files:**
- Modify: `ir_project_service.py`（+research/cancel/status/chapter/edit/rewrite/tbd/chat 方法）、`invest_reports.py` 路由（§5/§6/§7）、schemas、DTO（ChapterDetailOut/StatusOut/FeedEventOut/ChatMessageOut）
- Test: 扩展 `test_ir_project_service.py`

**Interfaces（Produces）:**
- `start_research(id, chapter_ids|None, confirm=False)`（缺省=全部非 done）→ `{enqueued}`；`cancel_queue`；`get_status(id, feed_after)`（含 queue/chapters/tbd_count/feed）
- `get_chapter(id,cid)`；`update_paragraph(id,cid,pid,text)`（busy→2044；删标记=移除关联：重算 content.citations/tbds 为正文仍引用的子集）；`rewrite_paragraph(id,cid,pid,instruction)`（busy→2044；调 `agent.rewrite_paragraph`，产物仅允许既有 ⟦c:id⟧，未知标记剔除）；`resolve_tbd(id,tid,value)`（复用 Task 1 纯函数）
- `list_chat/send_chat(id,message,chapter_id)`：目标章 busy→2044；`agent.chat` updated 时以 ChatOutcome.paragraphs 整章替换（引用子集重算同上）、version+1；user/assistant 两条消息落库
- Review Focus #4 测试在此：构造含 file 引用的 content → 删除资料 → get_chapter 引用仍完整返回

- [ ] **Step 1: 失败测试**（上述每个 2044/子集重算/整章替换/tbd 解决后 content 变化）→ **Step 2: RED** → **Step 3: 实现** → **Step 4: 全量绿** → **Step 5: Commit**

### Task 8: Pydantic AI 真实 Agent + 导出

**Files:**
- Create: `backend/app/infrastructure/ai/ir_agent_pydantic.py`、`backend/app/infrastructure/ir_export.py`
- Modify: `ir_agent_factory.py`（接入真实实现）、`ir_project_service.py`（export 方法）、路由 §8
- Test: `backend/tests/unit/test_ir_agent_pydantic.py`（pydantic-ai `TestModel`/`FunctionModel` 驱动，不走网络）、`backend/tests/unit/test_ir_export.py`

**Interfaces（Produces）:**
- `PydanticIrAgent(api_key, base_url, model, search_model, transport=None)`：
  - 模型装配：`OpenAIChatModel(model, provider=OpenAIProvider(base_url, api_key))`（pydantic-ai 的 OpenAI 兼容接法）
  - 研究 Agent：`Agent(model, output_type=ChapterDraft, deps_type=ResearchDeps)`，tools：`web_search(query)`（httpx 直调 OpenRouter chat `search_model`，解析 message.annotations 的 url_citation 列表 → [{title,url,snippet}]；**显式工具，每次调用触发 on_event('search',…) 与逐条 read 事件**）、`read_url(url)`（Task 4 的 parse_url，截 8k）、`query_sources(keyword)`（在 deps.sources 文本里朴素检索返回片段+来源名）；system prompt 固定要求：只写有依据的数据、输出局部 ⟦c:N⟧/⟦tbd:N⟧ 标记、citations 必填 quote 与 captured_at
  - 其余方法（learn_template/rewrite/chat/impact/parse_image）为单次结构化调用（`Agent(..., output_type=对应 DTO)` 或多模态消息）
  - 事件桥：Agent 工具内通过 deps 回调 on_event；研究开始/成稿各发一条 write/done
  - 错误收口：401/402/429+credit → ServerException(IR_UPSTREAM_QUOTA)，其余 → IR_UPSTREAM_FAILED
- `ir_export.build_docx(project_title, report_type, chapters: list[{title, paragraphs:[str]}]) -> bytes`：python-docx，标题1=报告名，各章 Heading 2 + 正文段（**传入前已 strip_markers**）；字体设置中文宋体/西文 Calibri 即可（P0 不还原范本样式，PRD 样式映射降级为标题层级——在计划此处显式降级，导出含模板样式为后续增强）
- `export(id)`：未 resolve tbd→2045(data.pending)；成稿章节数 0→2041；生成 bytes 存 `projects/{id}/final.docx`→`{download_url}`；`GET /projects/{id}/download` FileResponse
- Review Focus #1 的 remap 容错已在 Task 2；此处补 TestModel 驱动的「agent 输出越界标记→service 落库不崩」集成式单测

- [ ] **Step 1: 失败测试**（TestModel 驱动 research 返回 ChapterDraft 形状；web_search 用 MockTransport 断言 annotations 解析与 Key 不发给第三方——复用 av 下载不带 Key 的手法；export：干净稿无 ⟦ 标记、tbd 未清 2045）
- [ ] **Step 2: RED** → **Step 3: 实现** → **Step 4: 全量绿** → **Step 5: Commit**

### Task 9: 收尾——OpenAPI 快照、docs 对齐、lint 清零

- [ ] 重生成 `tests/smoke/openapi_baseline.json`（文档串里的 sort_keys 命令）；`docs/api/invest-reports.md` 与实现差异回写（若实现中有 Ruling 偏差）
- [ ] `uv run pytest -q` 全绿 + `cd frontend && npx tsc -b --noEmit`（防 DTO 字段名跑偏——前端类型就是契约镜像）
- [ ] Commit（`feat(invest-reports): 后端收尾——快照与文档对齐`）

### Task 10: 真机冒烟（需 OPENROUTER_API_KEY，花费 <$1）

- [ ] 起后端（VITE 不动，curl 驱动）：现场用 python-docx 生成 2 份迷你范本 docx → 上传 → learn（真 LLM）→ 建项目 → 传一份迷你 BP docx + 一条 URL 资料 → research 全部章节（真检索+写作，项目模板裁到 3 章内控费：learn 后用 PUT /templates 微调成 3 章）→ 轮询 status 看 feed → 校验 content 引用非空、tbd 行为 → resolve tbd → export → 下载 docx 用 python-docx 读回断言含章节标题、不含 ⟦ 标记
- [ ] 结果与花费记录进 ledger；发现的接口形状问题当场修（带测试）
