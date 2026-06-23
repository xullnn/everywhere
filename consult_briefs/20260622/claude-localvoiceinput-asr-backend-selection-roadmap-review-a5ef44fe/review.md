# LocalVoiceInput ASR 后端选择路线 — 独立盲审意见

日期：2026-06-22
范围：仅基于项目内 SDD/PMB 状态、eval 脚本源码与任务提供的事实独立审查。未读取 `consult_briefs/` 下任何文件，也未依赖任何此前由助手生成的总结、排名或推荐。SDD/PMB 中的推荐仅作为"当前项目状态"读取，未当作正确结论。

审查依据（已实际阅读的源文件）：
- `specs/feature_matrix.json`
- `eval/asr_streaming/incremental_ux_gate.py`（全文）
- `eval/asr_streaming/qwen3_mlx_cumulative_service.py`（头部 + 契约）
- `eval/asr_streaming/runtime_feasibility.md`（全文，含实测数字）
- `eval/asr_streaming/run_eval.py`（`char_length_ratio` / `partial_rewrite_rate` / 默认阈值定义）

---

## 1. 总判断

路线**方向正确，但不能按草案直接执行**。它的分层逻辑（partial / final / fallback / reference 四类后端、先证服务边界再进 App、FunASR 保底）是对的。但草案在四个地方存在会导致返工或验收失真的问题：

1. **Phase 2 的前提不成立**：草案说"真实 Qwen3 服务……然后进 `incremental_ux_gate.py`"，但该 gate 当前**只能驱动 fake 后端**（CLI `--adapter` 只接受 `fake-valid/fake-final-only/fake-late-partial`），既没有真实后端适配器，也没有跨进程客户端/传输适配器。同时另有一套 `qwen3_mlx_cumulative_service.py` 自带 `service_gate_passed` 门槛，与 `incremental_ux_gate.py` 语义重叠但不一致。**当前存在两套并行 gate，"统一 gate"在工程上尚不存在。**
2. **关键阈值与所选方案的实测行为冲突**：草案把 `first partial latency <= 1.5s` 当候选门槛，但累计重算实测首个可用 partial 在 smoke 上约 `2078ms`（取 2s 前缀）。按草案这会**直接淘汰被优先推进的 Qwen3 0.6B 累计重算方案**（在短语音上）。
3. **质量没有硬门槛**：`incremental_ux_gate.py` 的 fail 原因里只有 `final_coverage_too_low` 和 `rtf_too_high`。`final_coverage_ratio` 实为**字符长度比**（`char_length_ratio`，见 `run_eval.py:890`），不是正确率。CER/WER 被计算但**不参与 pass/fail**。也就是说：一个长度对、内容错的后端也能通过 UX gate。
4. **RTF 在 realtime 模式下不可信**：gate 的 `rtf = run_wall_seconds / duration_seconds`，而 realtime 模式每个 chunk 后 `time.sleep(chunk_ms)`，run_wall 必然 ≈ 音频时长，**RTF 恒 ≈ 1.0**，无法反映计算余量。把 `RTF <= 1.0` 当 realtime 门槛要么恒不可达、要么恒贴边。且工具默认 `max_rtf=1.5` 且 `fail_on_high_rtf` 默认关闭，与草案的 1.0 不一致。

下面给出修正版路线、SDD 要点、候选优先级/淘汰/进 App 门槛、可验收阶段目标，以及硬/软门槛划分。

---

## 2. 路线问题详述

### 2.1 "统一 gate"目前是空壳（阻断 Phase 1/2）
- `incremental_ux_gate.py` 是 backend-neutral（`IncrementalBackend` Protocol），但仓库里只有 fake 实现，CLI 也只暴露 fake adapter。真实模型无法进入此 gate。
- `qwen3_mlx_cumulative_service.py` 自己又实现了一遍 session/partial/finish/final/cancel/stale 隔离 + `service_gate_passed`。这与 UX gate 是**两套真值**。
- 后果：若不先把"真实后端 + 传输边界"接入唯一 gate，Phase 2~5 各模型会用各自脚本各自门槛"自证通过"，无法横向对比，违背 PMB/SDD 的单一真值原则。

