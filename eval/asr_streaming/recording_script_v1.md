# Local ASR Recording Script v1

Use this script to create the first reproducible local ASR evaluation set.

Recording rules:

- Record one audio file per case.
- Read exactly the text after `Text:`.
- Use a normal dictation speed first; do not over-enunciate.
- Keep file names exactly aligned with the case id, for example `zh_short_001.m4a`.
- Put raw recordings in `eval/asr_streaming/local_raw/`.
- Convert final evaluation WAV files into `eval/asr_streaming/audio/`.

## Pilot Set

Record these 10 cases first. Do not continue to the extended set until the conversion and baseline run are working.

This pilot intentionally includes long-form cases because real usage may contain hundreds of Chinese characters in one dictation session.

### zh_short_001

Text: 我想要做一个本地离线的中文语音输入工具。

### mix_tech_001

Text: 这个项目需要支持 FunASR、Qwen3-ASR 和 MacBook Pro。

### hotword_001

Text: LocalVoiceInput 的核心模块包括 FocusDetector、PasteEngine 和 TranscriptBuffer。

### punctuation_001

Text: 嗯，我想说一下，就是这个功能最好能够自动补标点。

### zh_numbers_001

Text: 二零二六年五月十三日，我在测试语音输入的数字规整能力。

### safety_001

Text: 密码框和安全输入框永远不应该自动粘贴，只能复制到剪切板。

### long_120_001

Text: 我希望这个应用能够作为一个长期使用的本地语音输入工具。它首先要保证隐私和安全，所有音频和文本都应该留在本机。其次，它要在不同软件里保持一致的体验，用户按住快捷键开始说话，松开以后看到最终文本被粘贴或者复制。最后，它不能因为识别失败、焦点变化或者粘贴失败而丢失内容。

### long_200_001

Text: 现在我们要测试一段更接近真实使用的长文本输入。我可能会连续说一两分钟，中间有停顿，也可能会临时修改说法。模型需要持续输出稳定的实时转写，不能在收到中途的离线片段时提前结束整个会话。等我真正停止录音以后，它才应该给出最终结果。如果当前输入框仍然安全可用，就自动粘贴；如果焦点变化、目标不可编辑或者粘贴无法确认，就把结果保留在剪切板。

### long_400_001

Text: 我想完整描述一下这个项目的目标和测试思路。LocalVoiceInput 是一个本地优先的 macOS 语音输入工具，它不是云端听写服务，也不是当前阶段的 InputMethodKit 输入法。用户在任意应用里按住右 Option 开始说话，松开后停止录音，系统把最终文本粘贴到当前光标位置；如果没有可用输入框，就复制到剪切板。为了选择更好的语音识别模型，我们不能只看公开榜单，也不能每次都靠人工随便念几句。我们需要固定的录音脚本、标准答案、可重复的音频文件和统一的评测指标。评测时要关注中文准确率、中英混合、技术名词、长文本稳定性、首个 partial 延迟、最终延迟、实时因子、内存占用，以及模型在本机离线运行时是否稳定。只有当新的后端在这些方面明显优于当前 Paraformer 基线时，我们才考虑把它接入真实应用。

### long_code_switch_001

Text: 这是一段中英混合的长文本测试，用来观察模型对 technical terms 和 product names 的处理能力。我们会比较 Paraformer、Fun-ASR-Nano、Qwen3-ASR 和 MiMo-V2.5-ASR。评测 harness 会记录 first partial latency、final latency、CER、WER、realtime factor、partial event count 和 final event count。真实产品里还会涉及 FocusDetector、PasteEngine、ClipboardManager、TranscriptBuffer、WebSocket client 和 AVAudioEngine。模型不仅要识别中文，还要准确保留 Swift Package、LocalVoiceInput、MacBook Pro、Chrome、Cursor、Obsidian、Notion、ChatGPT 这些词。

## Extended Set

After the pilot passes, record these additional cases.

### zh_short_002

Text: 这个工具需要在任意软件里通过全局快捷键唤起。

### zh_clipboard_001

Text: 当前没有输入框的时候，应该自动复制到剪切板。

### zh_paste_001

Text: 如果当前在微信输入框中，松开快捷键以后应该自动粘贴。

### zh_safety_001

Text: 如果识别失败，也不能丢失内容，至少要复制到剪切板。

### mix_tech_002

Text: 这里有一些中英混合内容，比如 Swift Package、WebSocket 和 Clipboard Manager。

### long_draft_001

