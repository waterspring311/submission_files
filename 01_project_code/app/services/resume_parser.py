
"""
简历解析模块
负责简历文件的解析和信息提取
"""
import os
import re
import json
from ..config import UPLOAD_FOLDER
from .utils import (
    read_resume_text,
    extract_email,
    extract_name,
    extract_gender,
    extract_age,
    extract_major,
    extract_education,
    extract_city,
    extract_target_city
)
from .ai_scorer import call_llm


def handle_upload_and_parse(file_bytes, filename):
    """
    处理上传的简历文件并解析
    :param file_bytes: 文件字节流
    :param filename: 文件名
    :return: 解析结果字典
    """
    temp_dir = UPLOAD_FOLDER
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"_parse_{filename}")
    with open(temp_path, "wb") as f:
        f.write(file_bytes)

    text = read_resume_text(temp_path)
    email = extract_email(text)

    name = extract_name(text)
    gender = extract_gender(text)
    age = extract_age(text)
    major = extract_major(text)
    education = extract_education(text)
    city = extract_city(text)

    if not name or not gender or not age:
        try:
            prompt = f"""从以下简历文本中提取姓名、性别、年龄。
如果文本中没有相关信息，返回空字符串。
只返回JSON：{{"name":"...","gender":"...","age":"..."}}

简历文本：
{text[:800]}"""
            content = call_llm([{"role": "user", "content": prompt}], temperature=0.0)
            info = json.loads(content)
            name = name or info.get("name", "")
            gender = gender or info.get("gender", "")
            age = age or info.get("age", "")
        except:
            pass

    try:
        os.remove(temp_path)
    except:
        pass

    skills = extract_skills_from_text(text)
    return {
        "text": text,
        "email": email,
        "name": name,
        "gender": gender,
        "age": age,
        "major": major,
        "education": education,
        "city": city,
        "target_city": "",
        "skills": skills
    }


def extract_skills_from_text(text):
    """
    从简历文本中提取技能关键词
    :param text: 简历文本
    :return: 技能列表（逗号分隔的字符串）
    """
    # 预设技能关键词库
    skill_keywords = [
        # 编程语言
        "Python", "Java", "JavaScript", "C++", "C#", "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "TypeScript",
        # 数据处理与分析
        "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Spark", "Hadoop", "Hive", "Flink", "Kafka",
        "数据分析", "数据挖掘", "机器学习", "深度学习", "人工智能", "AI", "NLP", "计算机视觉", "推荐系统",
        # 工具与框架
        "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Django", "Flask", "Spring", "React", "Vue",
        # 其他技能
        "Linux", "Git", "Docker", "Kubernetes", "GitLab", "CI/CD", "微服务", "分布式系统", "高并发",
        "Excel", "PPT", "Office", "产品经理", "UI设计", "UX设计", "项目管理", "团队协作",
        "英语", "日语", "韩语", "法语", "德语", "西班牙语"
    ]
    
    # 匹配技能关键词
    found_skills = []
    text_lower = text.lower()
    for skill in skill_keywords:
        # 精确匹配
        if skill.lower() in text_lower and skill not in found_skills:
            found_skills.append(skill)
    
    return ",".join(found_skills) if found_skills else ""


def extract_info_from_resume_text(text):
    """
    从简历文本中提取所有信息
    :param text: 简历文本
    :return: 信息字典
    """
    skills = extract_skills_from_text(text)
    return {
        "text": text,
        "email": extract_email(text),
        "name": extract_name(text),
        "gender": extract_gender(text),
        "age": extract_age(text),
        "major": extract_major(text),
        "education": extract_education(text),
        "city": extract_city(text),
        "target_city": extract_target_city(text),
        "skills": skills
    }

