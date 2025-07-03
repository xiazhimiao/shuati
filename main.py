from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import os
import json
import random
from typing import Dict, List, Optional

@register(
    name="shuati",
    author="xiazhimiao",
    desc="自定义JSON题库刷题插件",
    version="1.0.1",
    repo="https://github.com/xiazhimiao/shuati"
)
class ShuatiPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 修复：使用context.data_path获取插件数据目录
        self.data_dir = context.data_path
        
        self.questions_dir = os.path.join(self.data_dir, "questions")
        self.user_progress_dir = os.path.join(self.data_dir, "progress")
        
        # 创建目录
        for dir_path in [self.data_dir, self.questions_dir, self.user_progress_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # 加载用户提供的JSON题库（优先加载custom_questions.json）
        self.questions = self._load_questions()
        self.user_progress = self._load_user_progress()
        logger.info(f"shuati插件初始化完成，已加载{len(self.questions)}道题目")
    
    def _load_questions(self) -> Dict[str, Dict]:
        """加载题库（优先使用用户提供的custom_questions.json）"""
        custom_questions_path = os.path.join(self.questions_dir, "custom_questions.json")
        default_questions_path = os.path.join(self.questions_dir, "default_questions.json")
        
        # 先尝试加载用户自定义题库
        if os.path.exists(custom_questions_path):
            try:
                with open(custom_questions_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载自定义题库失败，使用默认题库: {e}")
        
        # 加载默认题库
        if os.path.exists(default_questions_path):
            try:
                with open(default_questions_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载默认题库失败: {e}")
        
        logger.warning("题库文件不存在，插件将使用空题库")
        return {}
    
    def _save_questions(self, questions: Dict[str, Dict]):
        """保存题库数据"""
        custom_questions_path = os.path.join(self.questions_dir, "custom_questions.json")
        try:
            with open(custom_questions_path, "w", encoding="utf-8") as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存题库失败: {e}")
    
    def _load_user_progress(self) -> Dict[str, Dict]:
        """加载用户进度数据"""
        progress_path = os.path.join(self.user_progress_dir, "progress.json")
        if os.path.exists(progress_path):
            try:
                with open(progress_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载用户进度失败: {e}")
        return {}
    
    def _save_user_progress(self, progress: Dict[str, Dict]):
        """保存用户进度数据"""
        progress_path = os.path.join(self.user_progress_dir, "progress.json")
        try:
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户进度失败: {e}")
    
    def _get_user_progress(self, user_id: str) -> Dict:
        """获取用户进度（不存在则初始化）"""
        progress = self.user_progress.get(user_id, {
            "solved": [],
            "attempts": 0,
            "correct": 0,
            "current": None
        })
        self.user_progress[user_id] = progress
        return progress
    
    def _save_user(self, user_id: str, progress: Dict):
        """保存单个用户进度"""
        self.user_progress[user_id] = progress
        self._save_user_progress(self.user_progress)
    
    # 注册主指令：/shuati
    @filter.command("shuati")
    async def shuati_help(self, event: AstrMessageEvent):
        """刷题插件帮助指令"""
        help_text = "🌟 欢迎使用shuati刷题插件！\n"
        help_text += "/shuati list - 查看所有可刷题目\n"
        help_text += "/shuati solve [题目ID] - 开始解答题目\n"
        help_text += "/shuati submit [题目ID] [答案] - 提交解题答案\n"
        help_text += "/shuati progress - 查看个人刷题进度\n"
        help_text += "/shuati hint [题目ID] - 获取题目提示"
        yield event.plain_result(help_text)
    
    # 列出所有题目
    @filter.command("shuati list")
    async def list_problems(self, event: AstrMessageEvent):
        """列出所有题目"""
        questions = self.questions
        if not questions:
            yield event.plain_result("题库中暂无题目，请检查custom_questions.json是否正确")
            return
        
        user_id = event.get_sender_id()
        user_progress = self._get_user_progress(user_id)
        solved_ids = set(user_progress["solved"])
        
        result = "📝 可刷题目列表：\n"
        for qid, data in questions.items():
            status = "✅" if qid in solved_ids else "❌"
            result += f"【{status}】题目ID: {qid} - {data['title']} ({data.get('difficulty', '未知难度')})\n"
            result += f"  描述: {data.get('description', '无描述')}\n"
        
        yield event.plain_result(result)
    
    # 开始解题
    @filter.command("shuati solve")
    async def solve_problem(self, event: AstrMessageEvent, problem_id: str):
        """开始解答指定题目"""
        problem = self.questions.get(problem_id)
        if not problem:
            yield event.plain_result(f"题目ID {problem_id} 不存在，请使用 /shuati list 查看有效题目")
            return
        
        user_id = event.get_sender_id()
        user_progress = self._get_user_progress(user_id)
        user_progress["current"] = problem_id
        self._save_user(user_id, user_progress)
        
        problem_content = f"🚀 开始解答题目 ID: {problem_id} - {problem['title']}\n\n"
        problem_content += f"📝 题目描述：\n{problem.get('description', '无题目描述')}\n\n"
        problem_content += "💡 请思考解题思路，使用 /shuati submit [题目ID] [答案] 提交解答\n"
        problem_content += f"提示：输入 /shuati hint {problem_id} 获取解题思路"
        
        yield event.plain_result(problem_content)
    
    # 提交答案
    @filter.command("shuati submit")
    async def submit_answer(self, event: AstrMessageEvent, problem_id: str, answer: str):
        """提交题目答案"""
        problem = self.questions.get(problem_id)
        if not problem:
            yield event.plain_result(f"题目ID {problem_id} 不存在，请先使用 /shuati solve [题目ID] 开始解题")
            return
        
        user_id = event.get_sender_id()
        user_progress = self._get_user_progress(user_id)
        
        # 检查是否正在解答该题目
        if user_progress["current"] != problem_id:
            yield event.plain_result(f"请先使用 /shuati solve {problem_id} 开始解答该题目")
            return
        
        user_progress["attempts"] += 1
        is_correct = self._check_answer(problem, answer)
        
        if is_correct:
            user_progress["correct"] += 1
            if problem_id not in user_progress["solved"]:
                user_progress["solved"].append(problem_id)
            result = f"🎉 恭喜！你的解答通过了题目 {problem_id}《{problem['title']}》\n"
            result += f"✅ 这是你解决的第 {len(user_progress['solved'])} 道题目"
        else:
            result = f"❌ 很遗憾，你的解答未能通过题目 {problem_id}《{problem['title']}》\n"
            result += f"💡 提示：可以输入 /shuati hint {problem_id} 获取解题思路，再试一次！"
        
        user_progress["current"] = None
        self._save_user(user_id, user_progress)
        yield event.plain_result(result)
    
    def _check_answer(self, problem: Dict, answer: str) -> bool:
        """检查答案是否正确"""
        correct_answer = problem.get("correct_answer", "").lower()
        user_answer = answer.lower()
        
        # 简单匹配：答案包含正确答案关键词
        return correct_answer in user_answer or user_answer in correct_answer
    
    # 获取题目提示
    @filter.command("shuati hint")
    async def get_hint(self, event: AstrMessageEvent, problem_id: str):
        """获取题目提示"""
        problem = self.questions.get(problem_id)
        if not problem:
            yield event.plain_result(f"题目ID {problem_id} 不存在，请使用 /shuati list 查看有效题目")
            return
        
        user_id = event.get_sender_id()
        user_progress = self._get_user_progress(user_id)
        
        # 检查是否已尝试或正在解答该题目
        if problem_id not in user_progress["solved"] and user_progress["current"] != problem_id:
            yield event.plain_result(f"请先使用 /shuati solve {problem_id} 开始解答，再获取提示")
            return
        
        hint = f"💡 题目《{problem['title']}》提示：\n{problem.get('hint', '暂无提示信息')}"
        yield event.plain_result(hint)
    
    # 查看刷题进度
    @filter.command("shuati progress")
    async def check_progress(self, event: AstrMessageEvent):
        """查看个人刷题进度"""
        user_id = event.get_sender_id()
        user_progress = self._get_user_progress(user_id)
        total_questions = len(self.questions)
        solved_count = len(user_progress["solved"])
        attempts = user_progress["attempts"]
        correct = user_progress["correct"]
        
        accuracy = f"{correct/attempts:.2%}" if attempts > 0 else "0.00%"
        
        progress = "📊 刷题进度报告：\n"
        progress += f"用户: {event.get_sender_name()}\n"
        progress += f"已完成: {solved_count}/{total_questions} 题\n"
        progress += f"总尝试: {attempts} 次\n"
        progress += f"正确率: {accuracy}\n"
        
        if solved_count > 0:
            progress += "\n最近解决的题目：\n"
            for pid in user_progress["solved"][-3:]:
                problem = self.questions.get(pid)
                if problem:
                    progress += f"- 题目ID: {pid} - {problem['title']}\n"
        
        yield event.plain_result(progress)
    
    async def terminate(self):
        """插件卸载时清理资源"""
        self._save_user_progress(self.user_progress)
        logger.info("shuati插件已卸载，资源清理完成")