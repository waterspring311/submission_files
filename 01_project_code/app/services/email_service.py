
"""
邮件服务模块
负责发送各类通知邮件
"""
import os
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import EMAIL_CONFIG, LOG_ROOT
from .utils import summarize_text
from .log_system import write_email_log


def send_email(receive_email, score, job_title, apply_result, report="", advantage="", shortcoming="", candidate_name=""):
    """
    发送简历评分邮件（求职者和HR双端）
    :param receive_email: 求职者邮箱
    :param score: 分数
    :param job_title: 岗位名称
    :param apply_result: 初筛结果（初筛通过/初筛未通过）
    :param report: 完整报告（求职者用）
    :param advantage: 优势（HR用）
    :param shortcoming: 不足（HR用）
    :param candidate_name: 候选人姓名
    :return: 邮件状态（成功/失败）
    """
    HR_EMAIL = EMAIL_CONFIG.get("hr_email")
    mail_status = "失败"

    if apply_result == "初筛通过":
        hr_tip = f"该候选人初筛通过，请关注后续面试流程。"
    else:
        hr_tip = "该候选人初筛未通过，已录入企业人才库，可后续关注。"

    advantage_text = advantage if advantage else "无明显优势信息"
    shortcoming_text = shortcoming if shortcoming else "无明显短板信息"

    applicant_content = report if report else "AI评分报告生成失败"

    hr_content = f"""【智聘未来 - 简历初筛报告】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 基本信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
候选人：{candidate_name or '未知'}
邮箱：{receive_email}
应聘岗位：{job_title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 初筛结果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
综合得分：{score}分
初筛结果：{apply_result}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ 简历优势
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{advantage_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 改进建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{shortcoming_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 HR处理提示
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{hr_tip}
"""

    print("\n" + "=" * 80)
    print("INFO: 求职者邮件全文：")
    print("=" * 80)
    print(applicant_content)
    print("\n" + "=" * 80)
    print("INFO: HR邮件全文：")
    print("=" * 80)
    print(hr_content)
    print("=" * 80 + "\n")

    mail_status = "失败"
    try:
        if not receive_email:
            print("ERROR: 错误：简历中未提取到邮箱，无法发送")
            return mail_status

        msg1 = MIMEMultipart()
        msg1["From"] = EMAIL_CONFIG["sender"]
        msg1["To"] = receive_email
        msg1["Subject"] = "【智聘未来】你的简历测评结果"
        msg1.attach(MIMEText(applicant_content, "plain", "utf-8"))
        smtp = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
        smtp.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        smtp.sendmail(EMAIL_CONFIG["sender"], receive_email, msg1.as_string())
        smtp.quit()
        print("OK: 求职者邮件发送成功")

        if HR_EMAIL:
            msg2 = MIMEMultipart()
            msg2["From"] = EMAIL_CONFIG["sender"]
            msg2["To"] = HR_EMAIL
            msg2["Subject"] = f"【智聘未来】简历投递通知｜得分：{score}｜{apply_result}"
            msg2.attach(MIMEText(hr_content, "plain", "utf-8"))
            smtp2 = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
            smtp2.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            smtp2.sendmail(EMAIL_CONFIG["sender"], HR_EMAIL, msg2.as_string())
            smtp2.quit()
            print("OK: HR精简邮件发送成功")

        mail_status = "成功"

    except smtplib.SMTPAuthenticationError:
        print("ERROR: 错误：邮箱授权码/密码错误，请检查.env配置")
    except smtplib.SMTPConnectError:
        print("ERROR: 错误：无法连接QQ邮箱服务器，检查网络/端口")
    except smtplib.SMTPRecipientsRefused:
        print("ERROR: 错误：对方邮箱不存在/被拒收/黑名单")
    except smtplib.SMTPHeloError:
        print("ERROR: 错误：邮箱服务器验证失败")
    except TimeoutError:
        print("ERROR: 错误：发送超时，网络不稳定")
    except Exception as e:
        print(f"ERROR: 邮件发送失败：{str(e)}")

    # 使用新的邮件日志记录功能（按初筛结果分类）
    log_file = write_email_log(
        candidate_name=candidate_name or "未知",
        email=receive_email,
        job_name=job_title,
        score=score,
        result=apply_result,
        applicant_email_content=applicant_content,
        hr_email_content=hr_content,
        success=(mail_status == "成功")
    )

    print(f"\n📌 最终邮件状态：{mail_status}")
    return mail_status


