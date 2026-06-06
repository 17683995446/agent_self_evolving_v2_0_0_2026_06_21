import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.workflow import create_workflow, create_step, WorkflowEngine

wf = create_workflow("dag")
wf.add_step(create_step("a", lambda x: 1))
wf.add_step(create_step("b", lambda x: x + 10, dependencies=["a"]))
wf.add_step(create_step("c", lambda x: x + 100, dependencies=["a"]))
wf.add_step(create_step("d", lambda x: sum(x), dependencies=["b", "c"]))

engine = WorkflowEngine()
engine.register(wf)
results = engine.execute("dag")

for k, v in results.items():
    print(f"{k}: status={v.status}, output={v.output}")
