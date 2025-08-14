import os 
from openai import OpenAI
from logger import LOG

class LLM:
  def __init__(self):
    self.client = OpenAI()
    # 添加System role来定义AI的行为和输出要求
    with open("prompt/report_prompt.txt", 'r', encoding='utf-8') as f:
        self.system_prompt = f.read()
    LOG.add("logs/llm.log", rotation="1 MB", level="DEBUG")
                

  def generate_daily_report(self, markdown_content, dry_run=False):
    messages = [
        {"role": "system", "content": self.system_prompt},
        {"role": "user", "content": markdown_content},
    ]
    # 试运行，先输出prompt到文件调试用，调试成功给到llm，可避免浪费过多的token
    if dry_run:
        LOG.info("Dry run mode enabled. Saving prompt to daily_progress/prompt.txt.")
        with open("daily_progress/prompt.txt", "w+") as f:
            # 同时保存system prompt和user prompt以便调试
            f.write(f"System Prompt:\n{self.system_prompt}\n\nUser Prompt:\n{markdown_content}")
        LOG.debug(f"Prompt saved to daily_progress/prompt.txt")
        test_llm_response = markdown_content
        return test_llm_response
    else:
        LOG.info("Starting report generation in GPT mode.")
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
             )
            LOG.debug("GPT response: {}", response)
            return response.choices[0].message.content
        except Exception as e:
            LOG.error("Error occurred while generating report: {}", e)
            return None
        