def send_interview_result_email(email, job_name, scores, total, apply_result, all_answers):
    """
    发送面试结果邮件
    :param email: 求职者邮箱
    :param job_name: 岗位名称
    :param scores: 各模块分数
    :param total: 总分
    :param apply_result: 录用结果
    :param all_answers: 所有答案
    """
    HR_EMAIL = EMAIL_CONFIG.get("hr_email")

    applicant_content = f"""【智聘未来】AI初面结果通知

应聘岗位：{job_name}
面试总分：{total:.1f}/10
录用结果：{apply_result}

各模块得分：
- 基础知识：{scores.get('基础知识', 0):.1f}/10
- 项目经历：{scores.get('项目经历', 0):.1f}/10
- 实习经历：{scores.get('实习经历', 0):.1f}/10
- 技能实战：{scores.get('技能实战', 0):.1f}/10
- 技能进阶：{scores.get('技能进阶实战', 0):.1f}/10

后续流程将另行邮件通知，请保持邮箱畅通。"""

    answers_text = "\n\n".join(
        [f"模块[{a['module']}]\nQ: {a['question']}\nA: {a['answer']}" for a in all_answers]
    )
    hr_content = f"""【智聘未来】候选人AI初面报告

求职者邮箱：{email}
应聘岗位：{job_name}
面试总分：{total:.1f}/10
录用建议：{apply_result}

详细得分：
- 基础知识：{scores.get('基础知识', 0):.1f}/10 (权重10%)
- 项目经历：{scores.get('项目经历', 0):.1f}/10 (权重30%)
- 实习经历：{scores.get('实习经历', 0):.1f}/10 (权重30%)
- 技能实战：{scores.get('技能实战', 0):.1f}/10 (权重20%)
- 技能进阶：{scores.get('技能进阶实战', 0):.1f}/10 (权重10%)

完整问答：
{answers_text}

请登录系统查看详情或进行二次评分。"""

    try:
        msg1 = MIMEMultipart()
        msg1["From"] = EMAIL_CONFIG["sender"]
        msg1["To"] = email
        msg1["Subject"] = f"【智聘未来】AI初面结果｜{job_name}｜{apply_result}"
        msg1.attach(MIMEText(applicant_content, "plain", "utf-8"))
        smtp = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
        smtp.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        smtp.sendmail(EMAIL_CONFIG["sender"], email, msg1.as_string())
        smtp.quit()
        print("OK: 求职者面试结果邮件发送成功")
    except Exception as e:
        print(f"ERROR: 求职者面试结果邮件发送失败: {e}")

    if HR_EMAIL:
        try:
            msg2 = MIMEMultipart()
            msg2["From"] = EMAIL_CONFIG["sender"]
            msg2["To"] = HR_EMAIL
            msg2["Subject"] = f"【智聘未来】AI初面报告｜{job_name}｜{total:.1f}分｜{apply_result}"
            msg2.attach(MIMEText(hr_content, "plain", "utf-8"))
            smtp2 = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
            smtp2.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            smtp2.sendmail(EMAIL_CONFIG["sender"], HR_EMAIL, msg2.as_string())
            smtp2.quit()
            print("OK: HR面试报告邮件发送成功")
        except Exception as e:
            print(f"ERROR: HR面试报告邮件发送失败: {e}")


