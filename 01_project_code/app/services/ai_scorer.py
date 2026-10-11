
"""
AI 评分模块
调用阿里云百炼大模型进行简历评分和智能对话
增强版：更好的错误处理、重试机制、日志记录
"""
import re
import json
import time
import requests
from ..config import API_CONFIG


SUPPORTED_API_FORMATS = {
    "auto",
    "openai_chat",
    "openai_responses",
    "anthropic_messages",
    "gemini",
    "dashscope",
}

API_FORMAT_ALIASES = {
    "chat": "openai_chat",
    "chat_completion": "openai_chat",
    "chat_completions": "openai_chat",
    "openai": "openai_chat",
    "openai_compatible": "openai_chat",
    "response": "openai_responses",
    "responses": "openai_responses",
    "reponse": "openai_responses",
    "reponses": "openai_responses",
    "openai_response": "openai_responses",
    "message": "anthropic_messages",
    "messages": "anthropic_messages",
    "anthropic": "anthropic_messages",
    "anthropic_message": "anthropic_messages",
    "gemini_native": "gemini",
    "google_gemini": "gemini",
    "dashscope_native": "dashscope",
    "qwen": "dashscope",
}


def _normalise_api_format(value):
    value = (value or "auto").strip().lower().replace("-", "_").replace(" ", "_")
    return API_FORMAT_ALIASES.get(value, value)


def _message_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    return str(content or "")


def _normalise_messages(messages):
    normalised = []
    for message in messages or []:
        if not isinstance(message, dict):
            normalised.append({"role": "user", "content": str(message)})
            continue
        normalised.append(
            {
                "role": message.get("role") or "user",
                "content": _message_text(message.get("content")),
            }
        )
    return normalised or [{"role": "user", "content": ""}]


def _messages_to_prompt(messages):
    role_labels = {"system": "系统", "user": "用户", "assistant": "助手"}
    return "\n".join(
        f"{role_labels.get(message['role'], message['role'])}: {message['content']}"
        for message in _normalise_messages(messages)
    )


def _detect_api_format():
    configured = _normalise_api_format(API_CONFIG.get("format") or "auto")
    if configured in SUPPORTED_API_FORMATS and configured != "auto":
        return configured

    api_url = (API_CONFIG.get("url") or "").lower()
    if "generatecontent" in api_url or "generativelanguage" in api_url:
        return "gemini"
    if "responses" in api_url:
        return "openai_responses"
    if "anthropic" in api_url or api_url.endswith("/messages"):
        return "anthropic_messages"
    if "compatible-mode" in api_url or "chat/completions" in api_url:
        return "openai_chat"
    return "dashscope"


def _request_url(api_format):
    api_url = (API_CONFIG.get("url") or "").strip()
    model = API_CONFIG.get("model") or ""
    if api_format == "gemini" and "generatecontent" not in api_url.lower():
        base_url = api_url.rstrip("/")
        if "{model}" in base_url:
            return base_url.replace("{model}", model)
        return f"{base_url}/models/{model}:generateContent"
    return api_url


def _validate_api_config(api_format, api_url):
    if not API_CONFIG.get("key") or API_CONFIG.get("key") == "your_api_key_here":
        return False, "未配置大模型 API Key，请管理员在系统配置中填写 API Key。"
    if not api_url:
        return False, "未配置大模型 API URL，请管理员在系统配置中填写接口地址。"
    if not api_url.startswith(("http://", "https://")):
        return False, "大模型 API URL 格式不正确，需要以 http:// 或 https:// 开头。"
    if api_format not in SUPPORTED_API_FORMATS:
        return False, f"不支持的大模型请求格式：{api_format}"
    return True, ""


def _headers(api_format):
    headers = {"Content-Type": "application/json"}
    api_key = API_CONFIG.get("key") or ""
    if api_format == "anthropic_messages":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    elif api_format == "gemini":
        headers["x-goog-api-key"] = api_key
    else:
        headers["Authorization"] = "Bearer " + api_key
    return headers


