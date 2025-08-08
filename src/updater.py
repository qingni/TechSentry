import schedule
import time

class Updater:
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
