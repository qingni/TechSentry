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
