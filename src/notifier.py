import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logger import LOG
import os
import markdown2
import requests
import json
class Notifier:
    def __init__(self, notification_settings):
        self.notification_settings = notification_settings

    def notify_github(self, repo, report):
        if self.notification_settings:
            subject=f"{repo} 进展报告"
            self.send_email(subject, report)
            self.send_wecom_robot(report)
        else:
            LOG.warning("未配置通知设置")
    
    def notify_github_trend(self, report):
        if self.notification_settings:
            subject="GitHub Trend 每日报告"
            self.send_email(subject, report)
            self.send_wecom_robot(report)
        else:
            LOG.warning("未配置通知设置")
    
    def notify_hack_news_daily(self, report):
        if self.notification_settings:
            subject="Hacker News 每日报告"
            self.send_email(subject, report)
            self.send_wecom_robot(report)
        else:
            LOG.warning("未配置通知设置")
    
    def send_email(self, subject, report):
        """
        发送消息到邮箱
        :param subject: 邮件主题
        :param report: 消息内容(markdown格式)
        """
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = self.notification_settings['email']['email_from']
        msg['To'] = self.notification_settings['email']['email_to']
        msg['Subject'] = subject

        # 确保report是字符串类型
        if not isinstance(report, str):
            LOG.warning(f"报告类型错误: {type(report)}，期望字符串类型")
            # 尝试转换为字符串
            if isinstance(report, tuple):
                # 如果是元组，尝试拼接元素
                report = '\n'.join(str(item) for item in report)
            else:
                report = str(report)
            
            LOG.info(f"已转换报告为字符串，长度: {len(report)}")

        # 将Markdown内容转换为HTML
        try:
            html_report = markdown2.markdown(report)
        except Exception as e:
            LOG.error(f"Markdown转换失败: {str(e)}")
            # 记录部分报告内容用于调试
            sample = report[:100] + "..." if len(report) > 100 else report
            LOG.info(f"报告样本内容: {sample}")
            raise
            
        # 添加邮件正文
        msg.attach(MIMEText(html_report, 'html'))

        smtp_server = self.notification_settings['email']['smtp_server']
        smtp_port = self.notification_settings['email']['smtp_port']
        sender_password = os.getenv('GMAIL_SPECIAL_PASSWORD')
        if not sender_password:
            raise EnvironmentError("环境变量GMAIL_SPECIAL_PASSWORD未设置")
        try:
            # 连接到 Gmail SMTP 服务器
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # 启用 TLS 加密
                server.login(msg['From'], sender_password)
                server.sendmail(msg['From'], msg['To'], msg.as_string())
            LOG.info("邮件发送成功！")
            return True
        except smtplib.SMTPAuthenticationError:
            LOG.error("认证失败！请检查邮箱地址和密码是否正确，Gmail等可能需要使用应用专用密码。")
            return False
        except Exception as e:
            LOG.error(f"发送邮件时发生错误: {str(e)}")
            return False
        
    def send_wecom_robot(self, content, msg_type="markdown"):
        """
        发送消息到企业微信群机器人
        :param webhook_url: 机器人webhook地址(从企微机器人配置页面获取)
        :param content: 消息内容(根据消息类型不同格式不同)
        :param msg_type: 消息类型(text/markdown/image等)
        """
        
        webhook_url = self.notification_settings['wx_webhook_url']
        headers = {"Content-Type": "application/json"}
        
        # 构造消息体(支持多种消息类型)
        message = {
            "msgtype": msg_type,
            msg_type: {
                "content": content
            }
        }
        
        response = requests.post(webhook_url, 
                            headers=headers,
                            data=json.dumps(message))
        LOG.info("企微机器人消息发送成功！")
        return response.json()
        
if __name__ == "__main__":
    from config import Config
    config = Config()
    notifier = Notifier(config.notification_settings)
    test_repo = "qingni/TechSentry"
    test_report = "Test report content"
    notifier.notify_github(test_repo, test_report)
    
    notifier.send_wecom_robot(test_report)
