
"""
日志系统模块
负责系统所有日志的记录和管理
包含5类日志：
1. 会话日志 - 按每日会话ID记录
2. 邮件日志 - 按初筛结果分类，按收件人姓名记录
3. AI面试日志 - 按面试者姓名记录，包含完整面试信息
4. HR操作日志 - 记录HR对岗位的增删改查操作
5. AI日报日志 - 记录AI生成的日报内容
"""
import os
import time
import json
from datetime import datetime, date
from ..config import LOG_ROOT

# ===================== 1. 会话日志配置 =====================
LOG_DIALOG = os.path.join(LOG_ROOT, "log_dialog", datetime.now().strftime("%Y-%m-%d"))
os.makedirs(LOG_DIALOG, exist_ok=True)

def create_session_log(session_id):
    """
    创建会话日志文件夹
    :param session_id: 会话ID
    :return: 会话日志文件夹路径
    """
    session_folder = os.path.join(LOG_DIALOG, f"session_{session_id}")
    os.makedirs(session_folder, exist_ok=True)
    return session_folder

def write_session_log(session_id, role, content):
    """
    写入会话日志
    :param session_id: 会话ID
    :param role: 角色（user/assistant/system）
    :param content: 对话内容
    """
    session_folder = create_session_log(session_id)
    log_file = os.path.join(session_folder, "conversation.log")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{role.upper()}] {content}\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

def get_dialog_log_file():
    """返回今日对话日志文件路径"""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_ROOT, "log_dialog", today, f"dialog_{today}.log")

def write_dialog_log(role, content, session_id=None):
    """
    记录单条对话消息
    :param role: 角色（user/assistant/system）
    :param content: 消息文本
    :param session_id: 会话ID（可选，如果有则同时写入会话日志）
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{role.upper()}] {content}\n"
    log_path = get_dialog_log_file()
    
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
        
        # 如果有会话ID，也写入会话专用日志
        if session_id:
            write_session_log(session_id, role, content)
            
    except Exception as e:
        print(f"对话日志写入失败: {e}")

# ===================== 2. 邮件日志配置 =====================
# Keep folder names ASCII while preserving Chinese business status labels.
LOG_EMAIL_ROOT = os.path.join(LOG_ROOT, "log_email")

def get_email_log_folder(result, log_date=None):
    """
    获取邮件日志目录
    :param result: 结果类型
    :param log_date: 日期（默认为今日）
    :return: 日志目录路径
    """
    if log_date is None:
        log_date = datetime.now().strftime("%Y-%m-%d")
    
    # 映射结果到子文件夹
    result_folders = {
        "初筛通过": "screening_passed",
        "面试邀请": "interview_invitation",
        "HR面试邀请": "hr_interview_invitation",
        "录用通知": "offer_notice",
        "初筛未通过": "screening_failed",
        "发送失败": "send_failed"
    }
    
    result_folder = result_folders.get(result, "screening_failed")
    log_folder = os.path.join(LOG_EMAIL_ROOT, log_date, result_folder)
    os.makedirs(log_folder, exist_ok=True)
    return log_folder

def write_email_log(candidate_name, email, job_name, score, result, applicant_email_content, hr_email_content, success=True):
    """
    写入邮件日志
    :param candidate_name: 收件人姓名
    :param email: 收件人邮箱
    :param job_name: 岗位名称
    :param score: 得分
    :param result: 结果（初筛通过/初筛未通过/面试邀请/HR面试邀请/录用通知）
    :param applicant_email_content: 发送给求职者的邮件内容
    :param hr_email_content: 发送给HR的邮件内容
    :param success: 发送是否成功
    """
    # 如果发送失败，使用发送失败结果
    if not success:
        result = "发送失败"
    
    # 获取日志目录（按日期分类）
    log_folder = get_email_log_folder(result)
    
    # 按收件人姓名创建文件
    filename = f"{candidate_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_file = os.path.join(log_folder, filename)
    
    # 构造日志内容
    log_content = f"""
{'='*80}
【邮件日志】
{'='*80}
记录时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
收件人姓名：{candidate_name}
收件人邮箱：{email}
应聘岗位：{job_name}
得分：{score}
初筛结果：{result}

{'='*80}
【发送给求职者的邮件】
{'='*80}
{applicant_email_content}

{'='*80}
【发送给HR的邮件】
{'='*80}
{hr_email_content}

