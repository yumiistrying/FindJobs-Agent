#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
岗位数据处理流水线

完整流程：
1. 爬取原始岗位数据 (job_crawler_v2.py)
2. 智能分析提取 (job_agent.py) - 使用LLM提取学历、技能、评分等
3. 生成网站可用数据
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

ROOT_DIR = Path(__file__).parent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner(text: str):
    """打印横幅"""
    width = 60
    print(f"\n{'='*width}")
    print(f"  {text}")
    print(f"{'='*width}\n")


def backup_existing_data():
    """备份现有数据"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    raw_file = ROOT_DIR / 'crawled_jobs_raw.json'
    if raw_file.exists():
        backup = ROOT_DIR / f'backup/crawled_jobs_raw_{timestamp}.json'
        backup.parent.mkdir(exist_ok=True)
        shutil.copy(raw_file, backup)
        logger.info(f"📦 备份原始数据: {backup.name}")
    
    enriched_file = ROOT_DIR / 'jobs_enriched.csv'
    if enriched_file.exists():
        backup = ROOT_DIR / f'backup/jobs_enriched_{timestamp}.csv'
        backup.parent.mkdir(exist_ok=True)
        shutil.copy(enriched_file, backup)
        logger.info(f"📦 备份分析数据: {backup.name}")


def step1_crawl_jobs(companies: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    步骤1: 爬取原始岗位数据
    """
    print_banner("步骤 1/3: 爬取原始岗位数据")
    
    cmd = [
        sys.executable,
        str(ROOT_DIR / 'job_crawler_v2.py'),
        '-f', 'crawled_jobs_raw.json'
    ]
    
    # ==========================================
    # 🚀 核心修改区域：注入城市与岗位关键词，取消固定公司限制
    # ==========================================
    target_cities = ["常州", "芜湖", "嘉兴", "慈溪", "湖州", "无锡"]
    # 加入 "校招" 或 "2027" 确保匹配你的应届生身份
    target_keywords = ["数据分析", "数字化运营", "市场企划", "出海", "管培生", "校招"]
    
    # 假设爬虫脚本接收 --city 和 --keyword 参数 (用逗号分隔)
    cmd.extend(['--city', ','.join(target_cities)])
    cmd.extend(['--keyword', ','.join(target_keywords)])
    
    # 如果命令行依然手动传入了具体公司，则追加搜索
    if companies:
        cmd.extend(['-c'] + companies)
    # ==========================================
    
    logger.info(f"运行爬虫: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    
    raw_file = ROOT_DIR / 'crawled_jobs_raw.json'
    if raw_file.exists():
        with open(raw_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
        logger.info(f"✅ 爬取完成: {len(jobs)} 个原始岗位")
        return {'success': True, 'count': len(jobs), 'file': str(raw_file)}
    else:
        logger.error("❌ 爬取失败: 未生成输出文件")
        return {'success': False, 'count': 0}


def step2_analyze_with_llm(max_jobs: Optional[int] = None) -> Dict[str, Any]:
    """
    步骤2: 使用LLM智能分析（调用job_agent.py）
    """
    print_banner("步骤 2/3: LLM智能分析提取")
    
    raw_file = ROOT_DIR / 'crawled_jobs_raw.json'
    if not raw_file.exists():
        logger.error("❌ 未找到原始数据文件")
        return {'success': False}
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    
    total_jobs = len(jobs)
    logger.info(f"📊 待分析岗位总数: {total_jobs}")
    
    if max_jobs and max_jobs < total_jobs:
        logger.info(f"⚠️  将只分析前 {max_jobs} 个岗位")
        jobs = jobs[:max_jobs]
        temp_file = ROOT_DIR / 'temp_jobs_for_analysis.json'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        input_file = temp_file
    else:
        input_file = raw_file
    
    output_file = ROOT_DIR / 'jobs_enriched.csv'
    
    cmd = [
        sys.executable,
        str(ROOT_DIR / 'job_agent.py'),
        '--jobs-file', str(input_file),
        '--output-file', str(output_file),
        '--min-skills', '3',
        '--max-skills', '10',
        '--max-workers', '5',
    ]
    
    logger.info("运行智能分析: job_agent.py")
    logger.info("🤖 正在调用LLM分析...")
    
    try:
        result = subprocess.run(cmd, cwd=str(ROOT_DIR), timeout=7200)
        
        if output_file.exists():
            import pandas as pd
            df = pd.read_csv(output_file)
            has_skills = df['skill_tags'].notna().sum()
            
            logger.info("✅ 智能分析完成")
            logger.info(f"   - 总岗位数: {len(df)}")
            
            try:
                import storage
                written = storage.upsert_jobs(
                    ROOT_DIR / 'jobs.db', df.fillna("").to_dict("records")
                )
                logger.info(f"   - 已同步 {written} 个岗位到 jobs.db")
            except Exception as exc:
                logger.warning(f"   - 同步 jobs.db 失败: {exc}")
            
            return {'success': True, 'count': len(df), 'file': str(output_file)}
        else:
            logger.error("❌ 分析失败: 未生成输出文件")
            return {'success': False}
            
    except subprocess.TimeoutExpired:
        logger.error("❌ 分析超时")
        return {'success': False}
    except Exception as e:
        logger.error(f"❌ 分析失败: {e}")
        return {'success': False}


def step3_prepare_for_website() -> Dict[str, Any]:
    """
    步骤3: 准备网站数据
    """
    print_banner("步骤 3/3: 准备网站数据")
    
    enriched_csv = ROOT_DIR / 'jobs_enriched.csv'
    output_json = ROOT_DIR / 'all_companies_jobs.json'
    
    if not enriched_csv.exists():
        raw_json = ROOT_DIR / 'crawled_jobs_raw.json'
        if raw_json.exists():
            shutil.copy(raw_json, output_json)
            with open(output_json, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
            return {'success': True, 'count': len(jobs), 'enriched': False}
        return {'success': False}
    
    import pandas as pd
    df = pd.read_csv(enriched_csv)
    
    jobs = []
    for _, row in df.iterrows():
        job = {
            'company_name': str(row.get('company_name', '')),
            'job_title': str(row.get('job_title', '')),
            'job_id': str(row.get('job_id', '')),
            'category': str(row.get('category', '')),
            'location': str(row.get('location', '')),
            'job_type': str(row.get('job_type', '')),
            'special_program': str(row.get('special_program', '')),
            'job_description': str(row.get('job_description', '')),
            'job_requirements': str(row.get('job_requirements', '')),
            'apply_url': str(row.get('apply_url', '')),
            'source_url': str(row.get('source_url', '')),
            'min_degree': str(row.get('min_degree', '')),
            'degree_priority': str(row.get('degree_priority', '')),
            'major_requirement': str(row.get('major_requirement_text', '')),
            'skill_tags': str(row.get('skill_tags', '')),
            'job_level1': str(row.get('job_level1', '')),
            'job_level2': str(row.get('job_level2', '')),
        }
        jobs.append(job)
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 网站数据已更新: {output_json.name} ({len(jobs)} 个)")
    return {'success': True, 'count': len(jobs), 'enriched': True}


def show_next_steps():
    print_banner("下一步操作")
    print("数据更新完成！可重启前端服务查看。")


def main():
    parser = argparse.ArgumentParser(description='岗位数据处理流水线')
    parser.add_argument('-c', '--companies', nargs='*', default=None, help='指定要爬取的公司')
    parser.add_argument('--crawl-only', action='store_true')
    parser.add_argument('--analyze-only', action='store_true')
    parser.add_argument('--max-jobs', type=int, default=None)
    parser.add_argument('--no-backup', action='store_true')
    args = parser.parse_args()
    
    print_banner("岗位数据处理流水线")
    
    if not args.no_backup:
        backup_existing_data()
    
    if args.analyze_only:
        result2 = step2_analyze_with_llm(args.max_jobs)
        if result2['success']: step3_prepare_for_website()
    elif args.crawl_only:
        step1_crawl_jobs(args.companies)
    else:
        result1 = step1_crawl_jobs(args.companies)
        if result1['success']:
            result2 = step2_analyze_with_llm(args.max_jobs)
            step3_prepare_for_website()
    
    show_next_steps()


if __name__ == '__main__':
    main()