### 2.2 gate 用 WAV 回放，未覆盖真实交互与音频路径
- gate 把预录 WAV 按时间切片回放，**不测**：实时麦克风采集、VAD/停顿分段、Right Option 按住、Option+Space 长文本、Esc 取消的真实控制流。
- 用户已澄清"实时 = 感知层增量 + 停顿分段 + 滚动窗口 + 累计重算 + 停止后 final 修正"。gate 测了累计重算与 final 修正，但**没测停顿分段**这一被用户明确接受的形态。
- 因此 gate 通过是 App 集成的**必要非充分**条件。草案 Phase 7"综合决策后才做 Swift 集成"缺一个"真实音频 + 控制流"验证阶段。

### 2.3 同步回放 gate 的计时模型与真实异步服务不一致
- gate 在 chunk-ingest 线程内**同步**调用 `on_chunk`。真实服务的重算应在后台线程，与音频摄入并发。若真实后端在 `on_chunk` 里阻塞计算，会推迟后续 sleep 与推流，扭曲 `first_partial_latency` / `final_latency` 与输入时间线。
- 这是 Phase 2 必须明确的架构约束：**计算必须脱离摄入线程**，否则 gate 的延迟数字不可作为 App 行为依据。

### 2.4 缺少质量硬门槛与术语/热词验收
- `runtime_feasibility.md` 自己指出：三款模型对 `Qwen3-ASR`、`MiMo-V2.5-ASR`、`LocalVoiceInput`、模块名都需要 hotword/context 纠偏。
- 草案没有任何阶段或验收项覆盖 CER/WER 硬阈值与术语准确率。对"开发者给自己用的本地语音输入"，专有名词错误是高频痛点。

### 2.5 缺少运行时降级/容错与可复现性约定
- 没有约定：所选后端服务崩溃/超时时如何回退 FunASR；模型版本/revision 如何 pin 以保证 eval 可复现（已有 `remote_model_acquisition.md`，但 spec 未引用）。
- 没有约定长会话（120s draft、连续多次会话）的内存增长/泄漏与 M4 热节流观测。

---

## 3. 修正版路线

> 原则：先把"唯一 gate + 真实后端适配器 + 真实录音语料 + 质量/延迟/内存硬门槛"全部钉死，再逐个后端进 gate；任何模型进 App 前必须跨真实进程边界并跑真实录音与真实控制流。

**Phase 0（新增，先决条件）— 总控 SDD spec + 决策锁定**
- 建立总控 spec：`specs/<date>-asr-backend-selection-roadmap/`，明确产出物：partial backend、final/long backend、fallback backend、reference-only models 各一组结论 + 进 App 门槛。
- 锁定：唯一 canonical gate = `incremental_ux_gate.py`；`qwen3_mlx_cumulative_service.py` 的 service gate 降级为 prototype 工具，其判定逻辑**收敛进** UX gate（避免两套真值）。
- 锁定：模型版本/revision pin 清单；真实录音语料清单（含技术术语 case）。

**Phase 1（重写）— 统一评测基座（含工程，不只是"采纳"）**
1. 给 `incremental_ux_gate.py` 增加**真实后端适配器**与**传输客户端**（localhost WS/HTTP），使其能驱动真实服务，而非只跑 fake。
2. 把 CER/WER 提升为 gate 的硬 fail 维度（阈值来自真实录音，见第 6 节），`final_coverage_ratio` 仅作"未截断/未丢失"下限。
3. 钉死 RTF 测量法：**计算 RTF 在 `--no-realtime` 模式测**；realtime 模式只用于测"是否实时跟得上 / 延迟是否随时长漂移"。
4. 扩充语料：在现有 10 例 + `long_120_001` 基础上，加入真实录音与术语 case；`run_eval.py` 保留为 file-level 质量 gate。
5. 验收：fake 自测继续通过；真实后端能跑通；两套 gate 收敛为一套。

**Phase 2 — Qwen3-ASR 0.6B MLX 真实本地服务边界**
- 常驻 Python 服务，模型只加载一次，localhost WS/HTTP 收 PCM chunk，输出 session events；**计算在后台线程**。
- 进**统一** gate（真实进程边界，非 in-process）。记录冷/热启动、稳态 RSS、120s draft 上的延迟漂移。

**Phase 3 — Qwen3-ASR 1.7B MLX 对照**
- 判断是否更适合 final/长文本 backend（CER/WER 更优但更慢更大）。同一 gate、同一语料对照。

**Phase 4 — MiMo-V2.5-ASR MLX final-only / 粗增量探针**
- final-only + 3s/5s coarse incremental probe。**用第 6 节的明确内存/延迟阈值判定**；不达标则降为 offline quality reference。

