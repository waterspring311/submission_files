from datetime import date, datetime, timedelta
from pathlib import Path

from ..config import LOG_ROOT
from .ai_scorer import call_llm_with_retry
from .orm_repository import dashboard_stats, list_interview_records, list_jobs, list_resumes, list_talents


def date_range_from_label(label):
    today = date.today()
    if label == "昨日":
        return today - timedelta(days=1), today - timedelta(days=1)
    if label == "近7天":
        return today - timedelta(days=7), today
    if label == "近30天":
        return today - timedelta(days=30), today
    return today, today


def collect_log_counts(start_date, end_date):
    root = Path(LOG_ROOT)
    counts = {
        "dialog_logs": 0,
        "hr_logs": 0,
        "delivery_logs": 0,
        "interview_logs": 0,
        "email_logs": 0,
    }
    if not root.exists():
        return counts

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        text = str(path)
        if "log_dialog" in text:
            counts["dialog_logs"] += 1
        elif "log_hr" in text:
            counts["hr_logs"] += 1
        elif "log_dayinfo" in text:
            counts["delivery_logs"] += 1
        elif "log_interview" in text:
            counts["interview_logs"] += 1
        elif "log_email" in text:
            counts["email_logs"] += 1
    return counts


def build_daily_report(label="今日", use_ai=False):
    start_date, end_date = date_range_from_label(label)
    stats = dashboard_stats()
    jobs = list_jobs(open_only=True)
    resumes = list_resumes(limit=20)
    talents = list_talents(limit=20)
    interviews = list_interview_records(limit=20)
    log_counts = collect_log_counts(start_date, end_date)

    base_report = f"""### 一、HR工作汇总
- 统计周期：{start_date} 至 {end_date}
- 开放岗位：{stats["open_jobs"]} 个
- 简历记录：{stats["resumes"]} 条
- 人才库总数：{stats["talents"]} 人，其中活跃人才 {stats["active_talents"]} 人
- AI面试记录：{stats["interviews"]} 条
- HR面试安排：{stats["hr_interviews"]} 条

### 二、投递与岗位
- 近期简历：{len(resumes)} 条
- 当前开放岗位：{", ".join([job.job_name for job in jobs[:5]]) or "暂无开放岗位"}

### 三、人才库情况
- 近期人才：{", ".join([talent.name or talent.email or "未知" for talent in talents[:5]]) or "暂无人才"}

### 四、AI面试情况
- 近期AI面试：{len(interviews)} 条
- 已完成：{len([item for item in interviews if item.status == "completed"])} 条

### 五、日志统计
- 对话日志：{log_counts["dialog_logs"]} 个
- HR操作日志：{log_counts["hr_logs"]} 个
- 投递日志：{log_counts["delivery_logs"]} 个
- 面试日志：{log_counts["interview_logs"]} 个
- 邮件日志：{log_counts["email_logs"]} 个

### 六、优化建议
- 优先跟进高分简历和已完成AI面试的候选人。
- 对缺少JD或评分标准的岗位补齐信息，提升简历匹配质量。
- 对长期未更新状态的人才做归档或重新触达。"""

    if not use_ai:
        return base_report, False

    prompt = f"请基于以下招聘数据生成一份专业HR日报，保留Markdown标题和表格：\n\n{base_report}"
    success, ai_report = call_llm_with_retry([{"role": "user", "content": prompt}], temperature=0.3)
    return (ai_report if success else base_report + f"\n\n> AI日报生成失败，已展示本地日报：{ai_report}"), success
