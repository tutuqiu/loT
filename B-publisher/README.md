# 给 PyQt 端的对接说明：如何控制 B-publisher/publish.py

## 1. 脚本定位

该脚本负责从本地数据文件读取传感器数据，并按指定 `metric + rate + 时间区间` 发布到 MQTT：

* Broker：`139.224.237.20:1883`
* Topic：`ingest/env/{metric}`，其中 `metric ∈ {temperature, humidity, pressure}`
* Payload：

```json
{"ts":"YYYY-MM-DDTHH:MM:SS","value": number|null}
```

脚本支持运行中控制：暂停 / 恢复 / 停止 / 动态改 rate（通过 stdin 命令）。

---

## 2. 运行方式（命令行参数）

脚本参数为**可选参数形式**（不是位置参数）：

```bash
python B-publisher/publish.py --metric <metric> --rate <rate_hz> [--start <start_ts>] [--end <end_ts>]
```

### 参数说明

* `--metric` / `-m`（必填）：`temperature | humidity | pressure`
* `--rate` / `-r`（必填）：浮点数，Hz（每秒发送条数）
* `--start` / `-s`（可选）：起始时间（包含），格式 `YYYY-MM-DDTHH:MM:SS`
* `--end` / `-e`（可选）：终止时间（包含），格式 `YYYY-MM-DDTHH:MM:SS`

### 示例

1）发布 temperature，1Hz，全量：

```bash
python B-publisher/publish.py -m temperature -r 1
```

2）发布 humidity，2Hz，仅发布指定区间：

```bash
python B-publisher/publish.py -m humidity -r 2 -s "2014-02-20T08:20:00" -e "2014-02-20T10:00:00"
```

> 时间过滤基于 `ts` 字符串比较（ISO 格式），要求输入格式严格一致。

---

## 3. 运行时控制（stdin 命令）

脚本运行后会开启控制线程读取 stdin（每条命令一行，必须带换行 `\n`）：

* 暂停发送：

```
pause
```

* 恢复发送（恢复时会重置调度，避免“追赶补发”）：

```
resume
```

* 动态修改速率（Hz）：

```
rate 5
```

* 停止并退出（优雅断开连接）：

```
stop
```

> PyQt 端通过 `QProcess.write(b"...\n")` 向脚本 stdin 写入上述命令即可控制。

---

## 4. PyQt 端如何启动脚本（QProcess）

推荐用当前解释器启动，避免环境不一致：

```python
import sys
from PyQt5.QtCore import QProcess

self.proc = QProcess(self)
self.proc.setProcessChannelMode(QProcess.MergedChannels)  # 合并 stdout+stderr

# 读取输出日志
self.proc.readyRead.connect(self.on_output)

program = sys.executable
args = [
    "B-publisher/publish.py",
    "--metric", metric,
    "--rate", str(rate),
]

# 如果用户填写了 start/end，再追加
if start_ts:
    args += ["--start", start_ts]
if end_ts:
    args += ["--end", end_ts]

self.proc.start(program, args)
```

读取日志示例：

```python
def on_output(self):
    text = bytes(self.proc.readAll()).decode("utf-8", errors="ignore")
    self.logTextEdit.append(text.rstrip())
```

---

## 5. PyQt 端如何实现 Start / Pause / Resume / Stop

### Start

* 使用上面 QProcess 启动即可
* 建议 Start 前检查：进程是否已在运行；运行中则先 Stop 或禁用 Start

### Pause

```python
if self.proc.state() != QProcess.NotRunning:
    self.proc.write(b"pause\n")
```

### Resume

```python
if self.proc.state() != QProcess.NotRunning:
    self.proc.write(b"resume\n")
```

### 动态改 rate（可选按钮/输入框）

```python
hz = 5
self.proc.write(f"rate {hz}\n".encode("utf-8"))
```

### Stop（优雅退出 + 兜底）

```python
if self.proc.state() != QProcess.NotRunning:
    self.proc.write(b"stop\n")
    self.proc.waitForFinished(2000)
    if self.proc.state() != QProcess.NotRunning:
        self.proc.terminate()
        self.proc.waitForFinished(1000)
        if self.proc.state() != QProcess.NotRunning:
            self.proc.kill()
```

---

## 6. GUI 控件与脚本参数映射建议

* metric 下拉框：temperature / humidity / pressure
* rate 输入框：double（范围如 0.1 ~ 50）
* start / end：文本输入框（格式必须是 `YYYY-MM-DDTHH:MM:SS`；空则不传参）
* 按钮：Start / Pause / Resume / Stop
* 日志窗口：显示脚本输出（连接成功、topic、时间区间、payload 等）

---

## 7. 输出格式（用于 GUI 展示）

脚本会输出类似：

* 连接信息：`正在连接...`、`✓ 已连接到 Broker`
* topic：`发布主题: ingest/env/temperature`
* 时间区间：

  * 全量：`时间区间：全部`
  * 半区间：`时间区间：2014-... ~ /` 或 `时间区间：/ ~ 2014-...`
* 控制事件：`|| paused`、`|| resumed`、`|| rate set to ...`、`|| stopping`
* 每条消息：`Payload: {...}`
* 结束：`✓ 完成`

---

## 8. 注意事项

1. stdin 命令必须带换行 `\n`（脚本用 `sys.stdin.readline()` 读取）。
2. 如果 GUI 日志显示延迟：确保脚本 `print(..., flush=True)`（你控制命令部分已 flush）。
3. `--start/--end` 必须是 ISO 格式字符串；否则过滤可能不符合预期。
---
