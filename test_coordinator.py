import sys
sys.path.insert(0, '/workspace/self_evolving_agent/core')

from system_coordinator import create_coordinator

print('=' * 60)
print('阶段91-95验证: 接口统一与协调')
print('=' * 60)

coord = create_coordinator('coord1')

# 测试1: 设置目标
coord.set_goal('safe', 0.8)
coord.set_goal('gain', 0.7)
coord.set_goal('eff', 0.6)
print('  [设置目标] OK')

# 测试2: 观察
coord._engine.predictive_coding.register_predictor(
    'test',
    lambda s: __import__('predictive_coding_engine', fromlist=['create_prediction']).create_prediction('p1', {'x': s.get('x',0)+1})
)
coord._engine.predictive_coding.register_corrector(
    'test',
    lambda e: __import__('predictive_coding_engine', fromlist=['create_correction']).create_correction('c1', e.error_id, {'w': -0.1})
)
result = coord.observe({'module_id': 'test', 'predicted': {'x': 10}, 'actual': {'x': 12}})
assert result['prediction'] is not None
print('  [观察] OK')

# 测试3: 行动
act_result = coord.act('explore', {'resources_used': {'cpu': 5.0}, 'output_value': 3.0})
assert act_result['action_taken'] is not None
print('  [行动] OK')

# 测试4: 反思
reflection = coord.reflect()
assert 'engine_stats' in reflection
assert 'consciousness_contents' in reflection
print('  [反思] OK')

# 测试5: 运行周期
cycle_result = coord.run_cycle({
    'available_actions': ['a', 'b'],
    'outcome': {'information_value': 0.6, 'safe_improvement': 0.5},
})
assert cycle_result['cycle'] >= 1
print('  [运行周期] OK')

# 测试6: 状态
status = coord.get_status()
assert status['coordinator_id'] == 'coord1'
print('  [状态] OK')

print('=' * 60)
print('阶段91-95验证通过')
print('=' * 60)
