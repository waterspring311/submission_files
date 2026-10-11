
"""
工具函数模块
存放通用的工具函数
"""
import re
import os
from docx import Document
from PyPDF2 import PdfReader
from ..config import JD_FOLDER


def extract_email(text):
    """
    从文本中提取邮箱地址
    :param text: 文本内容
    :return: 邮箱地址字符串，未找到返回 None
    """
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    res = re.findall(pattern, text)
    return res[0] if res else None


def extract_major(text):
    """
    从文本中提取专业信息
    :param text: 文本内容
    :return: 专业字符串，未找到返回空字符串
    """
    match = re.search(r"专业[:：]\s*([^\n\t\r]{2,20})", text)
    return match.group(1).strip() if match else ""


def extract_education(text):
    """
    从文本中提取学历信息
    :param text: 文本内容
    :return: 学历字符串，未找到返回空字符串
    """
    edu_list = ["大专", "本科", "硕士", "博士", "研究生", "高中", "中专"]
    for edu in edu_list:
        if edu in text:
            return edu
    return ""


def extract_city(text):
    """
    从文本中提取所在城市
    :param text: 文本内容
    :return: 城市字符串，未找到返回空字符串
    """
    match = re.search(r"(所在城市|现居|城市|地址)[：:]\s*([^\n\t\r]{2,10})", text)
    return match.group(2).strip() if match else ""


def extract_target_city(text):
    """
    从文本中提取意向城市
    :param text: 文本内容
    :return: 意向城市字符串，未找到返回空字符串
    """
    match = re.search(r"(意向城市|期望工作地|意向地点|意向地区)[：:]\s*([^\n\t\r]{2,10})", text)
    return match.group(2).strip() if match else ""


def extract_name(text):
    """
    从简历文本中提取姓名
    :param text: 简历文本
    :return: 姓名字符串，未找到返回空字符串
    """
    name = ""
    m = re.search(r'(姓名|名字)[：:]\s*([^\n\t\r]{2,4})', text)
    if m:
        name = m.group(2).strip()
    if not name:
        first_line = text.strip().split("\n")[0].strip()
        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', first_line):
            name = first_line
    return name


def extract_gender(text):
    """
    从简历文本中提取性别
    :param text: 简历文本
    :return: 性别字符串，未找到返回空字符串
    """
    gender = ""
    m = re.search(r'(性别)[：:]?\s*(男|女)', text)
    if m:
        gender = m.group(2)
    if not gender:
        if '男' in text[:300]:
            gender = '男'
        elif '女' in text[:300]:
            gender = '女'
    return gender


def extract_age(text):
    """
    从简历文本中提取年龄
    :param text: 简历文本
    :return: 年龄字符串，未找到返回空字符串
    """
    age = ""
    m = re.search(r'(出生年月|出生日期|生日)[：:]\s*(\d{4})', text)
    if m:
        try:
            age = str(2026 - int(m.group(2)[:4]))
        except:
            pass
    if not age:
        m = re.search(r'年龄[：:]\s*(\d{2})', text)
        if m:
            age = m.group(1)
    return age


def read_resume_text(file_path):
    """
    读取简历文件内容，支持 txt、docx、pdf 格式
    :param file_path: 文件路径
    :return: 简历文本内容
    """
    text = ""
    suffix = os.path.splitext(file_path)[1].lower()
    try:
        if suffix == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif suffix == ".docx":
            doc = Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif suffix == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"ERROR: 读取文件失败: {e}")
        return ""
    return text


def get_matched_jd_content(job_name):
    """
    根据岗位名称获取对应的 JD 内容
    :param job_name: 岗位名称
    :return: JD 文本内容
    """
    print(f"[DEBUG] 接收岗位名：{job_name}")
    if not os.path.exists(JD_FOLDER):
        print(f"WARN: 警告：JD文件夹不存在 {JD_FOLDER}，使用默认JD。")
        return "大数据开发工程师要求：熟悉Spark、Flink、数仓建模、SQL调优"

    try:
        target_jd_file = f"{job_name}_jd.txt"
        target_jd_path = os.path.join(JD_FOLDER, target_jd_file)

        if os.path.exists(target_jd_path):
            with open(target_jd_path, "r", encoding="utf-8") as f:
                print(f"OK: 读取前端指定岗位JD：{target_jd_file}")
                return f.read().strip()
        else:
            files = [f for f in os.listdir(JD_FOLDER) if f.endswith("_jd.txt")]
            if not files:
                return "未找到JD文件"
            default_file = files[0]
            default_path = os.path.join(JD_FOLDER, default_file)
            with open(default_path, "r", encoding="utf-8") as f:
                print(f"WARN: 未找到【{job_name}】对应JD，使用默认JD：{default_file}")
                return f.read().strip()

    except Exception as e:
        print(f"ERROR: 读取JD文件夹失败：{e}")
        return "大数据开发工程师要求：熟悉Spark、Flink、数仓建模、SQL调优"


def summarize_text(text, max_length=100):
    """
    文本摘要精简函数（保持接口，暂不实现AI摘要，直接截断）
    :param text: 原文本
    :param max_length: 最大长度
    :return: 精简后的文本
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