**Phase 5 — FunASR 2pass 保底基线**
- 保持默认。新模型必须在**统一 gate + 真实录音**上"明显超过"（量化标准见第 6 节），否则不替换默认路径。

**Phase 6 — 综合决策（产出四类结论）**
- 输出 partial / final / fallback / reference-only 的最终选择 + 证据指针，写入 `specs/progress.md`，结论提升进 PMB。

**Phase 7（新增）— 真实音频 + 控制流验证，然后才 Swift 集成**
- 真实麦克风采集、VAD/停顿分段、Right Option / Option+Space / Esc 控制流、运行时降级到 FunASR 的容错路径。
- 明确"不削弱现有 macOS 安全逻辑"（焦点检测、粘贴、剪贴板、不把 partial 写入输入框）为回归项。

---

## 4. 总控 SDD spec 应包含的要点

**requirements.md**
- 目标：在本地、离线、隐私安全约束下，选出 partial / final（长文本）/ fallback / reference-only 四类后端，并给出可复现证据。
- 明确"实时"定义采用用户澄清版（感知增量、可短延迟、停顿分段、滚动窗口、累计重算、停止后 final 修正；不要求逐字原生流式）。
- 硬约束（继承项目级）：本地运行、不上传、不改 InputMethodKit、默认不 LLM 纠偏、不自动发送、不把 partial 写入输入框、不削弱现有安全逻辑。
- 安全不变量（见第 6 节硬门槛）。
- 术语准确率与 hotword 需求显式列为需求项。

**plan.md**
- 七个 phase（见第 3 节），每个 phase 的产出物、依赖、所用脚本、所用语料、所写结果目录。
- 唯一 canonical gate 的工程改造项（真实适配器 + 传输 + CER/WER 硬维度 + RTF 测量法）。
- 运行时架构：常驻服务、模型单次加载、计算脱离摄入线程、崩溃/超时降级 FunASR。
- 模型版本 pin 与离线获取（引用 `remote_model_acquisition.md`）。

**validation.md**
- 区分硬门槛（必过，二值）与软门槛/人工复核信号（见第 6 节）。
- 每类后端的 pass 判据、所需 case 集（含真实录音、术语 case、120s draft、连续多会话）。
- RTF 在 no-realtime 模式测、延迟在 realtime 模式测的方法学固定下来。
- 内存/RSS、冷/热启动的具体数值阈值（草案缺，必须补）。
- 安全回归项：cancel 不泄漏、partial 不进输入框、final 才粘贴/复制、焦点不被抢。

**decisions.md**
- D1：canonical gate = `incremental_ux_gate.py`；service prototype gate 收敛入它。
- D2：partial backend 首选 Qwen3 0.6B MLX 累计重算 wrapper（待真实边界验证）。
- D3：first-partial 在短模式按"最小语音窗后"计，或降为软信号（见第 5 节冲突）。
- D4：质量用 CER/WER 硬门槛，coverage 仅作截断下限。
- D5：FunASR 替换标准量化。
- 未决：MiMo 是否能做 final-only（取决于内存/延迟实测）；1.7B 是否值得作为 final/长文本。

---

## 5. 模型候选：优先级 / 淘汰条件 / 进 App 门槛

### 优先级
| 角色 | 首选 | 备选 | 说明 |
|---|---|---|---|
| partial（浮窗增量） | Qwen3-ASR 0.6B MLX 累计重算 wrapper | （暂无原生 realtime 候选） | 唯一已证 in-process 可行的感知增量路径 |
| final / 长文本 | Qwen3-ASR 1.7B MLX | MiMo-V2.5-ASR MLX（若内存/延迟达标） | 1.7B CER/WER 更优；MiMo 文件级最佳但需证 final-only 稳态 |
| fallback / baseline | FunASR 2pass | — | 当前稳定保底，默认路径 |
| reference-only | MiMo（若不达标）、Fun-ASR-Nano、GLM-ASR-Nano、FireRedASR、Nemotron | — | 仅文件级参考，不进 App |

