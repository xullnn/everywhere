# LocalVoiceInput 感知实时（perceived-realtime）ASR 模型策略 —— 独立盲审

独立外部顾问意见。仅基于项目原始材料、本地安装的官方/开源代码，以及检索到的一手资料（官方 repo、官方代码、技术报告、官方模型卡）。未读取 `consult_briefs/`、`mlx_candidate_comparison_*.md` 或任何既有助手结论。项目内 spec/PMB 仅作为背景，不作为结论来源。

证据分级标注：
- **[已证实]** = 一手代码 / 官方文档 / 本地原始 eval JSON 可直接验证。
- **[工程假设]** = 方向合理但必须本机实测才能确认。
- **[通用知识]** = 行业通行做法，非本项目特有验证。

---

## 0. 一句话结论

> 你想要的不是“严格逐字流式”，而是“边说边累加、停下更准”的**感知实时**。这恰恰是当前主流本地 ASR 大模型（含 Qwen3-ASR）**官方自己采用的流式实现方式**——分块累计重算 + 前缀提示回滚。因此本项目独立做出的“cumulative recompute wrapper”路线在工程方向上是对的，且与 Qwen 官方流式同构。**MiMo-V2.5-ASR 可以做感知实时，但成本（显存/延迟）使它更适合作为“停后 final 精修”后端，而非浮窗 partial 后端。** 下一步真正缺的不是模型，而是一个**真实进程边界 + 真实墙钟节拍**的本地流式服务，以及一套不再“理想化计时”的评测。

---

## 1. 概念澄清：三类“实时”的边界 [已证实 + 通用知识]

把“实时”拆成三个**互不等价**的层级，避免再被模型卡上的 `streaming` 字样误导：

### A. Offline / file-level ASR（离线整段转写）
- 定义：拿到**完整音频** → 一次前向 → 一段最终文本。
- 代表：MiMo-V2.5-ASR `asr_sft(audio)`、Qwen3-ASR `transcribe(audio)`、FunASR offline Paraformer、FireRedASR-AED、GLM-ASR-Nano。
- 本项目证据：MiMo MLX `generate(...)` “loads the full audio, encodes full audio codes, builds one prompt, calls the model once”（`runtime_feasibility.md`），`mimo_audio.py:preprocess_input` 先把音频切 30s 窗、各自编码再拼接 codes，仍是一次性整段。**[已证实]**
- 特征：质量最高、无 partial、停后延迟 = 整段算一次的时间。

### B. Native streaming ASR（原生流式）
- 定义：模型/runtime 暴露**有状态会话**：`feed(pcm) → step → emit → close`，声学编码器**缓存历史、只增量算新帧**（cache-aware / chunk-aware conformer、RNN-T、CTC streaming）。延迟与算力**不随已说时长线性增长**。
- 代表（架构层）：Nemotron FastConformer-RNNT（cache-aware）、传统 Paraformer-online/2pass、商用流式引擎。
- 本项目关键发现：**“模型名里有 streaming ≠ runtime 暴露原生会话 API”**。
  - Nemotron MLX：`generate` / `stream_generate(audio)` 存在，但 `create_streaming_session/feed/step/close` **不存在**；它是“对已给定 buffer 做 cache-aware 文件流式”，不是麦克风 PCM 会话。且本机中英/术语质量弱（CER 0.309）。**[已证实]**
  - Qwen3-ASR MLX：有 `stream_transcribe/stream_generate`，但**只是对已物化音频 buffer 边生成边吐 token**，无 `create_streaming_session`。**[已证实]**

### C. Chunked / cumulative perceived realtime（分块累计感知实时）—— 你真正要的那一类
- 定义：**用 offline 模型 + wrapper** 模拟流式。把不断增长的音频前缀（1s, 2s, 3s, …）周期性重算，把每次输出当作 partial 推给浮窗；停止后对完整音频做一次 final。可叠加“前缀提示 + 回滚末 K token”降低边界抖动。
- 关键洞察（一手代码）：**这正是 Qwen3-ASR 官方流式的真实实现**：
  - `qwen3_asr.py:streaming_transcribe` 注释明示：“each time a new chunk is ready, we append it to audio_accum and **re-feed all audio seen so far** to the model … prefix rollback strategy … rollback last `unfixed_token_num` tokens”。**[已证实]**
  - 官方报告/博客印证：“2-second chunk size, a 5-token fallback, keep the last four chunks unfixed … prefix rollback … sliding window bounds encoder/decoder context for indefinite streaming”。**[已证实]**
  - 即 Qwen 的“streaming”本身就是 **B 的外壳 + C 的策略**——它在 vLLM 上做累计重算 + 前缀回滚，并用滑窗给编码器/解码器上下文封顶以支持“无限流式”。
