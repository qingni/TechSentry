class ReportGenerator:
    def generate_report(self, updates):
        # 添加最新版本信息
        report = "Latest Release Information:\n"
        for repo, release in updates.items():
            report += f"Repository: {repo}\n"
            report += f"Latest Version: {release['tag_name']}\n"
            report += f"Release Name: {release['name']}\n"
            report += f"Published at: {release['published_at']}\n"
            report += f"Release Notes:\n{release['body']}\n"
            report += "-" * 40 + "\n"
        return report
