#!/usr/bin/env python3
"""
验证脚本 - 用于检查数据库内容和统计信息
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = "data/measurements.db"

def check_database():
    """检查数据库状态"""
    
    if not Path(DB_PATH).exists():
        print(f"✗ 数据库文件不存在: {DB_PATH}")
        print("  请先运行 collector.py 启动采集器")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=" * 70)
        print("🔍 数据库验证报告")
        print("=" * 70)
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='measurements'
        """)
        if not cursor.fetchone():
            print("✗ measurements表不存在")
            return False
        print("✓ measurements表存在")
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM measurements")
        total = cursor.fetchone()[0]
        print(f"\n📊 总记录数: {total}")
        
        if total == 0:
            print("\n⚠ 数据库为空，可能的原因：")
            print("  1. Publisher还未开始发送数据")
            print("  2. MQTT连接配置不正确")
            print("  3. Topic订阅不匹配")
            return True
        
        # 按指标统计
        print("\n" + "-" * 70)
        print("📈 各指标详细统计")
        print("-" * 70)
        
        cursor.execute('''
            SELECT metric, 
                   COUNT(*) as total_count,
                   COUNT(value) as valid_count,
                   COUNT(*) - COUNT(value) as null_count,
                   MIN(value) as min_val,
                   MAX(value) as max_val,
                   AVG(value) as avg_val,
                   MIN(ts) as first_ts,
                   MAX(ts) as last_ts
            FROM measurements
            GROUP BY metric
            ORDER BY metric
        ''')
        
        rows = cursor.fetchall()
        for row in rows:
            metric, total_count, valid_count, null_count, min_val, max_val, avg_val, first_ts, last_ts = row
            
            print(f"\n【{metric.upper()}】")
            print(f"  总记录数    : {total_count}")
            print(f"  有效数据    : {valid_count} ({valid_count/total_count*100:.1f}%)")
            print(f"  缺失数据    : {null_count} ({null_count/total_count*100:.1f}%)")
            
            if min_val is not None:
                print(f"  最小值      : {min_val:.2f}")
                print(f"  最大值      : {max_val:.2f}")
                print(f"  平均值      : {avg_val:.2f}")
            
            print(f"  时间范围    : {first_ts} ~ {last_ts}")
        
        # 最近10条记录
        print("\n" + "-" * 70)
        print("📝 最近10条记录")
        print("-" * 70)
        
        cursor.execute('''
            SELECT metric, ts, value, received_at
            FROM measurements
            ORDER BY received_at DESC
            LIMIT 10
        ''')
        
        rows = cursor.fetchall()
        for i, (metric, ts, value, received_at) in enumerate(rows, 1):
            value_str = f"{value:.2f}" if value is not None else "NULL"
            print(f"{i:2d}. [{metric:11s}] {ts} = {value_str:>8s} (收到于: {received_at})")
        
        # 检查数据连续性
        print("\n" + "-" * 70)
        print("🔄 数据连续性检查")
        print("-" * 70)
        
        for metric in ['temperature', 'humidity', 'pressure']:
            cursor.execute('''
                SELECT COUNT(*) FROM measurements WHERE metric = ?
            ''', (metric,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"✓ {metric:11s}: {count} 条记录")
            else:
                print(f"✗ {metric:11s}: 无数据")
        
        print("\n" + "=" * 70)
        print("✓ 验证完成")
        print("=" * 70)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if check_database():
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

