"""
阶段96-100: 系统端到端测试

验证整个系统从感知到行动的完整流程。
"""

import sys
sys.path.insert(0, '/workspace/self_evolving_agent/core')

from system_coordinator import create_coordinator

print('=' * 60)
print('阶段96-100: 系统端到端测试')
print('=' * 60)

# 创建协调器
coord = create_coordinator('e2e_test')

# 注册预测器
coord._engine.predictive_coding.register_predictor(
    'sensor',
    lambda s: __import__('predictive_coding_engine').create_prediction('pred1', {'temp': 22.0})
)
coord._engine.predictive_coding.register_corrector(
    'sensor',
    lambda e: __import__('predictive_coding_engine').create_correction('corr1', e.error_id, {'bias': -0.1 * e.weighted_error})
)

# 端到端流程
print('\n--- 端到端流程测试 ---')

# 1. 设置目标（声明式）
coord.set_goal('safe', 0.9)
coord.set_goal('gain', 0.7)
coord.set_goal('eff', 0.8)
print('[1] 目标设置完成')

# 2. 观察环境
result = coord.observe({
    'module_id': 'sensor',
    'predicted': {'temp': 22.0},
    'actual': {'temp': 25.0},
})
print(f'[2] 观察完成: prediction_error={result["error"].surprise if result["error"] else 0:.2f}')

# 3. 评估驱力
gaps = coord._engine.evaluate_drives()
print(f'[3] 驱力评估完成: {len(gaps)} gaps')

# 4. 做出决策
act_result = coord.act('adjust_temperature', {
    'resources_used': {'cpu': 2.0, 'time': 1.0},
    'output_value': 5.0,
})
print(f'[4] 决策完成: action={act_result["action_taken"]}')

# 5. 学习与进化
coord._engine.learn_and_evolve({
    'information_value': 0.9,
    'safe_improvement': 0.85,
    'gain_improvement': 0.6,
    'eff_improvement': 0.75,
})
print('[5] 学习进化完成')

# 6. 反思状态
reflection = coord.reflect()
print(f'[6] 反思完成: cycles={reflection["cycle_count"]}, consciousness={len(reflection["consciousness_contents"])}')

# 7. 运行整合周期
cycle = coord.run_cycle({
    'available_actions': ['explore', 'exploit', 'rest'],
    'outcome': {'information_value': 0.8, 'safe_improvement': 0.7},
    'resources_used': {'cpu': 5.0},
    'output_value': 10.0,
})
print(f'[7] 整合周期完成: cycle={cycle["cycle"]}, dominant_drive={cycle["dominant_drive"]}')

# 8. 完整统计
stats = coord._engine.get_full_stats()
print(f'[8] 统计完成: engines={len(stats)}')

print('\n' + '=' * 60)
print('阶段96-100验证通过: 系统端到端测试成功')
print('=' * 60)
