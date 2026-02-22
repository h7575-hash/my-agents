"""プロンプト・データローダー"""

import json
from pathlib import Path
from typing import Optional


class PromptLoader:
    """プロンプトテンプレートをファイルから読み込む"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
    
    def load(self, workflow: str, prompt_name: str) -> str:
        """プロンプトテンプレートを読み込む
        
        Args:
            workflow: ワークフロー名（例: "news_workflow"）
            prompt_name: プロンプト名（例: "collector"）
        
        Returns:
            プロンプトテンプレート文字列
        """
        prompt_path = self.prompts_dir / workflow / f"{prompt_name}.txt"
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"プロンプトファイルが見つかりません: {prompt_path}")
        
        return prompt_path.read_text(encoding="utf-8")
    
    def format(self, template: str, **kwargs) -> str:
        """プロンプトテンプレートに変数を埋め込む
        
        Args:
            template: プロンプトテンプレート
            **kwargs: 埋め込む変数
        
        Returns:
            変数が埋め込まれたプロンプト
        """
        return template.format(**kwargs)


class DataLoader:
    """設定データをファイルから読み込む"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
    
    def load_user_profiles(self) -> dict:
        """ユーザプロファイルを読み込む"""
        profiles_path = self.data_dir / "user_profiles.json"
        
        if not profiles_path.exists():
            raise FileNotFoundError(f"プロファイルファイルが見つかりません: {profiles_path}")
        
        with open(profiles_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """特定ユーザのプロファイルを取得"""
        profiles = self.load_user_profiles()
        return profiles.get("user_profiles", {}).get(user_id)
    
    def get_workflow_config(self) -> dict:
        """ワークフロー設定を取得"""
        profiles = self.load_user_profiles()
        return profiles.get("workflow_config", {})
