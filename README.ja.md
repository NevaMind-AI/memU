<div align="center">

![MemU バナー](assets/banner.png)

### MemU: 次世代エージェントメモリシステム

[![PyPI version](https://badge.fury.io/py/memu-py.svg)](https://badge.fury.io/py/memu-py)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/memu)
[![Twitter](https://img.shields.io/badge/Twitter-Follow-1DA1F2?logo=x&logoColor=white)](https://x.com/memU_ai)
</div>

**MemU** は、エージェントのメモリアーキテクチャをメモリ中心の視点から再設計した次世代のエージェントメモリシステムです。文脈に基づいて関連情報を知的に整理・検索する「動的に進化するデータレイヤー」として抽象化されています。適応的な検索（retrieval）とバックトラッキング機構により、最も関連性の高い情報を動的に抽出します。  
このシステムはテキスト、画像、音声などの多様なデータ型をネイティブにサポートする **Unified Multimodal Memory** アーキテクチャを採用し、統一されたメモリ表現を形成します。

公式サイト: [memu.pro](https://memu.pro/)

---

## ⭐ GitHubでスターをつける

MemU にスターを付けることで、新しいリリースの通知を受け取り、永続的なメモリ機能を持つインテリジェントエージェントを構築する開発者コミュニティに参加できます。

![star-us](./assets/star.gif)

**💬 Discordコミュニティに参加:** [https://discord.gg/memu](https://discord.gg/memu)

---

## 🚀 はじめに

MemU の導入方法は主に 3 つあります。

### ☁️ クラウド版（[Online Platform](https://app.memu.so)）

memU をアプリケーションに最も速く統合する方法です。セットアップの手間をかけずにすぐ使い始めたいチームや個人に最適です。私たちはモデル、API、クラウドストレージをホストし、アプリケーションが高品質な AI メモリを利用できるようにします。

- **Instant Access** - 数分で AI メモリの統合を開始できます  
- **Managed Infrastructure** - スケーリング、更新、メンテナンスを当社で管理し、最適なメモリ品質を維持します  
- **Premium Support** - サブスクライブでエンジニアチームによる優先サポートを受けられます

### 手順

**Step 1:** アカウント作成

https://app.memu.so にアクセスしてアカウントを作成してください。  
その後、https://app.memu.so/api-key/ に移動して API キーを生成してください。

**Step 2:** コードに3行を追加
```python
pip install memu-py

# Example usage
from memu import MemuClient
# Initialize
  
詳細については、[APIリファレンス](docs/API_REFERENCE.md) または [公式ブログ](https://memu.pro/blog) をご覧ください。

📖 **完全な統合の詳細については [`example/client/memory.py`](example/client/memory.py) を参照してください。**

✨ **以上です！** MemU はすべてを記憶し、AI が過去の会話から学習するのを支援します。


最大限のセキュリティ、カスタマイズ性、制御、そして高品質を求める組織向け：
商用ライセンス - すべての専有機能、商用利用権、ホワイトラベルオプション
カスタム開発 - SSO/RBAC 統合、シナリオに合わせたフレームワーク最適化のための専任アルゴリズムチーム
インテリジェンスと分析 - ユーザー行動分析、リアルタイム運用監視、自動エージェント最適化
プレミアムサポート - 24時間365日の専任サポート、カスタムSLA、専門的な導入支援
📧 エンタープライズに関するお問い合わせ: contact@nevamind.ai

セルフホスティング（コミュニティ版）
ローカルでの制御、データのプライバシー、またはカスタマイズを重視するユーザー・開発者向け：


データプライバシー - 機密データを自分のインフラ内に保持
カスタマイズ - ニーズに合わせてプラットフォームを変更・拡張
コスト管理 - 大規模な導入時のクラウド利用料を削減

詳細は self hosting README
 を参照してください。


## ✨ 主な機能

### 🎥 デモ動画

<div align="left">
  <a href="https://www.youtube.com/watch?v=qZIuCoLglHs">
    <img src="https://img.youtube.com/vi/ueOe4ZPlZLU/maxresdefault.jpg" alt="MemU Demo Video" width="600">
  </a>
  <br>
  <em>MemU デモ動画を見るにはクリックしてください</em>
</div>

---
 
## 🎓 **ユースケース**

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="assets/usecase/ai_companion-0000.jpg" width="150" height="200"><br>**AI Companion** | <img src="assets/usecase/ai_role_play-0000.jpg" width="150" height="200"><br>**AI Role Play** | <img src="assets/usecase/ai_ip-0000.png" width="150" height="200"><br>**AI IP Characters** | <img src="assets/usecase/ai_edu-0000.jpg" width="150" height="200"><br>**AI Education** |
| <img src="assets/usecase/ai_therapy-0000.jpg" width="150" height="200"><br>**AI Therapy** | <img src="assets/usecase/ai_robot-0000.jpg" width="150" height="200"><br>**AI Robot** | <img src="assets/usecase/ai_creation-0000.jpg" width="150" height="200"><br>**AI Creation** | More... <br>その他... |
---

## 🤝 コントリビュート

オープンソースの協力を通じて信頼を築きます。あなたの創造的な貢献が memU の革新を前進させます。GitHub の課題やプロジェクトを確認し、参加して memU の未来に影響を与えましょう。

📋 **[詳細なコントリビューションガイドを読む →](CONTRIBUTING.md)**
 
### **📄 ライセンス**

MemU に貢献することで、あなたの貢献は **Apache License 2.0** の下でライセンスされることに同意したことになります。

---

## 🌍 コミュニティ

詳細については info@nevamind.ai までお問い合わせください

- **GitHub Issues:** バグ報告、機能リクエスト、開発状況の追跡。[Issueを提出](https://github.com/NevaMind-AI/memU/issues)  

- **Discord:** リアルタイムサポートを受けたり、コミュニティでチャットしたり、最新情報を取得。[参加する](https://discord.com/invite/hQZntfGsbJ)  

- **X (Twitter):** 更新情報、AIの洞察、重要な発表をフォロー。[フォローする](https://x.com/memU_ai)

## 🤝 エコシステム
 
素晴らしい組織と協力できることを誇りに思います：

<div align="center"> 
### 開発ツール
<a href="https://github.com/TEN-framework/ten-framework"><img src="https://avatars.githubusercontent.com/u/113095513?s=200&v=4" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://github.com/openagents-org/openagents"><img src="assets/partners/openagents.png" alt="OpenAgents" height="40" style="margin: 10px;"></a>
<a href="https://github.com/camel-ai/camel"><img src="https://avatars.githubusercontent.com/u/134388954?s=200&v=4" alt="Camel" height="40" style="margin: 10px;"></a>
<a href="https://github.com/eigent-ai/eigent"><img src="https://www.eigent.ai/nav/logo_icon.svg" alt="Eigent" height="40" style="margin: 10px;"></a>
<a href="https://github.com/milvus-io/milvus"><img src="https://miro.medium.com/v2/resize:fit:2400/1*-VEGyAgcIBD62XtZWavy8w.png" alt="Ten" height="40" style="margin: 10px;"></a>
<a href="https://xroute.ai/"><img src="assets/partners/xroute.png" alt="xRoute" height="40" style="margin: 10px;"></a>
<a href="https://jaaz.app/"><img src="assets/partners/jazz.png" alt="jazz" height="40" style="margin: 10px;"></a>
<a href="https://github.com/Buddie-AI/Buddie"><img src="assets/partners/buddie.png" alt="buddie" height="40" style="margin: 10px;"></a>
<a href="https://github.com/bytebase/bytebase"><img src="assets/partners/bytebase.png" alt="bytebase" height="40" style="margin: 10px;"></a>
</div>

---
*MemU とパートナーシップを希望されますか？[contact@nevamind.ai](mailto:contact@nevamind.ai) までご連絡ください。*
---

## 📱 WeChat コミュニティに参加する

最新情報、コミュニティディスカッション、限定コンテンツのために WeChat でつながりましょう：

<div align="center">
<img src="assets/qrcode.png" alt="MemU WeChat and discord QR Code" width="480" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 10px;">

*上記のいずれかのQRコードをスキャンして、WeChatコミュニティに参加してください*

</div>
---

*MemU コミュニティとつながり続けましょう！WeChat グループに参加して、リアルタイムのディスカッション、技術サポート、ネットワーキングの機会を活用してください。*

