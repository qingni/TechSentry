import os 
from logger import LOG
from openai import OpenAI
from config import Config
class LLM:
    def __init__(self, config):
        """初始化LLM类
        
        Args:
            config (Config): 配置对象，包含LLM相关配置
        """
        self.config = config
        self.model_type = config.llm_model_type.lower()
        if self.model_type == "openai":
            self.client = OpenAI()
        elif self.model_type == "ollama":
            self.client = OpenAI(
                base_url=self.config.ollama_api_url,  # Ollama 的 OpenAI‑compatible API
                api_key="ollama",                     # 任意字符串，Ollama 不校验
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
        
        # 添加System role来定义AI的行为和输出要求
        with open("prompt/report_prompt.txt", 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
        LOG.add("logs/llm.log", rotation="1 MB", level="DEBUG")     
                

    def generate_daily_report(self, markdown_content, dry_run=False):
        """生成日报内容
        
        Args:
            markdown_content (str): 原始Markdown格式的日报内容
            dry_run (bool, optional): 是否试运行模式. 默认为False
            
        Returns:
            str: 生成的日报内容
        """
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

        if self.model_type == "openai":
            return self.generate_daily_report_openai(messages)
        elif self.model_type == "ollama":
            return self.generate_daily_report_ollama(messages)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
           
        
    def generate_daily_report_openai(self, messages):
        """使用OpenAI模型生成日报
        
        Args:
            messages (list): 包含系统提示和用户消息的列表
            
        Returns:
            str: 模型生成的日报内容，出错时返回None
        """
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
        
    def generate_daily_report_ollama(self, messages):
        """使用Ollama模型生成日报
        
        Args:
            messages (list): 包含系统提示和用户消息的列表
            
        Returns:
            str: 模型生成的日报内容，出错时返回None
        """
        LOG.info("Starting report generation in ollama mode.")
        try:
            response = self.client.chat.completions.create(
                model=self.config.ollama_model_name,  # 你刚拉取的模型名称
                messages=messages,
                temperature=0.7,
                stream=False,          # 如果想要流式返回请改为 True
            )

            LOG.debug("GPT response: {}", response)
            return response.choices[0].message.content
        except Exception as e:
            LOG.error("Error occurred while generating report: {}", e)
            return None

if __name__ == "__main__":
    config = Config()
    llm = LLM(config)
    
    markdown_content = """# Daily Progress for ollama/ollama

**Report Create Date**: 2025-08-15

**Report Time Range**: 2025-08-14 至 2025-08-15

## Issues
-  Disable Thinking Mode #10492
-  Allow context to be set from the command line. #8356
-  Lates version of olllama (installer 0.9.6) on Windows not running "olllama app" #11556

## Pull Requests
-  New Memory Management #11090
-  Revert "cuda: leverage JIT for smaller footprint (#11635)" #11913
-  fix arm linux build when HWCAP2_SVE2 undefined #11908
-  convert: skip reading into memory when possible #11507
-  update vendored llama.cpp and ggml #11823
-  doc: clarify both rocm and main bundle necessary #11900

"""
    llm.generate_daily_report(markdown_content)