- 本项目的 `qwen3_mlx_cumulative_*` 与此**同构**：你独立复现了 Qwen 官方流式的核心思想。**[已证实，方向正确]**

**边界小结**：你要的“可接受短延迟、微停顿分段、滚动窗口、累计重算、停顿后修正前文”= **C 类**。C 类不要求模型是 B 类。**任何 offline（A 类）模型都能被包成 C 类**，差别只在“重算成本是否可控”。

---

## 2. 模型级判断：本地 ASR 是否支持“文本+语音”联合输入 / 上下文纠错

回答你的问题 2。结论：**主流本地 ASR 大模型大多是“audio-LLM”，架构上天然支持文本上下文输入；但各家“是否暴露这个口子”差别很大。** [已证实]

| 模型 | 文本/上下文输入能力（一手代码证据） | 暴露形式 |
|---|---|---|
| **Qwen3-ASR（官方 qwen-asr）** | `transcribe(audio, context=..., language=...)`，`_build_messages` 把 `context` 放进 **system role**；`_build_text_prompt` 在 system prompt 注入 context。官方：“utilize context tokens in the system prompt for customized results”“prompt biasing is very soft”。 | **直接 API 参数 `context`**（最干净）。**[已证实]** |
| **Qwen3-ASR MLX（mlx-audio）** | `_build_prompt(..., system_prompt=...)`、`stream_generate(..., system_prompt=...)` 支持 system prompt + audio。 | **`system_prompt` 参数**。**[已证实]** |
| **MiMo-V2.5-ASR** | 架构是 `MiMoAudioForCausalLM`（音频-语言模型），`InputSegment` 有独立 text 通道，prompt 由文本模板 + audio codes 交织组成——**架构层可注入文本**。但官方 `asr_sft(audio, audio_tag)` **只暴露音频 + 语言 tag**，无 context/hotword/prompt 文档化入口。 | **仅语言 tag**；context 需自己改 prompt，**官方未支持**。**[已证实]** |
| **Fun-ASR-Nano** | 官方报告含 “hotword customization / context”。 | 需按 FunASR 接口核实。**[需核实]** |
| **传统 Paraformer（当前基线）** | FunASR WebSocket 支持 `hotwords` 字段（`realtime_gate.py` start_message 里有 `hotwords`）。 | **WebSocket hotwords**。**[已证实]** |

**对“上下文纠错”的工程含义**：
- Qwen3-ASR 的 `context` 是**做术语/拼写偏置最现成的入口**：把项目热词（`LocalVoiceInput / FunASR / Qwen3-ASR / MiMo-V2.5-ASR / FocusDetector / PasteEngine / Obsidian / Cursor …`）和“上一段已确认 final 文本”塞进 system prompt，即可在**模型内部**做 bias，而不必只靠你现在 `CorrectionPipeline` 的规则替换。**[已证实可行，效果需实测]**
- 但官方明说 prompt biasing **“very soft”**——它降低错误概率，不是强制改写。强约束（如 `玄界→玄戒`）仍应保留规则后处理。**[已证实]**
- **关键警告**：在 **C 类累计重算** 中把“上一轮 partial 文本”当 prefix prompt 喂回去，会形成**自反馈**：一旦某轮 partial 错了且被当上下文，错误可能被放大。Qwen 官方用“回滚末 K token / 前 N 块不用前缀”正是为压制这个抖动（`unfixed_chunk_num` / `unfixed_token_num`）。自建 wrapper 必须照抄这套保护，否则会出现“越改越歪”。**[已证实机制，本项目需实测调参]**

---

