"""週次ニュースエージェント - 実行エントリーポイント"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils.model_helper import build_model
from utils.loaders import DataLoader
from workflows.news_workflow.scheduler import WeeklyNewsScheduler


def main() -> int:
    """週次ニュースエージェントのメインエントリーポイント"""
    
    try:
        load_dotenv()
        
        # データローダー初期化
        data_loader = DataLoader()
        
        # ユーザプロファイル読み込み
        user_profile = data_loader.get_user_profile("default_user")
        if not user_profile:
            print("エラー: ユーザプロファイルが見つかりません", file=sys.stderr)
            return 1
        
        # ワークフロー設定読み込み
        workflow_config = data_loader.get_workflow_config()
        
        # モデル初期化
        model = build_model()
        
        # スケジューラ初期化
        scheduler = WeeklyNewsScheduler(
            model=model,
            max_retries=workflow_config.get("max_retries", 2),
        )
        
        # 週次実行
        result = scheduler.run_weekly(
            user_id="default_user",
            topics=user_profile["topics"],
            exclude_keywords=user_profile.get("exclude_keywords", []),
            lookback_days=workflow_config.get("lookback_days", 7),
        )
        
        print("\n=== 実行結果 ===")
        print(f"ステータス: {result['status']}")
        print(f"通知: {result.get('notification_status')}")
        print(f"レポート: {result.get('report_path')}")
        
        return 0 if result["status"] == "success" else 1
        
    except Exception as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
