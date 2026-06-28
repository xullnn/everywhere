# Segmented Cache ASR Analysis

## Metric Notes

- `segment_count`: 分段数量。数量越多，单段更短，但总调用次数更多。
- `total_segment_audio_sec`: 所有分段音频时长之和。启用重叠时会大于原始音频时长。
- `total_model_wall_ms`: 所有分段识别真实耗时相加，单位毫秒。它表示模型总工作量，不等于用户停止后的等待时间。
- `max_segment_wall_ms`: 最慢单个分段识别耗时，单位毫秒。它影响后台处理能否追上用户说话。
- `serial_final_wait_ms`: 假设只有一个后台模型 worker，用户说完后还需要等待多久才能拿到全部已提交分段的最终结果。
- `serial_max_lag_ms`: 假设一个后台模型 worker 时，分段处理完成时间落后于对应音频结束时间的最大值。越大表示后台越积压。
- `cer`: 字符错误率，越低越好。这里按拼接后的全部分段文本对比原始整段标准答案。
- `wer`: 词或 token 错误率，越低越好。中文近似按单字 token，英文/数字/符号按连续 token。
- `coverage`: 输出覆盖率，等于拼接输出归一化字符数除以标准答案归一化字符数。过低通常表示漏尾或漏段。
- `strategy`: 切段策略，格式包含硬性音频时长上限、软文字预算和重叠秒数。

## Strategy Summary

| strategy | cases | pass candidates | avg CER | min coverage | max final wait ms | max backlog ms | max segments |
|---|---:|---:|---:|---:|---:|---:|---:|
| s30_c150_o0 | 1 | 1 | 0.0226 | 1.003 | 98.8 | 596.6 | 9 |
| s45_c250_o0 | 1 | 1 | 0.0278 | 1.003 | 328.8 | 804.1 | 6 |
| s60_c250_o0 | 1 | 1 | 0.0257 | 1.002 | 104.1 | 1065.0 | 5 |
| s90_c400_o0 | 1 | 1 | 0.0257 | 1.004 | 1237.2 | 1825.8 | 3 |

## Case Strategy Results

| source case | strategy | segments | total model wall ms | max segment wall ms | final wait ms | backlog ms | CER | WER | coverage | status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| synthetic_repeat_180_001 | s30_c150_o0 | 9 | 4344.4 | 596.6 | 98.8 | 596.6 | 0.0226 | 0.0452 | 1.003 | pass |
| synthetic_repeat_180_001 | s45_c250_o0 | 6 | 4259.4 | 804.1 | 328.8 | 804.1 | 0.0278 | 0.0513 | 1.003 | pass |
| synthetic_repeat_180_001 | s60_c250_o0 | 5 | 4254.4 | 1065.0 | 104.1 | 1065.0 | 0.0257 | 0.0513 | 1.002 | pass |
| synthetic_repeat_180_001 | s90_c400_o0 | 3 | 4741.3 | 1825.8 | 1237.2 | 1825.8 | 0.0257 | 0.0513 | 1.004 | pass |

## Recommendation

- 本次小样本中 `s30_c150_o0` 是最稳的候选：所有 case 通过阈值，最大停止后等待约 99ms。
- 当前结果仍是离线分段评测，不代表 macOS App 已经支持分段缓存运行时。
- 下一步应扩大到自然长语音和更长合成压力样本，再把通过的策略转成服务侧实现 spec。