## 3. 微信输入法 / 豆包 / 讯飞那种“修正前文”效果从哪来 [通用知识 + 部分已证实]

回答你的问题 3。结论：**几乎从来不是单一模块，而是一条多段流水线。** 把观察到的效果拆开对应：

| 你看到的效果 | 主要来源 | 说明 |
|---|---|---|
| 边说边出字（增量 partial） | **流式声学解码**（streaming transducer/AED/CTC，B 类） | 第一遍快速 online 结果。 |
| 长停顿后“回改前文”、合并重复词 | **two-pass / 重打分 rescoring**（offline 第二遍）+ **endpoint/VAD 分段** | 停顿触发段末，offline 整段重算覆盖 online。FunASR 2pass 就是这结构（你 MVP 已在用：online=partial，offline=final 修正）。**[已证实于本项目]** |
| 自动补标点、数字/日期规整（ITN） | **独立的标点模型 + ITN 后处理** | 通常是 ASR 之后单独一层（FunASR 的 punc/ITN）。你的 `cases.local.jsonl` 里 `punctuation_001 / zh_numbers_001` 正是测这层。 |
| 术语、产品名、人名拼对 | **热词 / context bias**（解码期）+ 后处理替换 | 解码期 bias（Qwen `context`）+ 规则纠偏（你的 `hotwords/homophones`）。 |
| 改错别字、顺滑语气词、改写口语 | **小型 LLM 顺滑/纠错（可选）** | 豆包等产品里更明显；属可选增强，**非 ASR 本体**。 |

要点：
- “修正前文”**本质是 two-pass + endpoint 分段**，不是模型“记得自己说错了”。**[已证实结构]**
- 标点/ITN/热词大多是**ASR 之外的模块**，可独立选型、独立评测。
- 小 LLM 纠偏是**最上层、最可选**的一段——与你的非目标“不默认开启 LLM 纠偏”一致；可作为长文本模式的显式可选项。**[与项目约束相容]**

**对 LocalVoiceInput 的直接启示**：你不需要“一个全能模型”。更稳的是**分层**：流式 partial 后端（C 类 wrapper 或原生流式）＋ 停后 final 后端（高质量 offline）＋ 标点/ITN/热词后处理＋（可选）长文本 LLM 顺滑。这与你已有的 `online→partial / offline→final / CorrectionPipeline` 架构完全契合，只是把“offline final”换成更强的模型。

---

## 4. MiMo-V2.5-ASR 是否值得做增量转写（C 类）验证

回答你的问题 1（针对 MiMo）。**判断：值得验证，但定位为“停后 final 精修后端”，不要押注它做浮窗 partial 后端。** 优先级低于 Qwen3-ASR MLX 路线。

理由（一手证据）：
- **质量是最强项**：本机 10 例 CER 0.0311 / WER 0.1613，三者中最好（`runtime_feasibility.md`）。**[已证实]**
- **成本是硬伤**：
  - 冷加载约 **60.5s**，短 WAV 峰值约 **9.17GB**，10 例整跑峰值约 **28.1GB**（命令级，非稳态 RSS）。**[已证实，本项目证据]**
  - 8B 参数 + 2.4GB 音频 tokenizer，**每次 `generate` 固定开销高**。C 类要在 1s/2s/3s… 前缀上反复整段重算，MiMo 把“整段”再重编码再 8B 生成，**重算单价远高于 0.6B**。
  - 在 48GB 机器上，28GB 峰值会与系统/前台 App 争内存——做**常驻**浮窗后端风险大。**[工程假设：需稳态 RSS 实测]**
- **官方定位就是 offline**：MiMo 官方 repo/模型卡**未提任何 streaming/实时**，API 只收 audio + 语言 tag（`WebFetch` 官方 README 确认）。它被明确做成“高准确率、抗噪、方言、歌词、多说话人”的离线精度标杆。**[已证实]**
- **架构上能塞文本但官方没开口**：`MiMoAudioForCausalLM` + `InputSegment` text 通道说明它能接受文本上下文，但 `asr_sft` 未暴露 context/hotword。要用得自己改 prompt 构造，属研究性改动。**[已证实]**

