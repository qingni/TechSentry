class ReportGenerator:
    def __init__(self, updates):
        self.updates = updates

    def generate_report(self):
        report = "GitHub Repository Update Report\n\n"
        for update in self.updates:
            report += f"{update['actor']['login']} pushed to {update['repo']['name']}\n"
        return report
