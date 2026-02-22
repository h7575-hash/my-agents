# ニュース収集トピック設定例

このファイルでは、収集したいニュースのトピックを設定します。
`data/user_profiles.json` で管理されています。

## デフォルト設定

```json
{
  "topics": ["AI", "LangGraph", "Vertex AI"],
  "exclude_keywords": ["広告", "PR", "スポンサー"]
}
```

## カスタマイズ例

### テック系全般
```json
{
  "topics": ["AI", "クラウド", "機械学習", "Python"],
  "exclude_keywords": ["広告", "求人"]
}
```

### 特定分野特化
```json
{
  "topics": ["生成AI", "GPT", "Gemini", "Claude"],
  "exclude_keywords": ["ゴシップ", "炎上"]
}
```

### 複数ユーザ管理

`user_profiles.json` に複数プロファイルを追加:

```json
{
  "user_profiles": {
    "user_tech": {
      "topics": ["AI", "クラウド"],
      "exclude_keywords": ["広告"]
    },
    "user_business": {
      "topics": ["スタートアップ", "資金調達"],
      "exclude_keywords": ["PR"]
    }
  }
}
```
