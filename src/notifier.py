import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logger import LOG
import os
import markdown2
class Notifier:
    def __init__(self, notification_settings):
        self.notification_settings = notification_settings

    def notify(self, repo, report):
        if self.notification_settings:
            self.send_email(repo, report)
        else:
            LOG.warning("未配置通知设置")
    
    def send_email(self, repo, report):
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = self.notification_settings['email']['email_from']
        msg['To'] = self.notification_settings['email']['email_to']
        msg['Subject'] = f"{repo} 进展报告"""

        # 将Markdown内容转换为HTML
        html_report = markdown2.markdown(report)
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
            print("邮件发送成功！")
            return True
        except smtplib.SMTPAuthenticationError:
            print("认证失败！请检查邮箱地址和密码是否正确，Gmail等可能需要使用应用专用密码。")
            return False
        except Exception as e:
            print(f"发送邮件时发生错误: {str(e)}")
            return False
        
if __name__ == "__main__":
    from config import Config
    config = Config()
    notifier = Notifier(config.notification_settings)
    test_repo = "qingni/GitHubArgus"
    test_report = "Test report content"
    notifier.notify(test_repo, test_report)
