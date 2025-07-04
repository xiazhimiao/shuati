# AstrBot 刷题插件 (shuati)

## 插件简介

AstrBot 刷题插件是一个为期末考试设计的刷题工具，支持按章节刷题、顺序刷题和错题复习等功能。插件具有完整的错题记录和统计功能，帮助用户高效复习考试内容。

## 功能特点

- ✅ **随机刷题**：从指定章节随机抽取题目进行练习
- ✅ **顺序刷题**：按章节内题目存储顺序依次刷题
- ✅ **错题本**：自动记录答错题目，支持针对性复习
- ✅ **统计功能**：记录答题总数、正确率等数据
- ✅ **章节管理**：支持多章节题目管理
- ✅ **智能提醒**：错题达到 50 道时自动提醒复习

## 安装方法

### 前提条件

- 已安装 AstrBot 框架
- Python 3.8+
- 基本的 Git 和 Python 知识

### 安装步骤

​	1.**克隆插件仓库**

```bash
git clone https://github.com/xiazhimiao/shuati.git
```

​	2.**将插件放入 AstrBot 插件目录**

```bash
mkdir -p AstrBot/data/plugins
mv shuati AstrBot/data/plugins/
```

​	3.**安装依赖**

```bash
cd AstrBot/data/plugins/shuati
pip install -r requirements.txt
```

​	4.**重启 AstrBot**

```bash
cd AstrBot
python main.py
```

## 使用说明

### 准备工作

1. 准备题目数据

   - 在插件目录下创建 `data` 文件夹

   - 添加章节题目数据文件（JSON 格式），例如 `chapter1.json`

   - 数据格式示例：

     ```json
     {
       "章节名称": {
         "single": [
           {
             "id": "q1",
             "question": "题目内容",
             "options": {
               "A": "选项A",
               "B": "选项B",
               "C": "选项C",
               "D": "选项D"
             },
             "answer": "A"
           }
         ],
         "multiple": [
           {
             "id": "q2",
             "question": "多选题内容",
             "options": {
               "A": "选项A",
               "B": "选项B",
               "C": "选项C"
             },
             "answer": ["A", "C"]
           }
         ]
       }
     }
     ```

### 基本指令

| 指令格式                          | 功能说明               |
| --------------------------------- | ---------------------- |
| `/shuati`                         | 显示帮助信息           |
| `/shuati [章节编号]`              | 开始指定章节的随机刷题 |
| `/shuati list`                    | 查看所有可用章节       |
| `/顺序刷题 [章节编号] [题目序号]` | 按顺序刷指定章节的题目 |
| `/wrong`                          | 从错题本练习           |
| `/wrong list`                     | 查看错题列表           |
| `/stats`                          | 查看刷题统计数据       |
| `/刷题帮助`                       | 显示详细的使用帮助信息 |

## 详细功能说明

### 1. 随机刷题

通过 `/shuati [章节编号]` 开始刷题：

```plaintext
/shuati 0  # 开始第1章的随机刷题
```

插件从指定章节随机抽题，支持单选 / 多选，答题后自动记录对错。

### 2. 顺序刷题

通过 `/顺序刷题 [章节编号] [题目序号]` 按顺序刷题：

```plaintext
/顺序刷题 0 5  # 开始第1章第6题（序号从0开始）
```

插件按章节内题目存储顺序出题，适合系统复习。

### 3. 错题本功能

使用 `/wrong` 指令复习错题：

```plaintext
/wrong  # 从错题本随机练习  
/wrong list  # 查看错题列表
```

答对后自动从错题本移除题目，支持针对性复习。

### 4. 统计功能

使用 `/stats` 查看刷题数据：

```plaintext
/stats  # 显示答题总数、正确率等统计
```

### 5. 智能提醒

当错题本累计 50 道题时，插件自动发送提醒消息，建议复习。

## 数据存储

- **题目数据**：`AstrBot/data/plugins/shuati/data/`
- **用户数据**：`AstrBot/data/plugins/shuati/data/shuati_user_data/`
  用户数据以 JSON 格式存储，插件更新时不会丢失。

## 开发信息

### 插件结构

```plaintext
shuati/
├── main.py              # 插件主逻辑
├── data/                # 数据目录  
│   ├── shuati_user_data/ # 用户错题与统计数据  
│   └── *.json           # 章节题目数据  
├── requirements.txt     # 依赖文件  
└── README.md            # 说明文档  
```

### 注意事项

1. 题目数据需放在 `data/` 目录，格式为 JSON
2. 用户数据自动存储在 `data/shuati_user_data/`，请勿手动修改
3. 插件卸载时会自动保存所有用户数据

## 贡献与反馈

如需反馈问题或提交代码，可通过 [GitHub 仓库](https://github.com/xiazhimiao/shuati) 提交 Issue。
QQ 交流群：1025462347
