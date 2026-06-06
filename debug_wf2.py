import sys
sys.path.insert(0, '/workspace')

from self_evolving_agent.core.workflow import create_workflow, create_step, WorkflowEngine

wf = create_workflow("simple")
step = create_step("step1", lambda x: x + 1)
wf.add_step(step)

print("step.fn:", step.fn)
print("step.fn(10):", step.fn(10))

result = step.execute(10)
print("result:", result)
print("result.status:", result.status)
print("result.output:", result.output)
