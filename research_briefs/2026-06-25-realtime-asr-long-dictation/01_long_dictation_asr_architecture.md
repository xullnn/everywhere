# DeepResearch Task 01: Long-Dictation Realtime ASR Architecture



项目定位：`LocalVoiceInput` 是一个 macOS 本地离线语音输入 MVP，目标是在 MacBook Pro M4 / 48GB 内存上运行，作为跨 App 的通用语音输入工具。它不是 InputMethodKit 真输入法版本，不把 partial 文本直接写入当前输入框，不默认上传音频或文本，不默认启用 LLM 纠错，也不默认自动发送消息。

研究过程中不要修改仓库，也不要读取或要求任何密钥、账号、密码、`.env`、客户材料、私有凭据、生产数据或未授权材料。外部研究请使用最新公开资料，并给出来源链接。每个重要结论请标注 `confirmed` / `inferred` / `unknown`。如信息可能随时间变化，请注明实际检索日期。

## 研究过程要求

请在报告前部加入项目语境确认，至少包括：

- 你是否读取了仓库；如果没有，请说明本任务基于本 brief 中提供的项目事实完成。
- 足够支撑本任务的项目事实，避免为了凑数引入噪声。
- 本任务边界：只研究成熟实时语音输入/实时 ASR 产品和技术路线如何处理长语音、低延迟 partial、前文修正和最终结果，不做 `LocalVoiceInput` 的最终工程实施方案。
- 你认为仍需项目团队确认的关键假设。

来源优先级建议：

1. 官方论文、技术报告、模型卡、产品文档、SDK 文档、开源项目文档。
2. 学术论文、公开 benchmark、会议演讲、可信工程博客。
3. 商业产品资料、社区讨论、开发者反馈。使用时请标注偏见或不确定性。

重要结论必须标注可信度：

- `confirmed`: 有明确来源或项目事实支持。
- `inferred`: 基于多个事实合理推断，但没有直接来源。
- `unknown`: 当前资料不足，不能下结论。

建议为关键事实建立事实卡片：

| Fact | Status | Source | Date Checked | Notes |
|---|---|---|---|---|
| ... | confirmed / inferred / unknown | URL or project fact | YYYY-MM-DD | ... |

## 当前项目事实

以下事实用于帮助你理解问题背景；如果后续研究发现某些术语需要更精确定义，请在报告中指出。

- `LocalVoiceInput` 的 Swift App 只负责靠近用户交互的一层：全局快捷键、录音、浮窗、焦点检测、剪切板、自动粘贴/复制、安全降级。
- 当前 ASR 运行在本机，不走云端。App 通过本地 HTTP 调用一个 Python ASR 服务，地址类似 `http://127.0.0.1:<port>`。
- “Qwen3 ASR 服务”和“Qwen3-ASR 模型”不是同一个东西：
  - Qwen3 ASR 服务是本机 Python 进程/HTTP 包装层，负责接收 Swift App 发来的音频片段、缓存音频、决定什么时候调用模型、把结果包装成 partial/final JSON 返回。
  - Qwen3-ASR 模型是实际做语音识别的模型权重和推理函数，负责把音频内容识别成文字。
  - 简单说：服务是本机接口和调度层；模型是识别引擎本身。
- 当前候选模型是 `Qwen3-ASR 0.6B MLX 8-bit`。它在短文本和中等长度语音输入上表现较好，但当前本地接入方式不是原生 stateful streaming。
- 当前实现使用“累计重算”模拟实时 partial：
  - 用户说到 1 秒时，服务识别第 0-1 秒音频。
  - 用户说到 2.5 秒时，服务重新识别第 0-2.5 秒音频。
  - 用户说到 4 秒时，服务重新识别第 0-4 秒音频。
  - 每次得到的新完整文本覆盖上一次 partial，因此用户会看到文字持续增加，也会看到前文标点、错字或短句被“修正”。
- 这种“修正”很可能不是独立纠错模块在编辑前文，而是更长音频上下文让模型重新识别整段时输出了更好的完整文本。
- 当前问题：当用户持续说很长一段话，例如几百字甚至更长时，后面的 partial 会越来越慢，因为每次都要重新识别越来越长的音频；最终停止录音时也可能需要等待更久。
- 用户真正需要的是产品体验层面的实时语音输入：说话时能持续看到文字累加，可以接受一定延迟；这不是外交同传那种极低延迟场景。但它必须支持真实长文本听写，不能只适合短句。
- 项目安全边界：本地优先、隐私优先、不丢文本、不误粘贴、不污染剪切板。partial 只显示在浮窗，最终文本才粘贴或复制。

## 本任务目标

调研成熟实时语音输入/实时 ASR 产品和公开技术路线，回答：

1. 它们在长语音听写中是否也会遇到“越说越慢、前文不断重算、长文本不友好”的限制。
2. 表现较好的产品或系统如何在“低延迟 partial、前文修正、长文本稳定输出、最终质量”之间做权衡。
3. 背后的常见模型或系统架构是什么：真流式模型、分段提交、滚动上下文、二阶段识别、端点检测、重打分、标点恢复、上下文纠错、LLM 后处理等分别承担什么角色。
4. 对 `LocalVoiceInput` 这种本地 macOS 离线语音输入工具，哪些技术路线值得后续工程验证，哪些路线明显不适合。

本任务只做资料收集、事实确认、风险识别和知识层面的综合。请不要输出完整工程实施方案、排期或代码。