def send_interview_invitation_email(email, candidate_name, interview_url):
    """
    发送面试邀请邮件
    :param email: 求职者邮箱
    :param candidate_name: 候选人姓名
    :param interview_url: 面试链接
    :return: 是否成功
    """
    if not candidate_name or candidate_name == "未知":
        candidate_name = email.split("@")[0] if email else "同学"

    content = f"""您好{candidate_name}，

由于您的简历初筛达到了我们的标准，现在我们邀请您进行一轮简单的AI面试。

点击下方链接开始面试：
{interview_url}

⚠️ 重要提醒：该面试链接最多只能访问3次，超过3次后链接将失效，请确保网络稳定！
⏰ 时间限时为48小时，过期不候。
✅ 完成面试后，我们后续会与您继续联系。

祝您面试顺利！

智聘未来 招聘团队"""

    print("\n" + "=" * 80)
    print("INFO: 面试邀请邮件全文：")
    print("=" * 80)
    print(content)
    print("=" * 80 + "\n")

    success = False
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["sender"]
        msg["To"] = email
        msg["Subject"] = "【智聘未来】AI初面邀请｜请在48小时内完成"
        msg.attach(MIMEText(content, "plain", "utf-8"))

        smtp = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
        smtp.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        smtp.sendmail(EMAIL_CONFIG["sender"], email, msg.as_string())
        smtp.quit()
        print("OK: 面试邀请邮件发送成功")
        success = True
    except Exception as e:
        print(f"ERROR: 面试邀请邮件发送失败: {e}")

    # 面试邀请邮件也记录到日志
    from .log_system import write_email_log
    write_email_log(
        candidate_name=candidate_name,
        email=email,
        job_name="AI面试邀请",
        score=0,
        result="面试邀请",
        applicant_email_content=content,
        hr_email_content=f"[面试邀请] 已发送面试链接给 {candidate_name} ({email})",
        success=success
    )
    return success


def send_interview_interrupted_email(candidate_name, email, job_name):
    """
    发送面试中断提醒邮件（只发给候选人，不发给HR）
    :param candidate_name: 候选人姓名
    :param email: 求职者邮箱
    :param job_name: 岗位名称
    """
    if not candidate_name or candidate_name == "未知":
        candidate_name = email.split("@")[0] if email else "同学"

    content = f"""您好{candidate_name}，

很抱歉通知您，您的面试链接已失效。

应聘岗位：{job_name}
失效原因：面试链接已被访问超过3次，为防止作弊，链接已被销毁。

如有疑问，请联系HR重新发起面试邀请。

智聘未来 招聘团队"""

    print("\n" + "=" * 80)
    print("INFO: 面试中断提醒邮件全文：")
    print("=" * 80)
    print(content)
    print("=" * 80 + "\n")

    success = False
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["sender"]
        msg["To"] = email
        msg["Subject"] = f"【智聘未来】面试链接失效提醒｜{job_name}"
        msg.attach(MIMEText(content, "plain", "utf-8"))

        smtp = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
        smtp.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        smtp.sendmail(EMAIL_CONFIG["sender"], email, msg.as_string())
        smtp.quit()
        print("OK: 面试中断提醒邮件发送成功")
        success = True
    except Exception as e:
        print(f"ERROR: 面试中断提醒邮件发送失败: {e}")

    # 记录到日志
    from .log_system import write_email_log
    write_email_log(
        candidate_name=candidate_name,
        email=email,
        job_name=job_name,
        score=0,
        result="面试中断",
        applicant_email_content=content,
        hr_email_content=f"[面试中断] 候选人 {candidate_name} ({email}) 的面试链接已失效",
        success=success
    )
    return success


def handle_send_email(receive_email, score, job_title, apply_result, report="", advantage="", shortcoming="", candidate_name=""):
    """
    封装的发送邮件接口（供外部调用），包含摘要精简
    :param receive_email: 求职者邮箱
    :param score: 分数
    :param job_title: 岗位名称
    :param apply_result: 录用结果
    :param report: 完整报告
    :param advantage: 优势
    :param shortcoming: 不足
    :param candidate_name: 候选人姓名
    :return: 邮件状态
    """
    short_adv = summarize_text(advantage, 100) if advantage else ""
    short_short = summarize_text(shortcoming, 100) if shortcoming else ""
    return send_email(receive_email, score, job_title, apply_result, report, short_adv, short_short, candidate_name)


