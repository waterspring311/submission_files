# 智聘未来 AI 智能招聘系统

这是一个基于 Flask、Bootstrap、MySQL ORM 和大模型接口的 AI 招聘系统。项目当前主线已经收敛为三类角色：求职者、招聘者、管理员。

## 1. 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Flask |
| 前端 | Bootstrap 5 + Jinja2 HTML |
| 数据库 | MySQL |
| ORM | Flask-SQLAlchemy |
| 大模型 | 可配置 API，支持 Chat、Responses、Messages、Gemini 原生、DashScope 原生 |
| 邮件 | SMTP |

## 2. 快速启动

Windows：

```bat
start_windows.bat
```

Mac/Linux：

```bash
bash start_mac_linux.sh
```

手动启动：

```powershell
cd C:\Users\admin\Desktop\submission_files\01_project_code
E:\cwj\Python\Python311\python.exe run_flask.py
```

访问地址：

```text
http://localhost:8501
```

统一登录入口：

```text
/auth/login
```

## 3. 演示账号

| 角色 | 用户名 | 密码 | 登录后首页 |
|---|---|---|---|
| 求职者 | candidate | 123456 | /candidate |
| 招聘者 | recruiter | 123456 | / |
| 管理员 | admin | 123456 | /admin |

## 4. 目录结构

```text
submission_files/
├── 01_project_code/             # Flask 项目代码
│   ├── app/
│   │   ├── routes/              # 页面和接口路由
│   │   ├── services/            # 业务服务
│   │   ├── templates/           # Bootstrap HTML 页面
│   │   ├── models.py            # SQLAlchemy ORM 模型
│   │   ├── config.py            # 环境和系统配置
│   │   └── auth_middleware.py   # 登录与角色权限中间件
│   ├── scripts/                 # 数据库维护脚本
│   └── run_flask.py             # Flask 启动入口
├── 01_resume_inbox/             # 上传简历
├── 02_processed_resumes/        # 已处理简历归档
├── 03_demo_materials/           # 演示材料
├── 04_data/                     # 环境配置、岗位 JD、会话数据
├── 07_logs/                     # 系统日志
├── requirements.txt             # Python 依赖
├── start_windows.bat            # Windows 启动脚本
└── start_mac_linux.sh           # Mac/Linux 启动脚本
```

## 5. 角色职责

### 求职者

入口：

```text
/candidate
```

职责：

- 上传简历。
- 选择已审核通过且开放的岗位。
- 使用 AI 对简历和岗位 JD 做匹配评分。
- 提交投递记录。
- 通过 AI 面试链接完成作答。

工作流：

```text
登录 -> 上传简历 -> 选择岗位 -> AI 评分 -> 提交投递 -> AI 面试作答
```

### 招聘者

入口：

```text
/
```

职责：

- 维护招聘岗位和 JD。
- 查看简历记录。
- 管理人才库。
- 生成和查看 AI 面试记录。
- 安排 HR 人工面试。
- 生成招聘日报。
- 发送录用通知。

工作流：

```text
登录 -> 新增岗位 -> 等待管理员审核 -> 查看简历/人才 -> 生成 AI 面试 -> 安排 HR 面试 -> 发送 Offer
```

注意：招聘者新增岗位默认是 `待审核`，管理员通过后求职者才可见。

### 管理员

入口：

```text
/admin
```

职责：

- 管理大模型配置、邮箱配置和系统访问地址。
- 审核招聘者发布的岗位、JD 和评分标准。
- 审核求职者投递简历和 AI 评分结果。

工作流：

```text
登录 -> 配置系统 -> 审核招聘信息 -> 审核求职者简历
```

## 6. 权限控制

权限由以下文件统一控制：

```text
01_project_code/app/auth_middleware.py
```

规则：

| 角色 | 可访问功能 |
|---|---|
| 求职者 | `/candidate`、`/api/jobs`、`/interviews/take/<token>` |
| 招聘者 | `/`、`/jobs`、`/resumes`、`/talents`、`/interviews`、`/hr/*` |
| 管理员 | 全部功能，核心职责是配置和审核 |

未登录用户访问业务页面会跳转到 `/auth/login`。

## 7. 核心路由