### 淘汰条件（任一触发即降级为 reference-only 或淘汰）
- 无法在**真实进程边界**上通过统一 gate 的安全不变量（硬门槛）。
- 真实录音上 CER/WER 未达硬阈值，或术语错误率不可接受。
- 稳态 RSS 超过内存硬门槛（MiMo 实测单发约 9.17GB、10 例命令级约 28.1GB，是高风险点）。
- 120s draft 上延迟随时长**漂移**（实时跟不上）。
- 本地无可行运行时（如官方 Qwen3 streaming 依赖 vLLM/CUDA，在 M4 未证可行 → 留作参考）。
- Nemotron：中文/技术术语质量已弱（CER 0.309），且无本地 session API → 明确低优先级。

### 进 App 的门槛（必须全部满足）
1. 通过统一 gate 全部**安全硬不变量**（真实进程边界，非 in-process）。
2. 真实录音 + 术语 case 上 CER/WER 达硬阈值。
3. 各模式延迟在硬上限内（短/长分别）。
4. 稳态 RSS 在硬上限内；冷/热启动有记录。
5. 真实麦克风 + 停顿分段 + Right Option/Option+Space/Esc 控制流验证通过。
6. 运行时降级 FunASR 的容错路径可用。
7. 不削弱任何现有 macOS 安全逻辑（回归通过）。
8. 证据写入 `specs/progress.md`，结论可复现（模型 revision pin）。

---

## 6. 阈值：硬门槛 vs 软门槛/人工复核

### 硬门槛（二值，必过，安全 + 功能正确性）
这些是 App 安全不变量，gate 已实现，应设为不可协商：
- 录音中至少 1 个 partial（仅对 partial 后端角色）。
- final 仅在用户停止后出现（无 final-before-stop）。
- final 之后无 partial（`partial_after_final = false`）。
- cancel 后无任何 accepted 输出（`accepted_output_after_cancel = false`）。
- 旧 session / token 不匹配事件不得被接受（`accepted_stale_event = false`）。

质量/性能硬门槛（**草案缺，必须补，且测量法固定**）：
- **CER/WER 硬阈值**：来自真实录音 + 术语 case（建议以 FunASR 2pass 当前真实录音表现为基线锚点设定具体数值，由项目用真实语料确定）。**应进 gate fail 维度**，目前未进。
- **稳态 RSS 上限**：给定 48GB 且需与用户其他工作共存，建议为 partial 服务设明确上限（具体数值由 0.6B 实测稳态确定，MiMo 的 ~9–28GB 是反例参照）。当前草案"只报告不判定"不可接受。
- **RTF**：在 `--no-realtime` 计算模式下测，partial 后端 `RTF <= 1.0`（计算余量）；另设"realtime 跟得上"硬项 = 120s draft 上延迟无单调漂移。**不要用 realtime 模式的 RTF≈1.0 当门槛。**

延迟（HARD 但**按模式**分开，且测量法 = realtime 模式）：
- short push-to-talk final latency `<= 2.5s`：合理（0.6B 实测 final 仅 137–603ms，门槛宽松，可接受）。
- long draft final latency `<= 8s`：合理。

### 软门槛 / 人工复核信号（不直接判 fail）
- **first partial latency `<= 1.5s`**：⚠️ 与所选方案冲突。累计重算短语音实测约 2078ms。建议：短模式下降为软信号，或改判据为"最小语音窗（如 1.5–2s 前缀）后出现首个 partial"。否则会误杀首选 partial 后端。
- **partial cadence `<= 1.5s`**：软，浮窗更新密度观测。
- **partial rewrite rate `<= 0.35`**：保持软（草案已正确标 soft）。累计重算的 rewrite 语义特殊，仅作浮窗稳定性人工复核。
- **final coverage ratio `>= 0.70`**：只能当"未截断/未丢失"的**下限保护**，**不能**当质量门槛（它是长度比，不是正确率）。质量交给 CER/WER 硬门槛。
- 冷启动时间：报告 + 软目标；热启动：软目标。

### 是否需要分短按/长文本模式：**需要**
- 短按（Right Option）与长文本（Option+Space）在 first-partial 容忍度、final 延迟上限、cadence 期望、累计重算窗口策略上都不同。所有延迟类阈值与 first-partial 判据应**分模式**，gate 应支持 mode 维度参数（当前 CLI 是单一阈值，需扩展）。

---

## 7. 一段可验收的阶段性 Goal（无歧义）