**给 MiMo 的具体建议**：
1. 把 MiMo 放进“**final-only 后端**”候选：用户停止后，对完整音频跑一次 MiMo，作为**最高质量 final**（尤其长文本模式 Option+Space）。先实测**稳态常驻 RSS + 单次 final 延迟**是否可接受。**[工程假设]**
2. **不要**让 MiMo 驱动 partial。若一定要 MiMo 的感知实时，用**粗粒度块**（如每 3–5s 一次、且只在 VAD 停顿点触发），而非 1s 步长，控制重算频率。**[工程假设]**
3. 若 MiMo final 延迟/内存不可接受，退回 Qwen3-ASR 1.7B / MiMo 仅作离线 benchmark 锚点。

---

## 5. 现有评测方法的不足与改造建议

回答你的问题 4。**判断：用录音文件模拟实时输入“方向有效、且是必要的”，但当前实现有三处会让结论失真，必须改造。**

### 5.1 哪些是对的（保留）[已证实]
- 固定录音脚本 + 标准答案 + 可复现 WAV + 统一指标（CER/WER/RTF/first_partial/final_latency/coverage）——**完全正确**，远胜“人工随便念”。
- `realtime_gate.py` 的硬条件设计是对的：**必须在“模拟用户停止”前出 partial、停止后出 final、拒绝 final 之后的 late partial、区分“中途 offline segment ≠ 整段会话结束”**。这套语义和你 MVP 的会话状态机一致。
- 把“file-level 质量”与“realtime 行为”**分两套指标**——正确且关键。

### 5.2 三个会让结论失真的缺陷（必须改）[已证实]
1. **严格实时门只跑过 FunASR**。`realtime_gate.py` 的 `--adapter` **只接受 `funasr-ws`**（`choices=["funasr-ws"]`）。所有 MLX 候选**从未进过这个真实墙钟、真实分块节拍的门**，只进过 `qwen3_mlx_cumulative_service.py` 的**另一套**门。两套门不可直接比较。
2. **MLX cumulative service 用的是“理想化计时”，不是真墙钟**。`qwen3_mlx_cumulative_service.py`：
   - chunk 以 `simulated_now_ms = audio_end_ms` 入列——**假设音频一到就处理，无真实 `sleep`**；
   - 延迟用 `worker_available_ms + compute_wall_ms` **建模**串行 worker，而非真实 asyncio 调度；
   - 因此 `first_usable_partial_ms / final_latency_ms` 是**模型估计值**，会**系统性偏乐观**（忽略真实排队、GIL、mx.eval 抖动、音频采集 jitter）。`native_realtime_gate_eligible` 固定 false 是诚实的，但延迟数字不能当“产品延迟”。
3. **file 替放天然缺三样东西**：真实 VAD/endpoint 行为、真实麦克风噪声/AGC/远场、真实采集节拍抖动。对“停顿分段、何时触发 final”这类**端点相关**结论，纯 file 替放无法回答。

### 5.3 改造建议（按价值排序）
- **R1（最高）：统一“真实墙钟”流式门，让所有后端走同一把尺。** 给 `realtime_gate.py` 增加一个**通用 push-PCM 适配层**（不限 funasr-ws），把 MLX 累计 wrapper 接成真实 `start/push_pcm(实时 sleep)/partial/finish/final/cancel` 服务，**用真实 wall-clock 计时**，输出与 FunASR 同口径的 gate 字段。这样 Qwen3-MLX wrapper 与 Paraformer 基线**可直接对比**。**[工程任务]**
- **R2：把 wrapper 放进真实进程边界再测。** 现在是 in-process。需起一个**本地子进程/本地 socket 服务**，测：跨进程 IPC 延迟、模型常驻不重载、稳态 RSS、取消/陈旧结果隔离在真并发下是否仍成立。`current_focus.md` 已把这列为下一步——评测必须跟着进程边界走。**[工程任务]**
- **R3：补“感知实时质量”指标，而不仅是延迟。** 新增：`partial_rewrite_rate`（已有，须纳入门槛）、**partial 稳定性**（同一前缀被改写次数）、**partial→final 的回改幅度**、**首词出现到稳定的时间**。用户体验对“抖动/反复改字”比对“绝对延迟”更敏感。**[工程任务]**
- **R4：扩样本到 30–100 条真实录音**，覆盖你 `model_survey.md` 列的场景（短/长/中英混/术语/低音量/快语速/噪声/已知失败例）。现在只有 10 例，long_200/long_400 各 1 条，统计噪声大。**[工程任务]**
- **R5：加“端点/停顿”用例**——录制中间含 2–5s 真停顿的长音频，验证“中途 offline segment 不提前结束会话”在 wrapper 下也成立（你 MVP 已修过 FunASR 的这个 bug，wrapper 必须复测）。**[工程任务]**
- **R6（可选）：半在线评测桥**——用一台能跑 vLLM 的 Linux/CUDA 机，仅用于验证 **Qwen3-ASR 官方 vLLM 流式**的质量/延迟上界，作为 MLX wrapper 的**参照天花板**（不进产品，仅作 oracle 对比）。因为官方流式只在 vLLM 上有。**[可选，需另一台机器]**

