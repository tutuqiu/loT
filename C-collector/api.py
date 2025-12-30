#!/usr/bin/env python3
"""
FastAPI HTTP API for C-collector

提供 3 个只读接口，完全遵守项目契约：
1) GET /api/realtime?metric=temperature&limit=200
2) GET /api/history?metric=temperature&from=...&to=...
3) GET /api/stats?metric=temperature&from=...&to=...

说明：
- metric 仅允许 temperature / humidity / pressure
- ts 字段使用 SQLite 中原始的 TEXT 时间戳 (YYYY-MM-DDTHH:MM:SS)
- NULL 不参与 min/max/mean 统计；missing 单独计数
"""

from typing import List, Optional, Literal

import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from collector import init_database, DB_PATH  # 复用采集器里的 DB 配置与建表逻辑


Metric = Literal["temperature", "humidity", "pressure"]

app = FastAPI(title="IoT Collector API", version="1.0.0")

# 如有需要，允许本机或前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection() -> sqlite3.Connection:
    """创建一个新的 SQLite 连接（每个请求一个，避免线程问题）"""
    conn = sqlite3.connect(DB_PATH)
    # 返回 dict-like 行，便于字段访问
    conn.row_factory = sqlite3.Row
    return conn


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时确保数据库已初始化"""
    init_database()


@app.get("/api/realtime")
def get_realtime(
    metric: Metric = Query(..., description="metric=temperature|humidity|pressure"),
    limit: int = Query(200, ge=1, le=2000, description="返回的最大点数（默认 200）"),
):
    """
    实时数据：按时间倒序取最近 N 条，再按时间正序返回
    响应结构：
    {
      "metric": "temperature",
      "points": [{"ts": "...", "value": 11.0}, ...]
    }
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ts, value
            FROM measurements
            WHERE metric = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            (metric, limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    # 需要按时间升序返回
    points = [
        {"ts": row["ts"], "value": row["value"]} for row in reversed(rows)
    ]

    return {"metric": metric, "points": points}


@app.get("/api/history")
def get_history(
    metric: Metric = Query(..., description="metric=temperature|humidity|pressure"),
    from_ts: Optional[str] = Query(None, alias="from", description="起始时间（含），YYYY-MM-DDTHH:MM:SS"),
    to_ts: Optional[str] = Query(None, alias="to", description="结束时间（含），YYYY-MM-DDTHH:MM:SS"),
):
    """
    历史数据：按时间范围查询并按时间升序返回
    响应结构与 /api/realtime 相同。
    """
    if from_ts is None and to_ts is None:
        raise HTTPException(status_code=400, detail="至少需要提供 from 或 to 参数")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        conditions = ["metric = ?"]
        params: List[object] = [metric]

        if from_ts is not None:
            conditions.append("ts >= ?")
            params.append(from_ts)
        if to_ts is not None:
            conditions.append("ts <= ?")
            params.append(to_ts)

        where_sql = " AND ".join(conditions)

        sql = f"""
            SELECT ts, value
            FROM measurements
            WHERE {where_sql}
            ORDER BY ts ASC
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    points = [{"ts": row["ts"], "value": row["value"]} for row in rows]
    return {"metric": metric, "points": points}


@app.get("/api/stats")
def get_stats(
    metric: Metric = Query(..., description="metric=temperature|humidity|pressure"),
    from_ts: Optional[str] = Query(None, alias="from", description="起始时间（含），YYYY-MM-DDTHH:MM:SS"),
    to_ts: Optional[str] = Query(None, alias="to", description="结束时间（含），YYYY-MM-DDTHH:MM:SS"),
):
    """
    统计数据：
    {
      "metric": "temperature",
      "count": 100,
      "missing": 5,
      "min": 1.0,
      "max": 10.0,
      "mean": 5.5
    }

    规则：
    - NULL 不参与 min/max/mean
    - missing = 总记录数 - 有效值记录数
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        conditions = ["metric = ?"]
        params: List[object] = [metric]

        if from_ts is not None:
            conditions.append("ts >= ?")
            params.append(from_ts)
        if to_ts is not None:
            conditions.append("ts <= ?")
            params.append(to_ts)

        where_sql = " AND ".join(conditions)

        sql = f"""
            SELECT
              COUNT(*) AS total_count,
              COUNT(value) AS non_null_count,
              MIN(value) AS min_val,
              MAX(value) AS max_val,
              AVG(value) AS avg_val
            FROM measurements
            WHERE {where_sql}
        """
        cur.execute(sql, params)
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        # 理论上不会发生，除非表不存在
        raise HTTPException(status_code=500, detail="统计查询失败")

    total = row["total_count"] or 0
    non_null = row["non_null_count"] or 0
    missing = int(total - non_null)

    # min/max/mean 在无有效值时保持为 None
    min_val = row["min_val"]
    max_val = row["max_val"]
    avg_val = row["avg_val"]

    return {
        "metric": metric,
        "count": int(total),
        "missing": missing,
        "min": min_val,
        "max": max_val,
        "mean": avg_val,
    }


if __name__ == "__main__":
    # 方便本地调试：python api.py
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)


