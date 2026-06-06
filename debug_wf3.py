import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.workflow import create_workflow, create_step, WorkflowEngine

wf = create_workflow("simple")
step = create_step("step1", lambda x: x + 1)
wf.add_step(step)

engine = WorkflowEngine()
engine.register(wf)

print("ready before:", wf.get_ready_steps())

step_input = engine._prepare_input(step, wf)
print("step_input:", step_input)

result = step.execute(step_input)
print("result:", result)
