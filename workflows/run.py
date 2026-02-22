"""workflows統合実行ランナー."""

import argparse
import importlib
import sys
from pathlib import Path


# プロジェクトルートを import パスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


WORKFLOW_ENTRYPOINTS = {
    "news": "workflows.news_workflow.run:main",
}


def _run_workflow(name: str) -> int:
    entrypoint = WORKFLOW_ENTRYPOINTS.get(name)
    if not entrypoint:
        print(f"未対応のworkflowです: {name}", file=sys.stderr)
        print(f"利用可能: {', '.join(sorted(WORKFLOW_ENTRYPOINTS.keys()))}", file=sys.stderr)
        return 1

    module_name, func_name = entrypoint.split(":")
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    return int(func())


def main() -> int:
    parser = argparse.ArgumentParser(description="workflows統合実行ランナー")
    parser.add_argument("workflow", choices=sorted(WORKFLOW_ENTRYPOINTS.keys()))
    args = parser.parse_args()
    return _run_workflow(args.workflow)


if __name__ == "__main__":
    raise SystemExit(main())

