import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.workflow import create_workflow, create_step, WorkflowEngine

wf = create_workflow("parallel")
wf.add_step(create_step("a", lambda x: 1))
wf.add_step(create_step("b", lambda x: 2))
wf.add_step(create_step("c", lambda x: sum(x), dependencies=["a", "b"]))

engine = WorkflowEngine()
engine.register(wf)
results = engine.execute("parallel")

for k, v in results.items():
    print(f"{k}: status={v.status}, output={v.output}")