| 蓝图 | URL 前缀 | 文件 | 职责 |
|---|---|---|---|
| auth | /auth | app/routes/auth.py | 登录、退出 |
| admin | /admin | app/routes/admin.py | 管理员后台、系统配置、审核 |
| main | / | app/routes/main.py | 招聘者工作台、岗位、简历、人才库 |
| candidate | /candidate | app/routes/candidate.py | 求职者投递流程 |
| interviews | /interviews | app/routes/interview.py | AI 面试管理和作答 |
| hr | /hr | app/routes/hr.py | HR 面试、日报、录用通知 |

## 8. 核心服务

| 文件 | 职责 |
|---|---|
| app/services/orm_repository.py | 数据库读写主接口 |
| app/services/admin_service.py | 系统配置、表初始化、管理员配置加载 |
| app/services/auth_service.py | 登录认证、角色首页分流 |
| app/services/ai_scorer.py | 大模型请求、响应解析、简历评分 |
| app/services/resume_parser.py | PDF/DOCX/TXT 简历解析 |
| app/services/interview_engine.py | AI 面试题生成和回答评分 |
| app/services/interview_links.py | 面试 token 和链接生成 |
| app/services/email_service.py | 初筛、面试、Offer 邮件 |
| app/services/reporting.py | 招聘日报 |
| app/services/log_system.py | 日志写入 |
| app/services/utils.py | 文本、PDF、DOCX 工具函数 |

## 9. 数据模型

模型定义：

```text
01_project_code/app/models.py
```

核心表：

| 表 | 模型 | 说明 |
|---|---|---|
| job_positions | JobPosition | 招聘岗位、JD、评分标准、审核状态 |
| resume_record | ResumeRecord | 简历投递、AI 评分、面试链接、审核状态 |
| talent_pool | TalentPool | 人才库 |
| interview_record | InterviewRecord | AI 面试记录 |
| interview_url | InterviewUrl | AI 面试访问链接和访问次数 |
| hr_login | HrUser | 兼容数据库 HR 用户 |
| hr_interview_schedule | HrInterviewSchedule | HR 人工面试安排 |
| system_config | SystemConfig | 管理员维护的系统配置 |

应用启动时会通过 ORM 创建核心表，并初始化管理员配置项。

## 10. 系统配置

管理员配置入口：

```text
/admin/config
```

配置项会写入 MySQL：

```text
system_config
```

大模型请求格式支持：

| 格式 | 说明 |
|---|---|
| auto | 按 URL 自动识别 |
| openai_chat | OpenAI Chat Completions 兼容格式 |
| openai_responses | OpenAI Responses 兼容格式 |
| anthropic_messages | Messages 兼容格式 |
| gemini | Gemini 原生 generateContent 格式 |
| dashscope | DashScope 原生 input.messages 格式 |

Gemini 原生格式可以填基础地址：

```text
https://generativelanguage.googleapis.com/v1beta
```

系统会自动拼接：

```text
/models/你的模型名:generateContent
```

## 11. 环境变量

配置文件位置：

```text
04_data/.env
```

常用配置：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=recruitment

API_KEY=your_api_key
API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
API_MODEL=qwen-turbo
API_FORMAT=auto

MAIL_SENDER=your_email@example.com
MAIL_PASSWORD=your_email_password
MAIL_SERVER=smtp.qq.com
MAIL_PORT=465
HR_EMAIL=hr@example.com

APP_BASE_URL=http://localhost:8501
```

## 12. 当前清理状态

项目已删除旧流程文件：

- 旧 Streamlit 页面目录 `pages/`
- 旧 PyMySQL 数据库服务 `app/services/database.py`
- 旧 Excel 数据服务 `app/services/excel_service.py`
- 旧 AI 面试流程 `app/services/interview_workflow.py`
- 旧 HR 登录模板 `app/templates/hr_login.html`
- 旧 HR 专用启动脚本 `start_hr_backend.py`
- 旧 SQL 建表脚本目录 `sql/`

当前主线以 Flask 蓝图、Bootstrap 页面和 SQLAlchemy ORM 为准。

## 13. 验收建议

启动后按下面顺序验收：

1. 管理员登录 `/admin`，检查系统配置和审核页面。
2. 招聘者登录，新建岗位，确认岗位为待审核。
3. 管理员审核岗位通过。
4. 求职者登录，确认可以选择该岗位并提交投递。
5. 招聘者查看简历、生成 AI 面试、安排 HR 面试。