def _gemini_payload(messages, temperature):
    system_parts = []
    contents = []
    for message in _normalise_messages(messages):
        role = message["role"]
        text = message["content"]
        if role == "system":
            system_parts.append({"text": text})
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )

    payload = {
        "contents": contents or [{"role": "user", "parts": [{"text": _messages_to_prompt(messages)}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": system_parts}
    return payload


def _build_payload(api_format, messages, temperature):
    normalised_messages = _normalise_messages(messages)
    model = API_CONFIG.get("model")
    if api_format == "openai_chat":
        return {
            "model": model,
            "messages": normalised_messages,
            "temperature": temperature,
        }
    if api_format == "openai_responses":
        return {
            "model": model,
            "input": normalised_messages,
            "temperature": temperature,
        }
    if api_format == "anthropic_messages":
        system_text = "\n".join(message["content"] for message in normalised_messages if message["role"] == "system")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "assistant" if message["role"] == "assistant" else "user",
                    "content": message["content"],
                }
                for message in normalised_messages
                if message["role"] != "system"
            ],
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if system_text:
            payload["system"] = system_text
        return payload
    if api_format == "gemini":
        return _gemini_payload(normalised_messages, temperature)
    return {
        "model": model,
        "input": {
            "messages": normalised_messages,
        },
        "parameters": {
            "temperature": temperature,
        },
    }


def _parts_to_text(parts):
    texts = []
    for part in parts or []:
        if isinstance(part, dict):
            texts.append(str(part.get("text") or part.get("content") or ""))
        else:
            texts.append(str(part))
    return "\n".join(text for text in texts if text)


def _extract_text_from_response(data):
    if not isinstance(data, dict):
        return ""

    if data.get("output_text"):
        return data["output_text"]

    output = data.get("output")
    if isinstance(output, dict) and output.get("text"):
        return output["text"]
    if isinstance(output, list):
        texts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                texts.append(_parts_to_text(content))
            elif content:
                texts.append(str(content))
        joined = "\n".join(text for text in texts if text)
        if joined:
            return joined

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            message = choice.get("message") or {}
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, list):
                    return _parts_to_text(content)
                if content:
                    return str(content)
            if choice.get("text"):
                return choice["text"]

    content = data.get("content")
    if isinstance(content, list):
        text = _parts_to_text(content)
        if text:
            return text
    elif isinstance(content, str):
        return content

    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates:
        candidate_content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
        if isinstance(candidate_content, dict):
            return _parts_to_text(candidate_content.get("parts"))

    message = data.get("message")
    if isinstance(message, dict) and message.get("content"):
        return str(message["content"])
    if isinstance(message, str):
        return message

    for key in ("response", "text", "result"):
        if isinstance(data.get(key), str):
            return data[key]
    return ""


def _friendly_ai_error(error_text):
    text = str(error_text or "").strip()
    if not text:
        return "AI服务暂不可用。"
    if "未配置" in text or "格式不正确" in text or "不支持" in text:
        return text
    if "认证失败" in text or "401" in text:
        return "API认证失败，请管理员检查 API Key。"
    if "频率" in text or "429" in text:
        return "API调用频率超限，请稍后重试。"
    if "超时" in text:
        return "API调用超时，请稍后重试。"
    if "连接" in text:
        return "API连接失败，请管理员检查接口地址和网络。"
    if "400" in text or "请求参数" in text:
        return "API请求参数不兼容，请管理员检查请求格式配置。"
    return "AI服务暂不可用，请管理员检查大模型配置。"


def _keywords(text):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}|[\u4e00-\u9fff]{2,}", (text or "").lower())
    stopwords = {
        "岗位", "要求", "负责", "相关", "能力", "经验", "熟悉", "掌握", "进行", "具备",
        "工作", "项目", "开发", "使用", "以及", "或者", "能够", "优先", "以上",
    }
    return [word for word in words if word not in stopwords and len(word) > 1]