Text: 请帮我把这个需求整理成一个清晰的项目执行计划，先说明目标，再列出阶段，然后给出每个阶段的验证方式。

### zh_short_003

Text: 我今天主要想测试语音输入的稳定性和准确率。

### zh_short_004

Text: 这是一段普通中文输入，用来观察模型是否会漏字或者改字。

### zh_short_005

Text: 请把这句话转换成最终文本，然后自动放到当前光标位置。

### zh_long_001

Text: 我希望这个应用能够长期作为我的本地语音输入工具使用，它需要足够快，足够安全，并且不能把音频或者文本上传到云端。

### zh_long_002

Text: 当前阶段我们不做真正的输入法重构，只需要保证浮窗显示实时转写，最终文本再粘贴或者复制。

### zh_long_003

Text: 如果用户在录音期间切换了应用，最终输出应该降级为复制到剪切板，而不是强行粘贴到新的窗口里。

### zh_numbers_002

Text: 这个测试包含一百二十三个样本，平均延迟需要低于八百毫秒。

### zh_numbers_003

Text: 请在下午三点半提醒我查看第十二条测试结果。

### mix_code_001

Text: 我们需要比较 Paraformer、Fun-ASR-Nano 和 Qwen3-ASR 的实时识别效果。

### mix_code_002

Text: 这个 backend harness 会记录 first partial latency、final latency、CER、WER 和 realtime factor。

### mix_code_003

Text: 请检查 cases.local.jsonl 里面的 audio、text、lang 和 scenario 字段。

### mix_code_004

Text: 如果 WebSocket server 没有启动，run_eval.py 应该返回清晰的错误信息。

### mix_code_005

Text: 我们暂时不要默认启用 LLM correction，也不要自动发送消息。

### app_names_001

Text: 我经常在 Apple Notes、Cursor、VS Code、Obsidian 和 Notion 里面使用语音输入。

### app_names_002

Text: 请在 Chrome 的 ChatGPT 输入框里测试中文和英文混合输入。

### app_names_003

Text: 如果是在 Finder 重命名文件，也要避免误粘贴和污染剪切板。

### safety_002

Text: 粘贴失败的时候，语音结果必须保留在剪切板，不能恢复旧剪切板。

### safety_003

Text: 自动粘贴成功以后，原来的剪切板内容应该被恢复。

### safety_004

Text: 按下 Escape 取消录音以后，不应该复制，也不应该粘贴。

### correction_001

Text: 语音识别结果里面的 fun asr 应该被纠正成 FunASR。

### correction_002

Text: 语音识别结果里面的 qwen 三应该被纠正成 Qwen3。

### correction_003

Text: 这里测试同音词纠错，比如玄界芯片应该写成玄戒芯片。

### low_voice_001

Text: 这是一段低声说话的测试，用来观察模型对小音量的识别能力。

### fast_speech_001

Text: 这是一段稍微快一点的语音输入测试，看看模型能不能跟上我的正常语速。

### noisy_001

Text: 现在环境里有一点背景噪声，我想测试模型是否还能稳定识别。

### filler_001

Text: 嗯，我觉得吧，这个功能其实最重要的是不要打断我当前的输入流程。

### filler_002

Text: 就是说，如果它能稳定运行，我就可以在很多应用里直接使用语音输入。

### draft_001

Text: 请帮我起草一段项目说明，强调本地运行、隐私保护、跨应用输入和安全降级。

### draft_002

Text: 我想写一段比较长的内容，先讲目标，再讲技术方案，最后讲当前还需要验证的问题。

### english_001

Text: This is a short English dictation test for LocalVoiceInput.

### english_002

Text: The backend should measure latency, accuracy, and streaming stability.

### english_mix_001

Text: 我们需要一个 local first voice input tool，而不是 cloud based dictation service。

### english_mix_002

Text: 请把 automatic speech recognition、clipboard restore 和 focus detection 这几个词识别准确。

### command_like_001

Text: 请创建一个新的测试用例，然后把结果保存到 eval 目录。

### command_like_002

Text: 帮我总结一下今天的测试结果，并列出下一步最值得做的事情。

### edge_pause_001

Text: 这句话中间会停顿一下，然后继续说完后面的内容。

### edge_repeat_001

Text: 我重复一遍，自动粘贴成功以后，原剪切板应该恢复。

### edge_correction_001

Text: 如果前半句识别错了，离线最终结果应该能够修正句尾内容。

### final_decision_001

Text: 如果新的模型在延迟和准确率上都明显更好，我们再考虑把它接入应用。
