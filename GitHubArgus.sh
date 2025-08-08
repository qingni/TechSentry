#!/bin/bash

# 创建项目根目录
mkdir -p GitHubArgus
cd GitHubArgus

# 创建项目结构
mkdir -p src tests

# 创建 README.md
cat <<EOL > README.md
# GitHub Argus

GitHub Argus 是一款开源工具类 AI Agent，专为开发者和项目管理人员设计，能够定期（每日/每周）自动获取并汇总订阅的 GitHub 仓库最新动态。其主要功能包括订阅管理、更新获取、通知系统、报告生成。通过及时获取和推送最新的仓库更新，GitHub Argus 大大提高了团队协作效率和项目管理的便捷性，使用户能够更高效地跟踪项目进展，快速响应和处理变更，确保项目始终处于最新状态。
EOL

# 创建 LICENSE 文件
cat <<EOL > LICENSE
MIT License

Copyright (c) 2025 GitHubArgus

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOL

# 创建 setup.py
cat <<EOL > setup.py
from setuptools import setup, find_packages

setup(
    name="GitHub Argus",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "schedule",
        "pyyaml"
    ],
    entry_points={
        "console_scripts": [
            "github-argus=scripts.run:run",
        ],
    },
)
EOL

# 创建 requirements.txt
cat <<EOL > requirements.txt
requests
schedule
pyyaml
EOL

# 创建 src/config.py
cat <<EOL > src/config.py
import yaml

class Config:
    def __init__(self, config_file="config.yaml"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_file, "r") as file:
            return yaml.safe_load(file)

    def get(self, key):
        return self.config.get(key)
EOL

# 创建 src/github_api.py
cat <<EOL > src/github_api.py
import requests

class GitHubAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.github.com"

    def get_repo_updates(self, repo):
        headers = {"Authorization": f"token {self.token}"}
        url = f"{self.base_url}/repos/{repo}/events"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch updates for {repo}")
EOL

# 创建 src/subscription.py
cat <<EOL > src/subscription.py
class SubscriptionManager:
    def __init__(self, config):
        self.config = config
        self.subscriptions = self.load_subscriptions()

    def load_subscriptions(self):
        return self.config.get("subscriptions")

    def update_subscriptions(self):
        updates = []
        for repo in self.subscriptions:
            updates.append(self.get_repo_updates(repo))
        return updates
EOL

# 创建 src/notifier.py
cat <<EOL > src/notifier.py
import smtplib
from email.mime.text import MIMEText

class Notifier:
    def __init__(self, smtp_server, smtp_port, sender_email, receiver_email):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.receiver_email = receiver_email

    def send_email(self, subject, body):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.sendmail(self.sender_email, self.receiver_email, msg.as_string())

    def notify(self, updates):
        body = "\n".join([f"{update['actor']['login']} pushed to {update['repo']['name']}" for update in updates])
        self.send_email("GitHub Repository Updates", body)
EOL

# 创建 src/report_generator.py
cat <<EOL > src/report_generator.py
class ReportGenerator:
    def __init__(self, updates):
        self.updates = updates

    def generate_report(self):
        report = "GitHub Repository Update Report\n\n"
        for update in self.updates:
            report += f"{update['actor']['login']} pushed to {update['repo']['name']}\n"
        return report
EOL

# 创建 src/scheduler.py
cat <<EOL > src/scheduler.py
import schedule
import time

class Scheduler:
    def __init__(self, subscription_manager, notifier, report_generator):
        self.subscription_manager = subscription_manager
        self.notifier = notifier
        self.report_generator = report_generator

    def check_for_updates(self):
        updates = self.subscription_manager.update_subscriptions()
        report = self.report_generator.generate_report()
        self.notifier.notify(updates)
        print(report)

    def start(self):
        schedule.every().day.at("08:00").do(self.check_for_updates)
        while True:
            schedule.run_pending()
            time.sleep(1)
EOL

# 创建 src/main.py
cat <<EOL > src/main.py
from config import Config
from github_api import GitHubAPI
from subscription import SubscriptionManager
from notifier import Notifier
from report_generator import ReportGenerator
from scheduler import Scheduler

def run():
    config = Config()
    github_api = GitHubAPI(config.get("github_token"))
    subscription_manager = SubscriptionManager(config)
    notifier = Notifier(config.get("smtp_server"), config.get("smtp_port"), config.get("sender_email"), config.get("receiver_email"))
    report_generator = ReportGenerator([])  # Pass the actual updates here

    scheduler = Scheduler(subscription_manager, notifier, report_generator)
    scheduler.start()

if __name__ == "__main__":
    run()
EOL

# 创建测试目录和测试文件
mkdir -p tests
cat <<EOL > tests/test_github_api.py
# Test GitHub API interactions here
EOL

cat <<EOL > tests/test_subscription.py
# Test Subscription management here
EOL

cat <<EOL > tests/test_notifier.py
# Test Notifier functionality here
EOL

cat <<EOL > tests/test_report_generator.py
# Test Report Generator functionality here
EOL

# 完成
echo "GitHub Argus project structure created successfully!"