---

## 6. 面向 LocalVoiceInput 的下一步技术路线与优先级

总回答你的问题 5。原则：**先证服务形态，再换模型；分层而非单模型；partial 与 final 解耦。**

### P0 — 统一评测底座（先做，1 项工程）
- 实施 **R1 + R3**：通用 push-PCM 真实墙钟门 + 感知实时质量指标。
- 产出：Paraformer 基线 vs Qwen3-MLX-0.6B wrapper 在**同一把尺**上的 partial 延迟、partial 稳定性、final 质量、RTF、RSS。
- 没有这步，后面所有“谁更好”的结论都站不住。**[最高优先级]**

### P1 — 把 Qwen3-ASR MLX 0.6B 做成真实本地流式服务
- 依据：Apple Silicon 原生、有 token streaming、累计重算在本机 smoke/long120 已“promising”、**且与 Qwen 官方流式同构**（最可借鉴官方策略：`unfixed_chunk_num/unfixed_token_num/2s chunk`）。**[已证实方向]**
- 动作：
  1. 真实子进程 + 本地 socket（R2）。
  2. 移植官方流式的**前缀回滚 + 前 N 块不用前缀**保护，压 partial 抖动。
  3. 把项目热词 + 上一段 final 注入 `system_prompt`（MLX 已支持），实测 bias 效果。**[工程假设：bias 增益待测]**
  4. 过 P0 的统一门；RTF<1、首 partial 够快、稳态 RSS 可接受才算通过。
- **暂不接 Swift App**，与 `current_focus.md` 一致。

### P2 — 分层后端：partial 与 final 用不同模型
- partial（浮窗）：Qwen3-MLX-0.6B wrapper（轻、快、原生）。
- final（停后精修）：候选 **MiMo-V2.5-ASR**（质量最高）或 **Qwen3-ASR-1.7B**——取决于 P1/R 的稳态 RSS 与单次延迟实测。长文本模式（Option+Space）尤其值得用 MiMo 做 final。**[工程假设]**
- 后处理：保留并强化 `CorrectionPipeline`（标点/ITN/热词/同音），强约束仍走规则，不依赖 soft prompt bias。

### P3 — 保底与对照
- 若 MLX wrapper 在真实墙钟门下达不到体验（抖动大/延迟高/内存高），**保留 FunASR 2pass 作为已验证基线**继续用，仅用更强模型替换“offline final”那一段（README 既有建议方向，但需用 P0 门量化“是否明显优于 Paraformer”再换）。
- Nemotron 暂缓（中文/术语质量弱）；Fun-ASR-Nano MLX 暂缓（长文本质量风险 CER 0.3156）；GLM-ASR-Nano / FireRedASR 作为离线质量对照池。**[已证实质量风险]**

### 明确不做（与项目约束一致）
- 不为追求“原生流式”而引入 vLLM/CUDA 进产品（M4 不可行）。
- 不默认开 LLM 纠偏、不上云、不重构 InputMethodKit。

---

## 7. 已证实 vs 需实测 —— 清单

