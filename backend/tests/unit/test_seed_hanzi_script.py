"""scripts/seed_hanzi.py 能否不带 `-m` 直接以脚本方式运行（B1 修复的回归锁）。

修复前：`python scripts/seed_hanzi.py` 会 `ModuleNotFoundError: No module named
'app'`——直接执行一个脚本文件时，Python 只把脚本所在目录（scripts/）而不是
backend/ 根目录塞进 sys.path[0]，只能改用 `python -m scripts.seed_hanzi`
（让 `app` 因为当前工作目录在 backend/ 而恰好可 import）。修复后脚本头部
用 `Path(__file__).resolve().parent.parent` 主动把 backend/ 根目录插进
sys.path，不再依赖调用方式或当前工作目录。

用真实子进程执行脚本文件本身（而非依赖 pytest 进程已经建立好的 sys.path），
且工作目录故意设成与 backend/ 无关的目录，逼出"只能靠脚本自己兜底"的场景。
用 `runpy.run_path(..., run_name="not_main")` 让 `if __name__ == "__main__":`
守卫不触发，只跑到模块顶层的 import 就停——不需要真的连数据库，跑得快、
不依赖外部服务，同时精确复现本次要锁的那段行为（import 解析），不锁无关的
业务逻辑。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_SCRIPT = BACKEND_ROOT / "scripts" / "seed_hanzi.py"


def _run_seed_script_imports(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(
        [
            sys.executable,
            "-c",
            f"import runpy; runpy.run_path(r'{SEED_SCRIPT}', run_name='not_main')",
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_seed_hanzi_importable_as_direct_script_regardless_of_cwd(tmp_path):
    """工作目录与 backend/ 无关时，脚本仍能靠自己的 sys.path 兜底找到 app.*。"""
    result = _run_seed_script_imports(cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr


def test_seed_hanzi_importable_from_backend_root():
    """从 backend/ 直接跑（文档里给的用法）同样成立。"""
    result = _run_seed_script_imports(cwd=BACKEND_ROOT)

    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr
