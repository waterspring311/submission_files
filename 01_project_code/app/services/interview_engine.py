import json

from ..config import INTERVIEW_CONFIG
from .ai_scorer import call_llm_with_retry


MODULE_NAMES = INTERVIEW_CONFIG["module_names"]


DEFAULT_QUESTIONS = {
    "基础知识": [
        {
            "question": "请介绍你最熟悉的一项技术，并说明它解决了什么问题。",
            "reference_answer": "能说明技术原理、适用场景和实际价值。",
            "scoring_points": ["基础理解", "表达清晰", "场景意识"],
        },
        {
            "question": "你平时如何保证代码或分析结果的质量？",
            "reference_answer": "能提到测试、复核、日志、代码规范或数据校验。",
            "scoring_points": ["质量意识", "工程习惯", "风险意识"],
        },
    ],
    "项目经历": [
        {
            "question": "请选择一个代表性项目，说明你的职责和最终结果。",
            "reference_answer": "能讲清背景、任务、行动、结果。",
            "scoring_points": ["项目结构", "个人贡献", "结果量化"],
        },
        {
            "question": "项目里遇到过什么难点？你是如何定位和解决的？",
            "reference_answer": "能描述问题定位、方案选择和复盘。",
            "scoring_points": ["问题拆解", "解决能力", "复盘意识"],
        },
        {
            "question": "如果重新做这个项目，你会优先优化哪一部分？",
            "reference_answer": "能提出可落地的优化点和原因。",
            "scoring_points": ["迭代思维", "架构意识", "业务价值"],
        },
    ],
    "实习经历": [
        {
            "question": "请描述一次你和团队协作完成任务的经历。",
            "reference_answer": "能说明沟通、分工、交付和协同方式。",
            "scoring_points": ["协作能力", "责任意识", "沟通能力"],
        },
        {
            "question": "你如何处理任务优先级冲突？",
            "reference_answer": "能结合目标、截止时间、影响面进行排序。",
            "scoring_points": ["优先级判断", "计划能力", "沟通同步"],
        },
        {
            "question": "实习或实践中你最大的成长是什么？",
            "reference_answer": "能结合具体经历说明成长。",
            "scoring_points": ["自我认知", "学习能力", "成长性"],
        },
    ],
    "技能实战": [
        {
            "question": "给你一个线上问题或数据异常，你会如何排查？",
            "reference_answer": "能从日志、指标、复现、回滚、修复等方面回答。",
            "scoring_points": ["排查路径", "工具使用", "风险控制"],
        },
        {
            "question": "请说明你如何学习并快速上手一个新工具或框架。",
            "reference_answer": "能提到官方文档、Demo、实践、总结。",
            "scoring_points": ["学习方法", "实践能力", "迁移能力"],
        },
    ],
    "技能进阶实战": [
        {
            "question": "如果系统访问量或数据量突然增长，你会从哪些方面优化？",
            "reference_answer": "能覆盖缓存、索引、异步、扩容、监控等方向。",
            "scoring_points": ["性能意识", "系统思维", "可观测性"],
        },
        {
            "question": "你如何平衡业务速度和技术质量？",
            "reference_answer": "能说明分阶段交付、风险隔离和债务治理。",
            "scoring_points": ["工程判断", "业务理解", "长期维护"],
        },
    ],
}


def generate_questions_for_module(module_name, resume_text="", jd_content=""):
    prompt = f"""你是专业面试官，请为候选人生成 {module_name} 模块面试题。

岗位JD：
{jd_content[:1200]}

简历摘要：
{resume_text[:1200]}

请只返回JSON数组，每项包含 question、reference_answer、scoring_points。
题目数量控制在2到3题。"""

    success, content = call_llm_with_retry([{"role": "user", "content": prompt}], temperature=0.3)
    if success:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and parsed:
                return parsed[:3]
        except Exception:
            pass
    return DEFAULT_QUESTIONS.get(module_name, DEFAULT_QUESTIONS["基础知识"])


def score_answers(answers):
    if not answers:
        return {}, 0.0, "未提交答案"

    grouped = {}
    for item in answers:
        grouped.setdefault(item.get("module", "未分类"), []).append(item)

    scores = {}
    for module, module_answers in grouped.items():
        lengths = [len((item.get("answer") or "").strip()) for item in module_answers]
        average_length = sum(lengths) / max(len(lengths), 1)
        score = 6.0
        if average_length >= 80:
            score = 8.0
        if average_length >= 160:
            score = 9.0
        if average_length < 20:
            score = 5.0
        scores[module] = score

    weights = dict(zip(INTERVIEW_CONFIG["module_names"], INTERVIEW_CONFIG["module_weights"]))
    total_weight = 0
    weighted_score = 0
    for module, score in scores.items():
        weight = weights.get(module, 0.2)
        weighted_score += score * weight
        total_weight += weight

    total = weighted_score / total_weight if total_weight else sum(scores.values()) / len(scores)
    result = "建议进入复试" if total >= 7 else "建议暂缓"
    return scores, round(total, 2), result
