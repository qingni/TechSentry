import os 
from openai import OpenAI

class LLM:
  def __init__(self):
    self.client = OpenAI()

  def generate_daily_report(self, markdown_content, dry_run=False):
    # 添加System role来定义AI的行为和输出要求
    system_prompt = """
    作为项目管理助理，按以下要求整理项目进展为简报：
    1. 分"新增功能"、"主要改进"、"修复问题"三部分
    2. 同类项合并，语言简洁，突出关键信息
    3. 避免过多技术术语，每项一句话
    4. 使用清晰的markdown格式
    """
    
    user_prompt = f"以下是项目的最新进展，请根据上述要求整理形成一份简报：\n\n{markdown_content}"
    
    if dry_run:
        with open("daily_progress/prompt.txt", "w+") as f:
            # 同时保存system prompt和user prompt以便调试
            f.write(f"System Prompt:\n{system_prompt}\n\nUser Prompt:\n{user_prompt}")
        return "DRY RUN"
    else:
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt.strip()  # 去除多余空白
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )
        print(response)
    return response.choices[0].message.content

