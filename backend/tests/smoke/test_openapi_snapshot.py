"""OpenAPI 基线快照测试。

锁定 app.openapi() 的完整输出。重构阶段任何一次搬运如果不小心改变了
请求/响应 schema、路径参数、tag 等对外契约，这里会先炸。

基线生成命令（在 backend/ 目录下）：
    .venv/bin/python -c "import json; from app.main import app; \
        print(json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True))" \
        > tests/smoke/openapi_baseline.json
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def test_openapi_matches_baseline():
    baseline = json.loads((Path(__file__).parent / "openapi_baseline.json").read_text())
    assert app.openapi() == baseline