### 已证实（一手代码/官方/本地 eval 可验证）
1. Qwen3-ASR 官方“streaming”=累计重算 + 前缀回滚 + 滑窗封顶，**仅 vLLM**；本机 M4 不具备。
2. Qwen3-ASR（官方 & MLX）**支持文本/上下文输入**（`context` / `system_prompt`），但官方称 prompt biasing “very soft”。
3. MiMo-V2.5-ASR 官方**仅 offline**，API 只收 audio+语言 tag，无 context/hotword 入口；架构层可塞文本但未暴露。
4. MiMo 本机质量最高（CER 0.0311）但成本高（冷载 ~60s、10 例峰值 ~28GB）。
5. “模型名含 streaming ≠ 有原生会话 API”：Nemotron/Qwen3-MLX 本机均无 `create_streaming_session/feed/step/close`。
6. 任何 offline 模型都可包成 C 类感知实时；这正是 Qwen 官方做法。
7. 当前严格实时门只跑过 FunASR；MLX 走的是**理想化计时**的另一套门，延迟数字偏乐观。
8. “修正前文”本质是 two-pass + endpoint 分段；标点/ITN/热词多为 ASR 外的独立模块。

### 需实测的工程假设
1. Qwen3-MLX-0.6B 累计 wrapper 在**真实进程边界 + 真实墙钟**下的 partial 延迟、抖动、final 质量、RTF、稳态 RSS。
2. 把热词/上一段 final 注入 `system_prompt` 对本项目术语的**实际 bias 增益**（及自反馈抖动风险）。
3. MiMo 作为 final-only 后端的**稳态常驻 RSS + 单次 final 延迟**是否可接受（48GB 上）。
4. 在真停顿用例下，wrapper 的“中途 offline 不提前结束会话”是否仍成立。
5. MiMo/Qwen-1.7B 粗粒度块（3–5s、VAD 触发）感知实时的体验上限。
6. 替换“offline final”后端是否**在统一门上明显优于 Paraformer 基线**（决定是否值得换）。

---

## 8. 风险与权衡
- **延迟数字别拿现成的当产品 KPI**：现有 MLX 延迟来自理想化计时，真实并发/进程边界会变差。先建 P0 门再下结论。
- **soft prompt bias 的双刃**：能改善术语，但在累计重算里会放大错误；必须配前缀回滚保护 + 规则强约束兜底。
- **8B 模型常驻内存争用**：MiMo 做 partial 后端在 48GB 上风险高；做 final 后端更稳。
- **样本太少**：10 例不足以支撑选型，先扩到 30–100 例再定。
- **不要被“原生流式”执念绑架**：你的产品需求是 C 类感知实时，C 类不需要 B 类；强求原生流式会把你推向 vLLM/CUDA，违背本地 M4 约束。

---

## Sources
- 本地一手代码：`/.venv/.../qwen_asr/inference/qwen3_asr.py`（官方 QwenLM，含 `transcribe(context=...)` 与 `streaming_transcribe` 累计重算+前缀回滚，注明 vLLM only）
- 本地一手代码：`/.external/repos/mlx-audio/.../qwen3_asr/qwen3_asr.py`（`_build_prompt(system_prompt=...)`、`stream_generate`，无 `create_streaming_session`）
- 本地一手代码：`/.external/repos/MiMo-V2.5-ASR-MLX/src/mimo_audio/mimo_audio.py`（`asr_sft(audio, audio_tag)`，整段一次性生成）
- 本地原始材料：`eval/asr_streaming/runtime_feasibility.md`、`model_registry.json`、`realtime_gate.py`、`qwen3_mlx_cumulative_service.py`、`cases.local.jsonl`、`project_memory_bank/*`
- [QwenLM/Qwen3-ASR 官方 repo](https://github.com/QwenLM/Qwen3-ASR) · [官方推理代码](https://github.com/QwenLM/Qwen3-ASR/blob/main/qwen_asr/inference/qwen3_asr.py)
- [Qwen3-ASR 官方博客](https://qwen.ai/blog?id=qwen3asr) · [Qwen3-ASR 技术报告 (arXiv)](https://arxiv.org/html/2601.21337v2)
- [XiaomiMiMo/MiMo-V2.5-ASR 官方 repo](https://github.com/XiaomiMiMo/MiMo-V2.5-ASR) · [官方模型卡 (HF)](https://huggingface.co/XiaomiMiMo/MiMo-V2.5-ASR)