{'='*80}
"""
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_content)
        print(f"OK: 邮件日志已写入：{log_file}")
        return log_file
    except Exception as e:
        print(f"ERROR: 邮件日志写入失败：{e}")
        return None

# ===================== 3. AI面试日志配置 =====================
LOG_INTERVIEW = os.path.join(LOG_ROOT, "log_interview")
os.makedirs(LOG_INTERVIEW, exist_ok=True)

def write_interview_log(candidate_name, interview_data):
    """
    写入AI面试日志
    :param candidate_name: 面试者姓名
    :param interview_data: 面试相关数据（包含所有面试信息）
    """
    # 按面试者姓名创建文件夹
    candidate_folder = os.path.join(LOG_INTERVIEW, candidate_name)
    os.makedirs(candidate_folder, exist_ok=True)
    
    # 面试信息文件名
    filename = f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file = os.path.join(candidate_folder, filename)
    
    # 添加元数据
    interview_data['log_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    interview_data['candidate_name'] = candidate_name
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(interview_data, f, ensure_ascii=False, indent=2)
        print(f"OK: AI面试日志已写入：{log_file}")
        return log_file
    except Exception as e:
        print(f"ERROR: AI面试日志写入失败：{e}")
        return None

def write_interview_detail_log(candidate_name, module, question, answer, score, scoring_reason):
    """
    写入AI面试详细日志（每道题的详细记录）
    :param candidate_name: 面试者姓名
    :param module: 模块名称
    :param question: 问题
    :param answer: 回答
    :param score: 得分
    :param scoring_reason: 评分依据
    """
    candidate_folder = os.path.join(LOG_INTERVIEW, candidate_name)
    os.makedirs(candidate_folder, exist_ok=True)
    
    log_file = os.path.join(candidate_folder, "interview_detail.log")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"""
{'='*80}
[{timestamp}] {module}
{'='*80}
【问题】{question}
【回答】{answer}
【得分】{score}
【评分依据】{scoring_reason}
"""
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"ERROR: AI面试详细日志写入失败：{e}")

# ===================== 4. HR操作日志配置 =====================
LOG_HR = os.path.join(LOG_ROOT, "log_hr")
os.makedirs(LOG_HR, exist_ok=True)

# ===================== 5. AI日报日志配置 =====================
LOG_DAILY_REPORT = os.path.join(LOG_ROOT, "log_daily_report")
os.makedirs(LOG_DAILY_REPORT, exist_ok=True)

def write_daily_report_log(start_date, end_date, report_content, operator=""):
    """
    写入AI日报日志
    :param start_date: 统计开始日期
    :param end_date: 统计结束日期
    :param report_content: AI生成的日报内容
    :param operator: 操作人姓名
    """
    # 按日期创建文件夹
    today = datetime.now().strftime("%Y-%m-%d")
    daily_folder = os.path.join(LOG_DAILY_REPORT, today)
    os.makedirs(daily_folder, exist_ok=True)
    
    # 日报文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"daily_report_{timestamp}.md"
    log_file = os.path.join(daily_folder, filename)
    
    # 构造日志内容
    log_content = f"""
{'='*80}
【AI智能日报】
{'='*80}
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
统计周期：{start_date} 至 {end_date}
操作人：{operator or '未知'}
{'='*80}

{report_content}

{'='*80}
"""
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_content)
        print(f"OK: AI日报日志已写入：{log_file}")
        return log_file
    except Exception as e:
        print(f"ERROR: AI日报日志写入失败：{e}")
        return None

def json_serializer(obj):
    """
    JSON序列化器，处理datetime和其他无法序列化的对象
    """
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif isinstance(obj, set):
        return list(obj)
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        try:
            return str(obj)
        except:
            return repr(obj)

def write_hr_log(operation_type, operator, target, before_data, after_data, remark=""):
    """
    写入HR操作日志
    :param operation_type: 操作类型（add/update/delete/query）
    :param operator: 操作人
    :param target: 操作对象（如：岗位名称、候选人信息等）
    :param before_data: 操作前数据
    :param after_data: 操作后数据
    :param remark: 备注
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_HR, f"hr_{today}.log")
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 操作类型中文映射
    operation_map = {
        "add": "新增",
        "update": "更新",
        "delete": "删除",
        "query": "查询"
    }
    operation_text = operation_map.get(operation_type, operation_type)
    
    log_content = f"""
{'='*80}
[{timestamp}] HR操作日志
{'='*80}
操作类型：{operation_text}
操作人：{operator}
操作对象：{target}
"""
    
    if before_data:
        try:
            before_json = json.dumps(before_data, ensure_ascii=False, indent=2, default=json_serializer)
        except Exception as e:
            before_json = str(before_data)
        log_content += f"""
操作前数据：
{before_json}
"""
    
    if after_data:
        try:
            after_json = json.dumps(after_data, ensure_ascii=False, indent=2, default=json_serializer)
        except Exception as e:
            after_json = str(after_data)
        log_content += f"""
操作后数据：
{after_json}
"""
    
    if remark:
        log_content += f"""
备注：{remark}
"""
    
    log_content += f"""
{'='*80}
"""
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_content)
        print(f"OK: HR操作日志已写入：{log_file}")
    except Exception as e:
        print(f"ERROR: HR操作日志写入失败：{e}")

# ===================== 保留原有函数（兼容性） =====================
def write_email_detail_log(content):
    """兼容旧代码"""
    log_dir = os.path.join(LOG_ROOT, "log_eminfo")
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(log_dir, f"{today}.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(content + "\n" + "="*80 + "\n")

def write_recruit_log(resume_name, job_name, score, email, mail_status, result_status, remark=""):
    """兼容旧代码"""
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = (
        f"【{now_time}】简历：{resume_name}，岗位：{job_name}，得分：{score}，"
        f"求职者邮箱：{email}，邮件状态：{mail_status}，测评结果：{result_status}，备注：{remark}"
    )
    
    log_dir = os.path.join(LOG_ROOT, "log_dayinfo")
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(log_dir, f"{today}.log")
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_text + "\n")
        print(f"OK: 投递日志已写入：{log_path}")
    except Exception as e:
        print(f"ERROR: 投递日志写入失败：{e}")