def _fallback_score_resume(job_name, resume_text, jd_content, scoring_criteria="", reason=""):
    resume_lower = (resume_text or "").lower()
    requirement_keywords = _keywords(" ".join([job_name or "", jd_content or "", scoring_criteria or ""]))
    unique_requirements = []
    for keyword in requirement_keywords:
        if keyword not in unique_requirements:
            unique_requirements.append(keyword)

    matched = [keyword for keyword in unique_requirements if keyword.lower() in resume_lower][:8]
    score = 55 + min(len(matched) * 4, 28)
    if job_name and job_name.lower() in resume_lower:
        score += 4
    if len(resume_text or "") >= 800:
        score += 4
    if not jd_content and not scoring_criteria:
        score = min(score, 62)
    score = max(35, min(score, 88))

    matched_text = "、".join(matched) if matched else "暂未识别到明显关键词重合"
    friendly_reason = _friendly_ai_error(reason)
    report = f"""【本地规则评分】
分数：{score}

【评分说明】
{friendly_reason}
系统已使用本地关键词匹配规则完成临时评分，供管理员审核时参考。

【匹配依据】
识别到的匹配关键词：{matched_text}

【简历优势】
- 简历已完成基础解析，可进入人工审核。
- 与岗位相关的关键词匹配情况已记录。

【简历不足与改进建议】
- 建议管理员检查大模型配置后重新触发 AI 深度评分。
- 建议候选人补充项目成果、量化指标和岗位相关技能细节。"""
    return {
        "score": score,
        "report": report,
        "advantage": f"本地规则匹配：{matched_text}",
        "shortcoming": "AI深度评分暂不可用，建议管理员检查大模型配置。",
    }


