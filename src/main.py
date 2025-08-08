from argus.config import Config
from argus.github_api import GitHubAPI
from argus.subscription import SubscriptionManager
from argus.notifier import Notifier
from argus.report_generator import ReportGenerator
from argus.updater import Updater

def run():
    config = Config()
    github_api = GitHubAPI(config.get("github_token"))
    subscription_manager = SubscriptionManager(config)
    notifier = Notifier(config.get("smtp_server"), config.get("smtp_port"), config.get("sender_email"), config.get("receiver_email"))
    report_generator = ReportGenerator([])  # Pass the actual updates here

    updater = Updater(subscription_manager, notifier, report_generator)
    updater.start()

if __name__ == "__main__":
    run()
