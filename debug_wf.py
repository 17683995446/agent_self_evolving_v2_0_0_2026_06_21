import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.workflow import create_workflow, create_step, WorkflowEngine

wf = create_workflow("simple")
wf.add_step(create_step("step1", lambda x: x + 1))

engine = WorkflowEngine()
engine.register(wf)

results = engine.execute("simple", 10)
for k, v in results.items():
    print(f"{k}: status={v.status}, output={v.output}")
print("wf status:", wf.get_status())
