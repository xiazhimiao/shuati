import os
import json
import random
from typing import Dict, List, Tuple, Union

import astrbot.api.message_components as Comp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.utils.session_waiter import session_waiter, SessionController


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@register("shuati", "xiazhimiao", "期末考试刷题插件", "1.0", "https://github.com/xiazhimiao/shuati")
class ShuatiPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.questions: Dict[str, Dict] = {}
        self.chapter_keys: List[str] = []
        self._load_all_chapters()

    def _load_all_chapters(self):
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
        section = self.questions.get(chapter)
        if not section:
            return None, None

        q_type = random.choice(["single", "multiple"])
        q_list = section.get(q_type, [])
        if not q_list:
            return None, None

        question = random.choice(q_list)
        return question, q_type

    def _format_question(self, question: Dict, q_type: str) -> str:
        opts = "\n".join([f"{key}. {val}" for key, val in question["options"].items()])
        tips = "（多选题，请用 A,B 格式作答）" if q_type == "multiple" else "（单选题）"
        return f"{question['question']}\n{opts}\n{tips}"

    @filter.command("shuati")
    async def start_quiz(self, event: AstrMessageEvent, arg: Union[str, int, None] = None):
        if arg is None:
            yield event.plain_result("请输入章节编号（如：/shuati 0），或输入 /shuati list 查看章节列表。")
            return

        if isinstance(arg, str) and arg.lower() == "list":
            lines = [f"{i}. {name}" for i, name in enumerate(self.chapter_keys)]
            yield event.plain_result("📚 可用章节列表：\n" + "\n".join(lines))
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
            user_answer = ev.message_str.strip().upper().replace("，", ",")

            if q_type == "single":
                if user_answer == question["answer"]:
                    await ev.send(ev.plain_result("✅ 回答正确！"))
                else:
                    await ev.send(ev.plain_result(f"❌ 回答错误，正确答案是: {question['answer']}"))
            elif q_type == "multiple":
                correct = set(question["answer"])
                given = set([x.strip() for x in user_answer.split(",") if x.strip()])
                if given == correct:
                    await ev.send(ev.plain_result("✅ 回答正确！"))
                else:
                    correct_ans = ",".join(question["answer"])
                    await ev.send(ev.plain_result(f"❌ 回答错误，正确答案是: {correct_ans}"))

            controller.stop()

        try:
            await wait_answer(event)
        except Exception as e:
            logger.error(f"答题时出错: {e}")
            yield event.plain_result("发生错误或超时，已退出刷题模式。")

    async def terminate(self):
        logger.info("Shuati 插件已卸载")
