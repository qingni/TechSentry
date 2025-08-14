import os 
from openai import OpenAI

class LLM:
  def __init__(self):
    self.client = OpenAI()
    # 添加System role来定义AI的行为和输出要求
    with open("prompt/report_prompt.txt", 'r', encoding='utf-8') as f:
        self.system_prompt = f.read()
                

  def generate_daily_report(self, markdown_content, dry_run=False):
    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": markdown_content},
    ]
    if dry_run:
        with open("daily_progress/prompt.txt", "w+") as f:
            # 同时保存system prompt和user prompt以便调试
            f.write(f"System Prompt:\n{self.system_prompt}\n\nUser Prompt:\n{markdown_content}")
        test_llm_response = "# LangChain 项目进展\n\n**创建日期**: 2025-08-14  \n**时间周期**: 2025-08-13 至 2025-08-14\n\n## 新增功能\n无\n\n## 主要改进\n- 更新了README.md文档内容，以提高信息的准确性和可用性。\n\n## 修复问题\n- 修复了 ChatOpenAI 中使用 GPT-5 详细参数与结构化输出冲突导致的 ValueError 问题 (#32492)。"
        return test_llm_response
    else:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        print(response)
    return response.choices[0].message.content

