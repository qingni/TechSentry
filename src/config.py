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
