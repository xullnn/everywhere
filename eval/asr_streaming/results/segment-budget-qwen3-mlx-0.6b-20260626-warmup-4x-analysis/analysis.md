# Segment Budget ASR Analysis

## Metric Notes

- `wall_ms`: 墙钟耗时，单位毫秒；这里近似等于本次 final 文件级识别真实等待时间。
- `rtf`: 实时因子，等于墙钟耗时除以音频时长；小于 1 表示处理速度快于实时播放。
- `cer`: 字符错误率，越低越好；中文主要看这个。
- `wer`: 词/token 错误率，越低越好；中英混合时辅助观察英文和技术词。
- `expected_chars`: 标准答案归一化后的字符数量，可粗略代表这段音频里需要转写的文字内容量。
- `final_chars`: 模型输出归一化后的字符数量。

## Case Results

| case | axis | audio sec | expected chars | final chars | wall ms | RTF | CER | WER | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| budget_repeat_2x_66s | more_text_longer_audio | 65.835 | 244 | 244 | 1177.2 | 0.018 | 0.008 | 0.008 | ok |
| budget_repeat_3x_99s | more_text_longer_audio | 98.752 | 366 | 366 | 1859.5 | 0.019 | 0.008 | 0.008 | ok |
| budget_repeat_4x_132s | more_text_longer_audio | 131.669 | 488 | 366 | 2181.1 | 0.017 | 0.256 | 0.256 | ok |
| budget_same_text_base_33s | same_text_base | 32.917 | 122 | 122 | 589.4 | 0.018 | 0.008 | 0.008 | ok |
| budget_same_text_pad_60s | same_text_longer_audio | 60.000 | 122 | 122 | 772.1 | 0.013 | 0.008 | 0.008 | ok |
| budget_same_text_pad_120s | same_text_longer_audio | 120.000 | 122 | 122 | 1240.7 | 0.010 | 0.008 | 0.008 | ok |
| budget_silence_33s | silence_duration_only | 32.917 | 0 | 1 | 259.9 | 0.008 | - | - | ok |
| budget_silence_60s | silence_duration_only | 60.000 | 0 | 1 | 419.2 | 0.007 | - | - | ok |
| budget_silence_120s | silence_duration_only | 120.000 | 0 | 0 | 767.1 | 0.006 | 0.000 | 0.000 | no_text |

## Comparisons

- `same_text_base`: {"case_count": 1, "duration_to_wall_ms_slope_ms_per_audio_sec": null, "max_duration_seconds": 32.917, "max_wall_ms": 589.4446540936113, "min_duration_seconds": 32.917, "min_wall_ms": 589.4446540936113}
- `same_text_longer_audio`: {"case_count": 2, "duration_to_wall_ms_slope_ms_per_audio_sec": 7.809913899594297, "max_duration_seconds": 120.0, "max_wall_ms": 1240.6955419573933, "min_duration_seconds": 60.0, "min_wall_ms": 772.1007079817355}
- `silence_duration_only`: {"case_count": 3, "duration_to_wall_ms_slope_ms_per_audio_sec": 5.82021263135861, "max_duration_seconds": 120.0, "max_wall_ms": 767.0780419139192, "min_duration_seconds": 32.917, "min_wall_ms": 259.86466696485877}
- `more_text_longer_audio`: {"case_count": 3, "duration_to_wall_ms_slope_ms_per_audio_sec": 15.249716261879357, "max_duration_seconds": 131.669, "max_wall_ms": 2181.140191646838, "min_duration_seconds": 65.835, "min_wall_ms": 1177.1903712622723}
- `overall`: {"duration_to_wall_ms_slope_ms_per_audio_sec": 12.461256197364078, "text_length_to_wall_ms_slope_ms_per_char": 3.53726501320914}

## Quality Warnings

- budget_repeat_4x_132s 输出覆盖率只有 366/488，说明这次 final 识别没有完整覆盖标准答案。
- budget_repeat_4x_132s CER=0.2561，明显高于可接受的普通听写水平。
- 这些警告优先级高于耗时指标：一个很快但漏掉末尾内容的 final，不能作为可用的长段重算策略。

## Recommendation

- budget_repeat_4x_132s 输出覆盖率只有 366/488，说明这次 final 识别没有完整覆盖标准答案。
- budget_repeat_4x_132s CER=0.2561，明显高于可接受的普通听写水平。
- 这些警告优先级高于耗时指标：一个很快但漏掉末尾内容的 final，不能作为可用的长段重算策略。
- 同样文字后面补静音仍然会增加处理耗时，所以不能只按已转写文字长度切段。
- 纯静音随时长变长也有可见成本，说明音频时长本身就是必须受控的资源。
- 重复内容组的耗时增长高于补静音组，说明文字/内容量也会带来额外成本。
- 建议后续分段采用混合预算：硬性音频时长上限 + 软性文字长度上限 + 静音/标点边界优先切分，而不是只用两分钟或只用字数。
- 这组是 compute-isolation pilot；最终产品阈值还需要至少重复跑 2-3 次，并加入自然长语音样本。