> **Phase 2 Goal（Qwen3-ASR 0.6B MLX 真实服务边界验证）**
>
> 交付一个独立于 Swift App 的常驻本地 Python 服务：进程启动时仅加载一次 `mlx-community/Qwen3-ASR-0.6B-8bit`（pin 到固定 revision），通过 localhost WebSocket 或 HTTP 接收 16kHz 单声道 PCM chunk，并发出 `start / partial / finish / final / cancel` session 事件，模型计算在独立于音频摄入的后台线程执行。
>
> 该服务必须通过**唯一 canonical gate**（`incremental_ux_gate.py`，经真实后端适配器 + 传输客户端跨真实进程边界驱动，非 in-process），在固定 case 集（现有 10 例 + `long_120_001` + 指定真实录音 + 术语 case，按 short 与 long 两种模式分别运行）上满足：
>
> 1. 全部安全硬不变量通过：录音中有 partial（short 模式）、final 仅在 stop 后、final 后无 partial、cancel 后无 accepted 输出、stale/旧 session 事件不被接受。
> 2. short 模式 final latency ≤ 2.5s，long 模式 final latency ≤ 8s（realtime 模式测）。
> 3. CER/WER 在真实录音与术语 case 上达到 validation.md 锁定的硬阈值；`final_coverage_ratio ≥ 0.70` 作截断下限。
> 4. 计算 RTF（`--no-realtime` 模式）≤ 1.0，且 `long_120_001` 上 final/partial 延迟不随时长单调漂移。
> 5. 稳态 RSS ≤ validation.md 锁定上限；冷启动与热启动时间被记录。
>
> 完成判据：上述 1–5 全部满足并在 `specs/progress.md` 留下可复现证据（结果目录 + 命令 + 模型 revision）；任一硬项不达标则不进入 Phase 3，且在 decisions.md 记录是回退 wrapper 设计还是降级该候选。**本 Goal 不包含 Swift App 集成，也不包含真实麦克风/控制流验证（属 Phase 7）。**

---

## 8. 风险、假设、权衡

**假设**
- 我把 `final_coverage_ratio` 理解为 `char_length_ratio`（长度比），依据 `run_eval.py:890`。
- 我把 realtime 模式 RTF≈1.0 的结论建立在 `run_gate_case` 中"每 chunk 后 `time.sleep(chunk_ms)`、run_wall 从 start 计到 finish"的代码路径上。
- 实测数字（首 partial 2078/1092ms、final 137/603ms、MiMo 9.17/28.1GB）取自 `runtime_feasibility.md`，未独立复跑。

**主要风险**
- R1（高）：若沿用草案 `first partial ≤ 1.5s` 硬门槛，会在短语音上误杀首选的 Qwen3 累计重算方案。→ 改软/改判据。
- R2（高）：质量无硬门槛 + coverage 是长度比 → 可能选出"长度对、内容错"的后端。→ CER/WER 入硬门槛。
- R3（中）：两套 gate 不收敛 → 各模型自证、无法横向比。→ Phase 1 收敛为一套。
- R4（中）：RTF 在 realtime 下不可信 → 性能结论失真。→ 固定测量法。
- R5（中）：MiMo 内存量级高，若无硬 RSS 上限可能被误选。→ 设上限。
- R6（中）：gate 不测真实音频/分段/控制流 → gate 过≠App 可用。→ 增 Phase 7。
- R7（低-中）：同步回放计时模型与异步服务不符 → 要求计算脱离摄入线程。

**权衡**
- 把 CER/WER 设为硬门槛会增加对"真实录音语料 + 标注"的依赖，前期成本上升，但避免选错后端的返工，值得。
- 收敛两套 gate 有一次性工程成本，但换来单一真值与可复现对比。

---

## 9. 建议的下一步（仅建议，不修改任何状态）

1. 先建总控 SDD spec（Phase 0），把 canonical gate、模型 pin、语料清单、硬/软门槛锁进 requirements/validation/decisions。
2. 重写 Phase 1：给 `incremental_ux_gate.py` 加真实后端 + 传输适配器，CER/WER 入硬维度，固定 RTF 测量法，收敛 service prototype gate。
3. 调整阈值：first-partial 短模式改软/改判据；补 CER/WER、RSS 的具体硬数值（由真实实测确定）；延迟分模式。
4. 在 Phase 6 之后、Swift 集成之前插入 Phase 7（真实音频 + 控制流 + 降级容错 + 安全回归）。

---

## Artifact paths:
/Users/xulelong/2025/projects/LocalVoiceInput/consult_briefs/20260622/claude-localvoiceinput-asr-backend-selection-roadmap-review-a5ef44fe/review.md