## 核心研究问题

- 成熟产品中的实时语音输入，例如 Apple Dictation、Google voice typing / Speech-to-Text streaming、Microsoft Azure Speech continuous recognition、Whisper/WhisperKit 类本地方案、FunASR/WeNet/sherpa-onnx 等开源路线，通常如何处理长时间连续听写？
- 它们的 partial 显示是否来自真正增量模型状态，还是也可能来自窗口化重算、分段重算、二阶段修正或服务端内部缓存？
- 长语音输入中，前文标点、错字、重复词、断句被修正，通常是 ASR 模型本身完成，还是由后处理模型、标点模型、语言模型、LLM、热词/上下文偏置、inverse text normalization 等模块完成？
- 对长文本听写，业界常见的“提交稳定片段”策略是什么？例如多长时间或多长静音后把一段文字视为 stable，后续是否还允许修改已经 stable 的前文？
- 真流式 ASR、累计重算、滑动窗口重算、分段提交 + 后处理，分别有什么优缺点？在本地 M4 设备上各自的性能风险是什么？
- 对中文和中英文混合输入，哪些公开模型或开源系统明确支持长语音/流式/准流式听写？请尽量区分官方支持、社区包装支持和理论可行但未验证。
- 如果某个产品长语音体验很好，但资料没有公开模型细节，请明确标注 `unknown`，不要把推断当事实。

## 范围内

- 实时语音输入的产品体验定义：用户说话时文字逐步出现，可以有轻微延迟，重点是长文本听写可用。
- ASR 系统架构：真流式、chunk streaming、滑动窗口、累计重算、分段提交、端点检测、partial/final 机制、前文修正策略。
- 长语音场景：几十秒、几分钟、几百字到上千字连续听写。
- 中文和中英文混合语音识别优先；英文资料也可用于解释通用技术路线。
- 本地部署可行性分析，尤其是 macOS Apple Silicon / MLX / Core ML / CPU/MPS 方向。
- 产品案例和开源案例都可以纳入，但必须区分“产品表现”“公开技术事实”“推断”。

## 范围外

- 不做最终模型选型。
- 不写 `LocalVoiceInput` 的代码或详细实施计划。
- 不研究云端商业 API 的价格、账户、鉴权或接入步骤，除非这些资料能帮助理解架构。
- 不讨论隐私政策或合规细节，除非它直接影响本地/云端架构判断。
- 不假设可以上传用户音频到云端；`LocalVoiceInput` 的目标仍是本地离线优先。
- 不把翻译同传、会议字幕或对话机器人作为主要产品场景；它们只能作为技术参考。

## 推荐输出结构

不强制完全照此结构输出；如研究内容更适合其他结构，可以调整。但请确保关键事实、来源、开放问题和可复用材料容易被后续综合。

1. Project Context Receipt
2. Executive Summary
3. Key Findings
4. Product Case Studies
5. Architecture Patterns
6. Long-Dictation Failure Modes
7. Model / Runtime Options Relevant to LocalVoiceInput
8. Comparison Table
9. Evidence / Fact Cards
10. Risks, Unknowns, and Assumptions
11. Implications for LocalVoiceInput
12. Open Questions
13. Follow-Up Handoff

## 建议比较表

请至少输出一张比较表，字段建议包括：

| System / Product / Model | Public Source | Supports User-Perceived Realtime Dictation? | Native Stateful Streaming? | Long-Dictation Strategy | Prior Text Revision Strategy | Chinese / Mixed CN-EN Support | Local Deployment Feasibility | Evidence Status |
|---|---|---|---|---|---|---|---|---|

如果某字段无法确认，请填 `unknown`，并解释为什么无法确认。

## 重点请解释清楚的概念

请用普通工程人员能理解的语言解释以下概念，不要假设读者有语音处理背景：

- user-perceived realtime dictation
- native streaming ASR
- partial result vs final result
- cumulative recompute
- sliding window
- endpointing / VAD
- stable segment / committed segment
- rescoring
- punctuation restoration
- contextual biasing / hotword biasing
- ASR-internal correction vs post-processing correction

## 输出要求

- 用中文输出。
- 给出来源链接和检索日期。
- 对重要结论标注 `confirmed` / `inferred` / `unknown`。
- 明确区分事实、推断、建议和开放问题。
- 不要读取或要求任何敏感材料，不要修改仓库。
- 如果引用产品效果，请尽量说明是官方声明、论文指标、开发者经验还是你的推断。
- 如果目标工具支持文件产物，请把研究产物按类别分文件夹放置，例如：主报告、事实卡片、来源材料、比较表、开放问题、交接清单，并将整个任务成果目录打包成一个 `.zip` 文件，供下载和归档。
- 如果目标工具不支持文件夹或 zip，请用清晰标题分隔这些内容，保证后续可以手动归档。

## Follow-Up Handoff

本次只有一个外部研究任务，无跨任务依赖。请在末尾明确列出：

- 可直接交给 `LocalVoiceInput` 后续技术方案设计使用的事实和表格。
- 需要本地工程验证的问题，例如某模型是否真的支持 incremental PCM feed、长音频 partial 延迟曲线、分段提交后是否丢上下文等。
- 值得沉淀进项目长期知识库的架构结论。
- 对当前 Qwen3-ASR MLX 累计重算路线的判断：适合作为什么阶段的方案，不适合作为什么阶段的方案，以及需要哪些证据才能升级判断。
