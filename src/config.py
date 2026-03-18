import json
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)

class Config:
    def __init__(self):
        self.load_config()

    def load_config(self):
        # 从环境变量获取GitHub Token
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise EnvironmentError("环境变量GITHUB_TOKEN未设置")
        
        # 从环境变量加载通知配置
        self.notification_settings = {
            'email': {
                'smtp_server': os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', '587')),
                'email_from': os.getenv('EMAIL_FROM', ''),
                'email_to': os.getenv('EMAIL_TO', ''),
            },
            'wx_webhook_url': os.getenv('WX_WEBHOOK_URL', ''),
        }

        config_path = Path(__file__).resolve().parent.parent / 'config.json'
        with config_path.open('r', encoding='utf-8') as f:
            config = json.load(f)
            self.subscriptions_file = config.get('subscriptions_file')
            self.update_freq_days = config.get('update_frequency_days')
            self.update_execution_time = config.get('update_execution_time')

            # 加载llm相关配置
            llm_config = config.get('llm', {})
            self.llm_model_type = llm_config.get('model_type')
            self.openai_model_name = llm_config.get('openai_model_name')
            self.ollama_model_name = llm_config.get('ollama_model_name')
            self.ollama_api_url = llm_config.get('ollama_api_url')

            # 获取报告类型
            self.report_types = config.get('report_types', ['github', 'github_trend_daily'])
            