import json
import os
class Config:
    def __init__(self):
        self.load_config()

    def load_config(self):
        # 从环境变量获取GitHub Token
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise EnvironmentError("环境变量GITHUB_TOKEN未设置")
        with open('config.json', 'r') as f:
            config = json.load(f)
            self.notification_settings = config.get('notification_settings')
            self.subscriptions_file = config.get('subscriptions_file')
            self.update_freq_days = config.get('update_frequency_days')
            self.update_execution_time = config.get('update_execution_time')
            self.notification_settings = config.get('notification_settings')
            
            # 加载llm相关配置
            llm_config = config.get('llm', {})
            self.llm_model_type = llm_config.get('model_type')
            self.openai_model_name = llm_config.get('openai_model_name')
            self.ollama_model_name = llm_config.get('ollama_model_name')
            self.ollama_api_url = llm_config.get('ollama_api_url')
            
            # 获取报告类型
            self.report_types = config.get('report_types', ['github', 'github_trend_daily'])
            