def send_hr_interview_invitation_email(email, candidate_name, job_name, interview_date, interview_time, interview_location, interviewer, interview_notes=""):
    """
    发送HR人工面试邀请邮件
    :param email: 候选人邮箱
    :param candidate_name: 候选人姓名
    :param job_name: 岗位名称
    :param interview_date: 面试日期
    :param interview_time: 面试时间
    :param interview_location: 面试地点
    :param interviewer: 面试官
    :param interview_notes: 面试备注
    :return: 是否成功
    """
    if not candidate_name or candidate_name == "未知":
        candidate_name = email.split("@")[0] if email else "同学"
    
    content = f"""您好{candidate_name}，

恭喜您通过了AI面试环节！我们诚邀您参加HR人工面试。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 面试信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
应聘岗位：{job_name}
面试时间：{interview_date} {interview_time}
面试地点：{interview_location}
面试官：{interviewer}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{"面试注意事项：" + interview_notes if interview_notes else ""}

请提前10分钟到达面试地点，并准备好以下材料：
• 身份证原件
• 简历纸质版（如有）
• 相关证书原件（如有）

如有任何问题，请回复此邮件或联系HR。

期待与您见面！

智聘未来 招聘团队"""

    print("\n" + "=" * 80)
    print("INFO: HR面试邀请邮件全文：")
    print("=" * 80)
    print(content)
    print("=" * 80 + "\n")
    
    success = False
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["sender"]
        msg["To"] = email
        msg["Subject"] = f"【智聘未来】HR人工面试邀请｜{job_name}｜{interview_date} {interview_time}"
        msg.attach(MIMEText(content, "plain", "utf-8"))

        smtp = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
        smtp.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        smtp.sendmail(EMAIL_CONFIG["sender"], email, msg.as_string())
        smtp.quit()
        print("OK: HR面试邀请邮件发送成功")
        success = True
    except Exception as e:
        print(f"ERROR: HR面试邀请邮件发送失败: {e}")

    # 记录到日志
    from .log_system import write_email_log
    write_email_log(
        candidate_name=candidate_name,
        email=email,
        job_name=job_name,
        score=0,
        result="HR面试邀请",
        applicant_email_content=content,
        hr_email_content=f"[HR面试邀请] 候选人 {candidate_name} ({email})，岗位 {job_name}，时间 {interview_date} {interview_time}",
        success=success
    )
    return success


def send_offer_email(email, candidate_name, job_name, salary="面议", start_date="待定", benefits="标准福利"):
    """
    发送录用通知邮件
    :param email: 候选人邮箱
    :param candidate_name: 候选人姓名
    :param job_name: 岗位名称
    :param salary: 薪资待遇
    :param start_date: 入职日期
    :param benefits: 福利待遇
    :return: 是否成功
    """
    if not candidate_name or candidate_name == "未知":
        candidate_name = email.split("@")[0] if email else "同学"
    
    content = f"""恭喜您，{candidate_name}！

经过多轮面试评估，我们很高兴地通知您，您已成功通过智聘未来的全部面试环节，现正式向您发出录用通知！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 录用信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
岗位名称：{job_name}
薪资待遇：{salary}
入职日期：{start_date}
福利待遇：{benefits}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请在收到录用通知后3个工作日内回复此邮件确认录用意向，并提供以下信息：
• 确认入职日期
• 学历证书编号
• 身份证号码（用于办理入职手续）

如对录用条件有任何疑问，欢迎随时联系HR。

再次恭喜您，期待您的加入！

智聘未来 招聘团队
{datetime.now().strftime('%Y-%m-%d')}"""

    print("\n" + "=" * 80)
    print("INFO: 录用通知邮件全文：")
    print("=" * 80)
    print(content)
    print("=" * 80 + "\n")
    
    success = False
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["sender"]
        msg["To"] = email
        msg["Subject"] = f"🎉【智聘未来】录用通知｜{candidate_name}｜{job_name}"
        msg.attach(MIMEText(content, "plain", "utf-8"))

        smtp = smtplib.SMTP_SSL(EMAIL_CONFIG["server"], EMAIL_CONFIG["port"])
        smtp.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        smtp.sendmail(EMAIL_CONFIG["sender"], email, msg.as_string())
        smtp.quit()
        print("OK: 录用通知邮件发送成功")
        success = True
    except Exception as e:
        print(f"ERROR: 录用通知邮件发送失败: {e}")

    # 记录到日志
    from .log_system import write_email_log
    write_email_log(
        candidate_name=candidate_name,
        email=email,
        job_name=job_name,
        score=100,
        result="录用通知",
        applicant_email_content=content,
        hr_email_content=f"[录用通知] 候选人 {candidate_name} ({email})，岗位 {job_name}，薪资 {salary}，入职 {start_date}",
        success=success
    )
    return success
