import os
import json
import random
import time
from typing import Dict, List, Tuple, Union, Optional

import astrbot.api.message_components as Comp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.session_waiter import session_waiter, SessionController, SessionFilter

# 数据存储路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USER_DATA_DIR = os.path.join(DATA_DIR, "shuati_user_data")


@register("shuati", "xiazhimiao", "期末考试刷题插件（带错题本功能）", "1.9", "https://github.com/xiazhimiao/shuati")
class ShuatiPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.questions: Dict[str, Dict] = {}
        self.chapter_keys: List[str] = []
        self.user_data: Dict[str, Dict] = {}  # 缓存用户数据
        self._load_all_chapters()
        self._ensure_user_data_dir_exists()
        logger.info("Shuati 插件初始化完成")

    def _ensure_user_data_dir_exists(self):
        """确保用户数据目录存在"""
        if not os.path.exists(USER_DATA_DIR):
            os.makedirs(USER_DATA_DIR)

    def _load_all_chapters(self):
        """加载所有章节题目数据"""
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".json"):
                path = os.path.join(DATA_DIR, fname)
                with open(path, encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        for chapter_title, content in data.items():
                            self.questions[chapter_title] = content
                            self.chapter_keys.append(chapter_title)
                    except Exception as e:
                        logger.error(f"加载 {fname} 时出错: {e}")

    def _get_random_question(self, chapter: str) -> Tuple[Dict, str]:
        """从指定章节获取随机题目"""
        section = self.questions.get(chapter)
        if not section:
            return None, None

        q_type = random.choice(["single", "multiple"])
        q_list = section.get(q_type, [])
        if not q_list:
            return None, None

        question = random.choice(q_list)
        return question, q_type

    def _get_chapter_questions(self, chapter: str) -> List[Dict]:
        """获取指定章节的所有题目（按存储顺序排列）"""
        section = self.questions.get(chapter)
        if not section:
            return []
        
        # 合并单选和多选题，保持原始顺序
        all_questions = []
        for q_type in ["single", "multiple"]:
            all_questions.extend(section.get(q_type, []))
        return all_questions

    def _get_question_by_index(self, chapter: str, index: int) -> Tuple[Dict, str]:
        """按索引获取章节中的题目及题型"""
        questions = self._get_chapter_questions(chapter)
        if index < 0 or index >= len(questions):
            return None, None
        
        question = questions[index]
        q_type = "single" if len(question.get("answer", "")) == 1 else "multiple"
        return question, q_type

    def _format_question(self, question: Dict, q_type: str) -> str:
        """格式化题目展示（修改多选题提示为空格分隔）"""
        opts = "\n".join([f"{key}. {val}" for key, val in question["options"].items()])
        # 多选题提示改为空格分隔
        tips = "（多选题，请用 A B 格式作答）" if q_type == "multiple" else "（单选题）"
        return f"{question['question']}\n{opts}\n{tips}"

    def _get_user_data(self, user_id: str) -> Dict:
        """获取用户数据（从缓存或文件加载）"""
        if user_id in self.user_data:
            return self.user_data[user_id]
        
        user_data_path = os.path.join(USER_DATA_DIR, f"{user_id}.json")
        if os.path.exists(user_data_path):
            try:
                with open(user_data_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.user_data[user_id] = data
                    return data
            except Exception as e:
                logger.error(f"加载用户 {user_id} 数据时出错: {e}")
        
        # 初始化用户数据
        self.user_data[user_id] = {
            "wrong_questions": [],
            "total_questions": 0,
            "correct_questions": 0,
            "showed_50_wrong_tip": False
        }
        return self.user_data[user_id]

    def _save_user_data(self, user_id: str):
        """保存用户数据到文件"""
        if user_id not in self.user_data:
            return
        
        user_data_path = os.path.join(USER_DATA_DIR, f"{user_id}.json")
        try:
            with open(user_data_path, "w", encoding="utf-8") as f:
                json.dump(self.user_data[user_id], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户 {user_id} 数据时出错: {e}")

    def _add_wrong_question(self, user_id: str, question: Dict, chapter: str, q_type: str, event: AstrMessageEvent):
        """添加错题到用户错题本（新增50题检测）"""
        user_data = self._get_user_data(user_id)
        # 检查是否已存在该错题（避免重复添加）
        question_id = question.get("id", None)
        if question_id:
            existing = [q for q in user_data["wrong_questions"] if q.get("id") == question_id]
            if existing:
                return
        
        # 添加错题
        wrong_question = {
            "chapter": chapter,
            "type": q_type,
            "question": question["question"],
            "options": question["options"],
            "answer": question["answer"],
            "id": question.get("id", random.randint(1000, 9999))  # 生成临时ID
        }
        user_data["wrong_questions"].append(wrong_question)
        user_data["total_questions"] += 1
        
        # 检测错题数量是否达到50且未提示
        if len(user_data["wrong_questions"]) == 50 and not user_data["showed_50_wrong_tip"]:
            user_name = event.get_sender_name()
            tips = f"📢 {user_name}，你的错题集已累计50道题！\n立即使用 /wrong 开始针对性复习吧～"
            event.send(event.plain_result(tips))  # 发送提醒消息
            user_data["showed_50_wrong_tip"] = True  # 标记已提示
        
        self._save_user_data(user_id)
        logger.info(f"用户 {user_id} 添加错题: {question['question'][:20]}...")

    def _get_random_wrong_question(self, user_id: str) -> Optional[Tuple[Dict, str, str]]:
        """从用户错题本中随机获取一道错题"""
        user_data = self._get_user_data(user_id)
        wrong_questions = user_data["wrong_questions"]
        
        if not wrong_questions:
            return None
        
        question = random.choice(wrong_questions)
        chapter = question["chapter"]
        q_type = question["type"]
        return question, chapter, q_type

    @filter.command("shuati")
    async def start_quiz(self, event: AstrMessageEvent, arg: Union[str, int, None] = None):
        """启动刷题模式（支持章节选择）"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        if arg is None:
            yield event.plain_result("请输入章节编号（如：/shuati 0），或输入 /shuati list 查看章节列表。")
            return

        if isinstance(arg, str) and arg.lower() in ["list", "错题本", "wrong"]:
            if arg.lower() == "list":
                lines = [f"{i}. {name}" for i, name in enumerate(self.chapter_keys)]
                yield event.plain_result("📚 可用章节列表：\n" + "\n".join(lines))
            elif arg.lower() in ["错题本", "wrong"]:
                await self._show_or_practice_wrong_questions(event, user_id, user_name, show_only=True)
            return

        try:
            chapter_index = int(arg)
        except (ValueError, TypeError):
            yield event.plain_result("章节编号无效，请输入 /shuati list 查看章节编号。")
            return

        if chapter_index >= len(self.chapter_keys):
            yield event.plain_result("章节编号超出范围，请输入 /shuati list 查看章节编号。")
            return

        chapter = self.chapter_keys[chapter_index]
        question, q_type = self._get_random_question(chapter)
        if not question:
            yield event.plain_result("未找到该章节的题目。")
            return

        await event.send(event.plain_result(f"📖 当前章节：{chapter}\n" + self._format_question(question, q_type)))

        @session_waiter(timeout=90)
        async def wait_answer(controller: SessionController, ev: AstrMessageEvent):
            user_answer = ev.message_str.strip().upper().replace("，", " ")  # 统一替换为空格
            is_correct = False

            if q_type == "single":
                is_correct = user_answer == question["answer"]
            elif q_type == "multiple":
                correct = set(question["answer"])
                # 用空格分割答案
                given = set([x.strip() for x in user_answer.split() if x.strip()])
                is_correct = given == correct

            if is_correct:
                await ev.send(ev.plain_result("✅ 回答正确！"))
                user_data = self._get_user_data(user_id)
                user_data["correct_questions"] += 1
                self._save_user_data(user_id)
            else:
                # 多选题正确答案用空格连接展示
                correct_ans = " ".join(question["answer"]) if q_type == "multiple" else question["answer"]
                await ev.send(ev.plain_result(f"❌ 回答错误，正确答案是: {correct_ans}"))
                # 添加错题到错题本（传递event参数）
                self._add_wrong_question(user_id, question, chapter, q_type, ev)
            
            # 无论回答正确与否，处理完后立即终止会话
            controller.stop()

        try:
            await wait_answer(event)
        except Exception as e:
            logger.error(f"答题时出错: {e}")
            yield event.plain_result("发生错误或超时，已退出刷题模式。")

    @filter.command("顺序刷题")
    async def order_quiz(self, event: AstrMessageEvent):
        """按顺序刷题（格式：/顺序刷题 [章节编号] [题目序号]）"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        
        # 从原始消息中提取参数（跳过命令部分）
        command_prefix = "/顺序刷题"
        full_msg = event.message_str
        arg_str = full_msg[len(command_prefix):].strip()
        logger.info(f"order_quiz 原始参数: {arg_str}")
        
        if not arg_str:
            yield event.plain_result("请输入章节编号和题目序号（格式：/顺序刷题 [章节编号] [题目序号]）。")
            return
        
        args = arg_str.split()
        if len(args) != 2:
            yield event.plain_result("参数格式错误，需输入章节编号和题目序号（如：/顺序刷题 0 5）。")
            return
        
        try:
            chapter_idx = int(args[0])
            question_idx = int(args[1])
        except (ValueError, TypeError):
            yield event.plain_result("章节编号和题目序号必须为数字。")
            return
        
        # 验证章节有效性
        if chapter_idx < 0 or chapter_idx >= len(self.chapter_keys):
            yield event.plain_result(f"章节编号无效（0-{len(self.chapter_keys)-1}），请输入 /shuati list 查看章节。")
            return
        
        chapter = self.chapter_keys[chapter_idx]
        questions = self._get_chapter_questions(chapter)
        if not questions:
            yield event.plain_result(f"章节“{chapter}”下没有题目数据。")
            return
        
        # 验证题目序号有效性
        if question_idx < 0 or question_idx >= len(questions):
            yield event.plain_result(f"题目序号无效（0-{len(questions)-1}），该章节共有{len(questions)}道题。")
            return
        
        question, q_type = self._get_question_by_index(chapter, question_idx)
        if not question:
            yield event.plain_result("获取题目失败，请重试。")
            return
        
        await event.send(event.plain_result(f"📖 顺序刷题 - 章节：{chapter}，题目序号：{question_idx}\n" + 
                                     self._format_question(question, q_type)))
        
        @session_waiter(timeout=90)
        async def wait_answer(controller: SessionController, ev: AstrMessageEvent):
            user_answer = ev.message_str.strip().upper().replace("，", " ")  # 统一替换为空格
            is_correct = False

            if q_type == "single":
                is_correct = user_answer == question["answer"]
            elif q_type == "multiple":
                correct = set(question["answer"])
                given = set([x.strip() for x in user_answer.split() if x.strip()])
                is_correct = given == correct

            if is_correct:
                await ev.send(ev.plain_result("✅ 回答正确！"))
                user_data = self._get_user_data(user_id)
                user_data["correct_questions"] += 1
                self._save_user_data(user_id)
            else:
                # 多选题正确答案用空格连接展示
                correct_ans = " ".join(question["answer"]) if q_type == "multiple" else question["answer"]
                await ev.send(ev.plain_result(f"❌ 回答错误，正确答案是: {correct_ans}"))
                # 添加错题到错题本
                self._add_wrong_question(user_id, question, chapter, q_type, ev)
            
            # 无论回答正确与否，处理完后立即终止会话
            controller.stop()

        try:
            await wait_answer(event)
        except Exception as e:
            logger.error(f"顺序刷题时出错: {e}")
            yield event.plain_result("发生错误或超时，已退出顺序刷题模式。")

    @filter.command("wrong")
    async def practice_wrong_questions(self, event: AstrMessageEvent, arg: Union[str, None] = None):
        """从错题本练习题目（支持查看错题列表）"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        await self._show_or_practice_wrong_questions(event, user_id, user_name, show_only=(arg == "list"))

    async def _show_or_practice_wrong_questions(self, event: AstrMessageEvent, user_id: str, user_name: str, show_only: bool):
        """查看错题本或从错题本练习"""
        user_data = self._get_user_data(user_id)
        wrong_questions = user_data["wrong_questions"]
        
        if not wrong_questions:
            await event.send(event.plain_result(f"{user_name}，你的错题本还是空的哦～继续加油刷题吧！"))
            return

        if show_only:
            # 显示错题列表（最多10条）
            display_questions = wrong_questions[:10]
            msg = f"{user_name}，你的错题本（共{len(wrong_questions)}道题）：\n"
            for i, q in enumerate(display_questions):
                msg += f"\n{i+1}. {q['chapter']} - {q['question'][:20]}..."
                if i == 9:
                    msg += "\n（更多题目请通过练习模式查看）"
            await event.send(event.plain_result(msg))
            return

        # 从错题本中随机出题
        question_info = self._get_random_wrong_question(user_id)
        if not question_info:
            await event.send(event.plain_result("错题本中没有题目哦～"))
            return

        question, chapter, q_type = question_info
        await event.send(event.plain_result(f"📝 错题复习 - 章节：{chapter}\n" + self._format_question(question, q_type)))

        @session_waiter(timeout=120)
        async def wait_review_answer(controller: SessionController, ev: AstrMessageEvent):
            user_answer = ev.message_str.strip().upper().replace("，", " ")  # 统一替换为空格
            is_correct = False

            if q_type == "single":
                is_correct = user_answer == question["answer"]
            elif q_type == "multiple":
                correct = set(question["answer"])
                # 用空格分割答案
                given = set([x.strip() for x in user_answer.split() if x.strip()])
                is_correct = given == correct

            if is_correct:
                await ev.send(ev.plain_result("✅ 回答正确！这道题已经掌握啦～"))
                # 从错题本中移除正确回答的题目
                user_data = self._get_user_data(user_id)
                user_data["wrong_questions"] = [q for q in user_data["wrong_questions"] if q.get("id") != question.get("id")]
                self._save_user_data(user_id)
            else:
                # 多选题正确答案用空格连接展示
                correct_ans = " ".join(question["answer"]) if q_type == "multiple" else question["answer"]
                await ev.send(ev.plain_result(f"❌ 回答错误，正确答案是: {correct_ans}，需要继续复习哦～"))
                # 添加错题到错题本（传递event参数）
                self._add_wrong_question(user_id, question, chapter, q_type, ev)
            
            # 无论回答正确与否，处理完后立即终止会话
            controller.stop()

        try:
            await wait_review_answer(event)
        except Exception as e:
            logger.error(f"错题复习时出错: {e}")
            await event.send(event.plain_result("发生错误或超时，已退出错题复习模式。"))

    @filter.command("stats")
    async def show_statistics(self, event: AstrMessageEvent):
        """显示刷题统计数据"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        user_data = self._get_user_data(user_id)
        
        total = user_data["total_questions"]
        correct = user_data["correct_questions"]
        wrong_count = len(user_data["wrong_questions"])
        accuracy = f"{(correct / total * 100):.2f}%" if total > 0 else "0%"
        
        msg = f"{user_name} 的刷题统计：\n"
        msg += f"📊 总共答题：{total} 道\n"
        msg += f"✅ 正确数量：{correct} 道\n"
        msg += f"❌ 错题数量：{wrong_count} 道\n"
        msg += f"🎯 正确率：{accuracy}"
        
        yield event.plain_result(msg)
    
    @filter.command("刷题帮助")
    async def show_help(self, event: AstrMessageEvent):
        """显示刷题插件帮助信息"""
        help_msg = """
        📚 刷题插件帮助指南 📚
        
        一、插件基本逻辑
        1. 支持按章节随机刷题和顺序刷题
        2. 单选题直接输入选项（如A），多选题用空格分隔选项（如A B）
        3. 错题本支持针对性复习，答对后自动移除已掌握题目
        
        二、常用指令
        /shuati [章节编号]       开始指定章节随机刷题
        /顺序刷题 [章节编号] [题目序号] 按顺序刷指定章节的题目
        /shuati list            查看所有可用章节
        /wrong                  从错题本练习
        /wrong list             查看错题列表
        /stats                  查看刷题统计数据
        
        三、顺序刷题说明
        1. 格式：/顺序刷题 [章节编号] [题目序号]
        2. 章节编号从0开始，可通过 /shuati list 查看
        3. 题目序号从0开始，代表章节内题目的存储顺序
        4. 若题目序号超出范围，将提示该章节的题目总数
        """
        yield event.plain_result(help_msg.strip())

    async def terminate(self):
        """插件卸载时保存所有用户数据"""
        for user_id in self.user_data:
            self._save_user_data(user_id)
        logger.info("Shuati 插件已卸载，用户数据已保存")