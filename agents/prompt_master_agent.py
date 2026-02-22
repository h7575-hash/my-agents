"""PromptMasterAgent - プロンプト管理・FB反映エージェント"""

from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel

from workflows.news_workflow.state import (
    NewsWorkflowState,
    PromptBundle,
    UserProfile,
    FeedbackContext,
    MemoryContext,
)
from utils.loaders import PromptLoader


class PromptMasterAgent:
    """
    プロンプトマスター: プロンプト収集・管理・更新、FB反映
    
    再利用性:
        - テンプレートをドメイン別に差し替え可能
        - FBルールをカスタマイズ可能
    """
    
    def __init__(
        self,
        model: BaseChatModel,
        workflow: str = "news_workflow",
        prompts_dir: Optional[str] = None,
        use_dynamic_generation: bool = False,
    ):
        self.model = model
        self.workflow = workflow
        self.prompt_loader = PromptLoader(prompts_dir) if prompts_dir else PromptLoader()
        self.use_dynamic_generation = use_dynamic_generation
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """プロンプトバンドルを生成"""
        
        user_profile = state["user_profile"]
        feedback_context = state["feedback_context"]
        memory_context = state["memory_context"]
        retry_count = state.get("retry_count", 0)
        
        # FB・記憶を反映したプロンプト生成
        prompt_bundle = self._generate_prompts(
            user_profile=user_profile,
            feedback_context=feedback_context,
            memory_context=memory_context,
            retry_count=retry_count,
        )
        
        return {"prompt_bundle": prompt_bundle}
    
    def _generate_prompts(
        self,
        user_profile: UserProfile,
        feedback_context: FeedbackContext,
        memory_context: MemoryContext,
        retry_count: int,
    ) -> PromptBundle:
        """各エージェント向けプロンプトを生成"""
        
        # CollectorAgent用プロンプト
        collector_prompt = self._build_collector_prompt(
            user_profile, feedback_context, memory_context, retry_count
        )
        
        # AIOreAgent用プロンプト
        judge_prompt = self._build_judge_prompt(
            user_profile, feedback_context, memory_context
        )
        
        # NotifyAssistantAgent用プロンプト
        notify_prompt = self._build_notify_prompt(user_profile)
        
        return PromptBundle(
            collector=collector_prompt,
            judge=judge_prompt,
            notify=notify_prompt,
        )
    
    def _build_collector_prompt(
        self,
        profile: UserProfile,
        feedback: FeedbackContext,
        memory: MemoryContext,
        retry_count: int,
    ) -> str:
        """NewsCollectorAgent用プロンプト構築"""
        
        # テンプレート読み込み
        template = self.prompt_loader.load(self.workflow, "collector")
        
        # 優先トピック整形
        priority_topics = ""
        if feedback.topic_priorities:
            sorted_topics = sorted(
                feedback.topic_priorities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            if sorted_topics:
                lines = [f"- {topic} (重要度: {score:.2f})" for topic, score in sorted_topics]
                priority_topics = "\n".join(lines)
        
        # 失敗理由整形
        failure_reasons = ""
        if retry_count > 0 and memory.failure_reasons:
            lines = [f"- {reason}" for reason in memory.failure_reasons[-3:]]
            failure_reasons = "\n".join(lines) + "\n\n上記を改善した収集を行ってください。"
        
        # テンプレート埋め込み
        return self.prompt_loader.format(
            template,
            topics=", ".join(profile.topics),
            exclude_keywords=", ".join(profile.exclude_keywords),
            language=profile.language,
            region=profile.region,
            priority_topics=priority_topics if priority_topics else "（なし）",
            failure_reasons=failure_reasons if failure_reasons else "（なし）",
        )
    
    def _build_judge_prompt(
        self,
        profile: UserProfile,
        feedback: FeedbackContext,
        memory: MemoryContext,
    ) -> str:
        """AIOreAgent用プロンプト構築"""
        
        # テンプレート読み込み
        template = self.prompt_loader.load(self.workflow, "judge")
        
        # 高評価理由整形
        liked_reasons = ""
        if feedback.liked_reasons:
            lines = [f"- {reason}" for reason in feedback.liked_reasons[-5:]]
            liked_reasons = "\n".join(lines)
        
        # 低評価理由整形
        disliked_reasons = ""
        if feedback.disliked_reasons:
            lines = [f"- {reason}" for reason in feedback.disliked_reasons[-5:]]
            disliked_reasons = "\n".join(lines)
        
        # トピック傾向整形
        topic_trends = ""
        if memory.topic_trends:
            lines = [f"- {topic}: {trend:.2f}" for topic, trend in list(memory.topic_trends.items())[:5]]
            topic_trends = "\n".join(lines)
        
        # テンプレート埋め込み
        return self.prompt_loader.format(
            template,
            primary_topic=profile.topics[0] if profile.topics else "ニュース",
            liked_reasons=liked_reasons if liked_reasons else "（なし）",
            disliked_reasons=disliked_reasons if disliked_reasons else "（なし）",
            topic_trends=topic_trends if topic_trends else "（なし）",
        )
    
    def _build_notify_prompt(self, profile: UserProfile) -> str:
        """NotifyAssistantAgent用プロンプト構築"""
        
        # テンプレート読み込み
        template = self.prompt_loader.load(self.workflow, "notify")
        
        # テンプレート埋め込み
        return self.prompt_loader.format(
            template,
            primary_topic=profile.topics[0] if profile.topics else "ニュース",
        )
    
    def _generate_prompt_with_llm(
        self,
        target_agent: str,
        profile: UserProfile,
        feedback: FeedbackContext,
        memory: MemoryContext,
    ) -> str:
        """LLMを使ってプロンプトを動的に生成（オプション機能）
        
        use_dynamic_generation=True の場合に使用
        FBと記憶を元にLLMがプロンプトを最適化
        """
        
        # プロンプトマスター用テンプレート読み込み
        master_template = self.prompt_loader.load(self.workflow, "prompt_master")
        
        # FB・記憶整形
        liked_reasons = "\n".join([f"- {r}" for r in feedback.liked_reasons[-5:]]) if feedback.liked_reasons else "（なし）"
        disliked_reasons = "\n".join([f"- {r}" for r in feedback.disliked_reasons[-5:]]) if feedback.disliked_reasons else "（なし）"
        failure_reasons = "\n".join([f"- {r}" for r in memory.failure_reasons[-5:]]) if memory.failure_reasons else "（なし）"
        
        # プロンプトマスターへの指示
        master_prompt = self.prompt_loader.format(
            master_template,
            workflow=self.workflow,
            topics=", ".join(profile.topics),
            exclude_keywords=", ".join(profile.exclude_keywords),
            language=profile.language,
            region=profile.region,
            liked_reasons=liked_reasons,
            disliked_reasons=disliked_reasons,
            failure_reasons=failure_reasons,
            target_agent=target_agent,
        )
        
        # LLMでプロンプト生成
        response = self.model.invoke([HumanMessage(content=master_prompt)])
        
        return response.content
