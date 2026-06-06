import sys
import importlib.util

# 手动加载所有需要的模块，避免触发 __init__.py

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

base = '/workspace/self_evolving_agent/core'

# 按依赖顺序加载，保留模块引用
pce = load_module('pce', f'{base}/predictive_coding_engine.py')
dfp = load_module('dfp', f'{base}/drive_first_principles.py')
lfp = load_module('lfp', f'{base}/learning_first_principles.py')
efp = load_module('efp', f'{base}/exploration_first_principles.py')
mfp = load_module('mfp', f'{base}/memory_first_principles.py')
evfp = load_module('evfp', f'{base}/evolution_first_principles.py')
sfp = load_module('sfp', f'{base}/safety_first_principles.py')
effp = load_module('effp', f'{base}/efficiency_first_principles.py')
sofp = load_module('sofp', f'{base}/social_first_principles.py')
cfp_c = load_module('cfp_c', f'{base}/creativity_first_principles.py')
caufp = load_module('caufp', f'{base}/causal_first_principles.py')
metafp = load_module('metafp', f'{base}/metacognition_first_principles.py')
emfp = load_module('emfp', f'{base}/emotion_first_principles.py')
confp = load_module('confp', f'{base}/consciousness_first_principles.py')
fwfp = load_module('fwfp', f'{base}/free_will_first_principles.py')

# 将core目录加入path，使绝对导入能工作
sys.path.insert(0, base)

# 最后加载统一引擎
ufp = load_module('ufp', f'{base}/unified_first_principles_engine.py')

print('=' * 60)
print('阶段86-90验证: 核心引擎整合')
print('=' * 60)

engine = ufp.create_unified_engine('unified1')

# 测试1: 所有子引擎已初始化
assert engine.predictive_coding is not None
assert engine.drive is not None
assert engine.learning is not None
assert engine.exploration is not None
assert engine.memory is not None
assert engine.evolution is not None
assert engine.safety is not None
assert engine.efficiency is not None
assert engine.social is not None
assert engine.creativity is not None
assert engine.causal is not None
assert engine.metacognition is not None
assert engine.emotion is not None
assert engine.consciousness is not None
assert engine.free_will is not None
print('  [所有子引擎初始化] OK')

# 测试2: 感知与预测（先注册预测器）
engine.predictive_coding.register_predictor(
    'test_module',
    lambda state: pce.create_prediction('pred1', {'x': state.get('x', 0) + 1})
)
engine.predictive_coding.register_corrector(
    'test_module',
    lambda error: pce.create_correction('corr1', error.error_id, {'w': -0.1})
)
result = engine.perceive_and_predict('test_module', {'x': 10}, {'x': 12})
assert result['prediction'] is not None
assert result['error'] is not None
print('  [感知与预测] OK')

# 测试3: 驱力评估
gaps = engine.evaluate_drives()
assert len(gaps) == 3
print('  [驱力评估] OK')

# 测试4: 整合决策
choices = fwfp.ChoiceSet(choice_id='test', options=['safe_option', 'fast_option'], context={})
decision_result = engine.make_consolidated_decision(choices)
assert decision_result['decision'] is not None
print('  [整合决策] OK')

# 测试5: 学习与进化
learn_result = engine.learn_and_evolve({
    'information_value': 0.8,
    'safe_improvement': 0.6,
    'gain_improvement': 0.5,
    'eff_improvement': 0.4,
})
assert learn_result['memory_stored'] is True
print('  [学习与进化] OK')

# 测试6: 完整整合循环
cycle_result = engine.run_integration_cycle({
    'available_actions': ['explore', 'exploit', 'wait'],
    'outcome': {'information_value': 0.7, 'safe_improvement': 0.55},
    'resources_used': {'cpu': 10.0},
    'output_value': 5.0,
})
assert cycle_result['cycle'] == 1
assert cycle_result['gaps'] == 3
print('  [完整整合循环] OK')

# 测试7: 完整统计
stats = engine.get_full_stats()
assert 'predictive_coding' in stats
assert 'drive' in stats
assert 'consciousness' in stats
assert 'free_will' in stats
print('  [完整统计] OK')

print('=' * 60)
print('阶段86-90验证通过')
print('=' * 60)