def call_llm_with_retry(messages, temperature=0.3, max_retries=3, retry_delay=2):
    """
    调用阿里云百炼大模型 API（支持重试机制）
    :param messages: 对话消息列表
    :param temperature: 温度参数
    :param max_retries: 最大重试次数
    :param retry_delay: 重试间隔（秒）
    :return: (是否成功, 回复内容)
    """
    api_format = _detect_api_format()
    api_url = _request_url(api_format)
    ok, config_error = _validate_api_config(api_format, api_url)
    if not ok:
        return False, config_error
    headers = _headers(api_format)
    
    for attempt in range(max_retries):
        response = None
        try:
            payload = _build_payload(api_format, messages, temperature)
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            content = _extract_text_from_response(data)
            if content:
                return True, content
            return False, f"API返回异常：{data}"
                
        except requests.exceptions.Timeout:
            print(f"WARN: API调用超时（第{attempt + 1}次尝试）")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return False, "API调用超时，请稍后重试"
            
        except requests.exceptions.ConnectionError as e:
            print(f"WARN: API连接错误（第{attempt + 1}次尝试）: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return False, f"API连接失败，请检查网络：{e}"
            
        except requests.exceptions.HTTPError as e:
            print(f"WARN: API HTTP错误（第{attempt + 1}次尝试）: {e}")
            status_code = (e.response.status_code if e.response is not None else None) or (response.status_code if response is not None else None)
            if status_code == 401:
                return False, "API认证失败，请检查API Key是否正确"
            elif status_code == 429:
                return False, "API调用频率超限，请稍后重试"
            elif status_code == 400:
                return False, f"API请求参数错误：{e}"
            else:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return False, f"API HTTP错误：{e}"
                
        except Exception as e:
            print(f"WARN: API调用异常（第{attempt + 1}次尝试）: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return False, f"AI调用失败：{e}"
    
    return False, "API调用失败，已达到最大重试次数"


def call_llm(messages, temperature=0.3):
    """
    调用阿里云百炼大模型 API（兼容旧版本）
    :param messages: 对话消息列表
    :param temperature: 温度参数
    :return: 模型回复内容
    """
    success, result = call_llm_with_retry(messages, temperature)
    return result


def extract_json_from_response(response_text, default_structure):
    """
    从AI回复中提取JSON数据
    :param response_text: AI回复文本
    :param default_structure: 默认结构（解析失败时返回）
    :return: 解析后的数据
    """
    if not response_text:
        return default_structure
    
    try:
        return json.loads(response_text)
    except:
        pass
    
    json_patterns = [
        r'\{[^{}]*"[^"]+"\s*:\s*[^{}]+\}',
        r'\[.*\]',
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
    
    return default_structure


def parse_score_from_text(text):
    """
    从文本中提取分数
    :param text: 文本内容
    :return: 分数（0-100）
    """
    if not text:
        return 0
    
    patterns = [
        r"分数[:：]\s*(\d+)",
        r"得分[:：]\s*(\d+)",
        r"评分[:：]\s*(\d+)",
        r"(\d+)\s*分",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            score = int(matches[0])
            if 0 <= score <= 100:
                return score
    
    return 0


def ai_score_resume_with_jd(resume_text, jd_content, job_name="匹配到的岗位"):
    """
    根据 JD 对简历进行 AI 评分
    :param resume_text: 简历文本
    :param jd_content: JD 内容
    :param job_name: 岗位名称
    :return: (分数, 完整报告)
    """
    prompt = f"""你是专业HR面试官，根据【岗位JD】对简历进行严格评分（满分100）。

【岗位名称】
{job_name}

【岗位JD要求】
{jd_content}

【简历内容】
{resume_text[:3000]}

请严格按以下格式输出：

【简历评分】
分数：xx

【分项评分标准】
1. 专业匹配度：xx分
2. 技能匹配度：xx分
3. 项目经验匹配度：xx分
4. 综合素养：xx分

【简历优势】
xxx

【简历不足与改进建议】
xxx"""

    success, content = call_llm_with_retry([{"role": "user", "content": prompt}], temperature=0.1)
    
    if not success:
        fallback = _fallback_score_resume(job_name, resume_text, jd_content, reason=content)
        return fallback["score"], fallback["report"]
    
    score = parse_score_from_text(content)
    
    if score >= 70:
        final_msg = "\n——————————————\n【初筛结果通知】\n恭喜同学，你的简历综合得分：" + str(score) + "分，\n你的简历通过了初筛！\n后续将通过邮件发送面试邀请，请留意邮箱。"
    else:
        final_msg = "\n——————————————\n【初筛结果通知】\n很遗憾，你的简历综合得分：" + str(score) + "分，\n暂未通过初筛，\n建议结合改进建议优化简历，\n欢迎再次投递。"
    
    return score, content + final_msg


def handle_score(job_name, resume_text, jd_content, scoring_criteria=""):
    """
    结构化 AI 评分，返回结构化数据
    :param job_name: 岗位名称
    :param resume_text: 简历文本
    :param jd_content: JD 内容
    :param scoring_criteria: 评分标准（可选）
    :return: {score, report, advantage, shortcoming}
    """
    criteria_text = scoring_criteria if scoring_criteria else "请按专业匹配度、技能匹配度、项目经验匹配度、学历/经验匹配度四个维度自主评分，满分100。"
    
    prompt = f"""你是专业HR面试官，请根据【岗位JD】和【评分标准】对候选人简历进行严格评分（满分100）。

【岗位名称】{job_name}
【岗位JD要求】{jd_content}
【评分标准】{criteria_text}

【简历内容】{resume_text[:3000]}

请严格按照以下格式输出完整的评分报告（这个报告将直接作为邮件正文发送给求职者，请务必详细、专业）：

【简历评分】
分数：xx

【分项评分标准】
1. 专业匹配度：xx分
2. 技能匹配度：xx分
3. 项目经验匹配度：xx分
4. 综合素养：xx分

【简历优势】
- 具体列出与JD匹配的亮点，每条用"- "开头，至少写3条，要结合简历中的具体内容
- 每条优势都要有具体的技能/项目/经验支撑

【简历不足与改进建议】
- 具体列出与JD要求有明显差距的地方，每条用"- "开头，至少写3条
- 针对每条不足给出可操作的改进建议"""
    
    success, content = call_llm_with_retry([{"role": "user", "content": prompt}], temperature=0.1)
    
    if not success:
        return _fallback_score_resume(job_name, resume_text, jd_content, scoring_criteria, reason=content)
    
    score = parse_score_from_text(content)
    
    short_advantage = ""
    short_shortcoming = ""
    
    if "【简历优势】" in content:
        parts = content.split("【简历优势】")
        if len(parts) > 1:
            advantage_part = parts[1].split("【简历不足与改进建议】")[0] if "【简历不足与改进建议】" in parts[1] else parts[1]
            short_advantage = advantage_part.strip()[:200]
    
    if "【简历不足与改进建议】" in content:
        parts = content.split("【简历不足与改进建议】")
        if len(parts) > 1:
            shortcoming_part = parts[1].split("——————————————")[0] if "——————————————" in parts[1] else parts[1]
            short_shortcoming = shortcoming_part.strip()[:200]
    
    if not short_advantage:
        short_advantage = "简历与岗位要求基本匹配"
    if not short_shortcoming:
        short_shortcoming = "建议补充项目量化成果与核心技能"
    
    return {
        "score": score,
        "report": content,
        "advantage": short_advantage,
        "shortcoming": short_shortcoming
    }


def ask_resume_question(resume_text, question):
    """
    根据简历内容回答用户问题
    :param resume_text: 简历文本
    :param question: 用户问题
    :return: AI 回复
    """
    prompt = f"""你是一个专业招聘顾问，根据候选人简历内容回答其问题。

【简历内容】
{resume_text[:2000]}

【候选人问题】
{question}

请给出具体、有针对性、可操作的回答。如果简历中缺乏相关信息，也请诚实指出。"""
    
    success, result = call_llm_with_retry([{"role": "user", "content": prompt}], temperature=0.5)
    return result if success else "抱歉，AI回答失败，请稍后重试。"


def generate_free_reply(history_list, user_input):
    """
    生成自由对话回复
    :param history_list: 对话历史列表
    :param user_input: 用户最新输入
    :return: AI 回复
    """
    recent = history_list[-6:] if len(history_list) > 6 else history_list
    history_text = "\n".join(
        [("用户: " + m['content']) if m['role'] == 'user' else ("助手: " + m['content']) for m in recent]
    )
    
    prompt = f"""你是一个专业的智聘未来招聘助手。根据对话历史，用自然、友好的语气回应用户，并尝试引导用户使用以下功能：
- 查看在招岗位
- 了解岗位具体要求
- 上传简历
- 评估简历与岗位的匹配度
- 获取简历优化建议

不要编造虚构信息。如果用户想了解岗位，提醒他们可以直接说出岗位名称。
当前对话历史：
{history_text}
用户最新输入：{user_input}

请直接给出助手回复："""
    
    success, result = call_llm_with_retry([{"role": "user", "content": prompt}], temperature=0.7)
    return result if success else "抱歉，AI回答失败，请稍后重试。"


def analyze_candidates_comparison(candidates_list):
    """
    对多个候选人进行AI智能对比分析
    :param candidates_list: 候选人信息列表
    :return: AI分析结果
    """
    candidates_text = ""
    for i, candidate in enumerate(candidates_list, 1):
        candidates_text += f"""
【候选人{i} - {candidate.get('name', '未知')}】
- 姓名：{candidate.get('name', '未知')}
- 性别：{candidate.get('gender', '未知')}
- 年龄：{candidate.get('age', '未知')}
- 学历：{candidate.get('education', '未知')}
- 专业：{candidate.get('major', '未知')}
- 城市：{candidate.get('city', '未知')}
- 技能：{candidate.get('skills', '未知')}
- 经验：{candidate.get('experience', '未知')}
- 标签：{candidate.get('tags', '未知')}
"""
    
    prompt = f"""你是一名资深人力资源专家，请对以下候选人进行全面、专业的对比分析。

【候选人信息】
{candidates_text}

请严格按照以下格式输出分析结果：

【📊 整体分析总结】
简要总结这批候选人的整体特点和水平

【📚 学历背景分析】
1. 学历分布情况（具体说明每个学历层次有多少人）
2. 学历层次对比分析
3. 专业匹配度分析（如果有相关信息）

【💼 技能匹配分析】
1. 热门技能统计（列出出现频率最高的前5个技能）
2. 技能互补性分析
3. 技能优势总结

【🏙️ 城市分布分析】
1. 候选人城市分布
2. 地域特点分析

【🎯 各候选人优劣势分析】
针对每个候选人，分别列出：
- 候选人姓名：
  - 核心优势：
  - 潜在不足：

【💡 综合建议】
基于分析结果，给出最终录用建议和注意事项"""

    success, result = call_llm_with_retry([{"role": "user", "content": prompt}], temperature=0.3)
    return result if success else "抱歉，AI分析失败，请稍后重试。"
