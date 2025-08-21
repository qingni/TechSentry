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
                base_url=self.get_ollama_base_url(),  # 自动适应容器环境
                api_key="ollama",
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

        LOG.add("logs/llm.log", rotation="1 MB", level="DEBUG")     
    
    def get_ollama_base_url(self):
        """
        自动判断运行环境，返回合适的Ollama基础地址
        - 容器内环境：使用host.docker.internal
        - 本地环境：使用localhost
        """
        # 方法1：检查是否存在容器特征文件（推荐）
        if os.path.exists("/.dockerenv"):
            return "http://host.docker.internal:11434/v1"
        
        # 方法2：检查是否有Docker相关环境变量（备选）
        if "DOCKER_HOST" in os.environ or "container" in os.environ.get("HOSTNAME", ""):
            return "http://host.docker.internal:11434/v1"
        
        # 默认使用本地地址
        return self.config.ollama_api_url         

    def generate_daily_report(self, system_prompt, markdown_content, dry_run=False):
        """生成日报内容
        
        Args:
            markdown_content (str): 原始Markdown格式的日报内容
            dry_run (bool, optional): 是否试运行模式. 默认为False
            
        Returns:
            str: 生成的日报内容
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markdown_content},
        ]
        # 试运行，先输出prompt到文件调试用，调试成功给到llm，可避免浪费过多的token
        if dry_run:
            LOG.info("Dry run mode enabled. Saving prompt to prompts/dry_run_prompt.txt.")
            with open("prompts/dry_run_prompt.txt", "w+") as f:
                # 同时保存system prompt和user prompt以便调试
                f.write(f"System Prompt:\n{system_prompt}\n\nUser Prompt:\n{markdown_content}")
            LOG.debug(f"Prompt saved to prompts/dry_run_prompt.txt")
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
    system_prompt = """作为项目管理助理，按以下要求整理项目进展为中文简报：
1. 分"新增功能"、"主要改进"、"修复问题"三部分
2. 同类项合并，语言简洁，突出关键信息
3. 避免过多技术术语，每项一句话
4. 使用清晰的markdown格式
    
参考示例如下：

# LangChain 项目进展

**创建日期**: 2025-08-12 17:17:07  
**时间周期**: 2025-08-11 17:17:07 至 2025-08-12 17:17:07

## 新增功能
- 增加了对JSON类输入的字符串解析功能。
- 添加了Desearch集成。
- 提升了针对vLLM兼容性的错误消息。
- 增设了DeepSeek模型选项。
- 增加了TrueFoundry AI网关的文档。

## 主要改进
- 文档中新增了Linux JaguarDB快速设置方法及Google合作伙伴指南。
- 重构了部分代码，去除了`sentence-transformers`依赖。
- 更新了`standard-tests`及文档对Tool Artifacts与Injected State的说明。
- 切割器的元素迭代器增加了反向保留功能。

## 修复问题
- 修正了RAG教程中关于当qdrant作为向量存储时未找到集合的错误处理。
- 更新了有关`llamacpp.ipynb`的安装选项文档。
- 修复了关于Spider网页加载器的文档说明。
- 修复了文档中语法、大小写和样式的问题。"""
    
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


    llm.generate_daily_report(system_prompt, markdown_content, dry_run=True)