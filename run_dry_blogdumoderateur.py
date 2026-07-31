from dataharvest.config import Config
from dataharvest.orchestrator import Orchestrator

cfg = Config('configs/blogdumoderateur.yaml')
report = Orchestrator(cfg).run(dry_run=True)
print(report)
