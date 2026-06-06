## 第七卷：扩展深化与前沿探索

---

## 第五十一章：高级预测模型架构

### 51.1 世界模型（World Models）

世界模型是智能体对环境的内部模拟，能够预测未来状态并支持规划。

**核心组件**：

```python
class WorldModel:
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        self.state_dim = state_dim
        self.action_dim = action_dim

        # 视觉编码器（将高维观测压缩为低维状态）
        self.vision = VisionEncoder(state_dim, hidden_dim)

        # 记忆模型（RNN维护隐藏状态）
        self.memory = MemoryRNN(hidden_dim, hidden_dim)

        # 动态模型（预测下一状态）
        self.dynamics = DynamicsModel(hidden_dim, action_dim, hidden_dim)

        # 奖励模型（预测即时奖励）
        self.reward = RewardModel(hidden_dim, hidden_dim)

    def encode(self, observation):
        """将观测编码为状态表示"""
        return self.vision(observation)

    def step(self, state, action, hidden):
        """预测下一状态和奖励"""
        next_hidden = self.memory(state, action, hidden)
        next_state = self.dynamics(next_hidden)
        reward = self.reward(next_hidden)
        return next_state, reward, next_hidden

    def imagine(self, initial_state, initial_hidden, policy, horizon=50):
        """在想象中执行策略，生成轨迹"""
        states = [initial_state]
        rewards = []
        hidden = initial_hidden

        for _ in range(horizon):
            action = policy(states[-1])
            next_state, reward, hidden = self.step(states[-1], action, hidden)
            states.append(next_state)
            rewards.append(reward)

        return states, rewards
```

**训练策略**：

世界模型的训练分为两个阶段：

1. **监督学习阶段**：使用真实经验训练视觉编码器、记忆模型和动态模型
2. **强化学习阶段**：在想象的环境中训练策略

```python
def train_world_model(agent, env, epochs=1000):
    # 阶段1：收集经验并训练世界模型
    for epoch in range(epochs // 2):
        experience = collect_experience(agent, env)
        agent.world_model.train_on_experience(experience)

    # 阶段2：在想象中训练策略
    for epoch in range(epochs // 2):
        # 从真实经验中采样初始状态
        initial_state, initial_hidden = sample_initial_state(agent.memory)

        # 在想象中生成轨迹
        imagined_trajectory = agent.world_model.imagine(
            initial_state, initial_hidden, agent.policy
        )

        # 使用想象的轨迹训练策略
        agent.policy.train_on_imagined(imagined_trajectory)
```

### 51.2 因果推理模型

因果推理模型能够识别变量之间的因果关系，而不仅仅是相关性。

**因果图学习**：

```python
class CausalDiscovery:
    def __init__(self, variables):
        self.variables = variables
        self.causal_graph = nx.DiGraph()
        self.causal_graph.add_nodes_from(variables)

    def discover(self, data, method='pc'):
        if method == 'pc':
            return self.pc_algorithm(data)
        elif method == 'ges':
            return self.ges_algorithm(data)
        elif method == 'lingam':
            return self.lingam_algorithm(data)

    def pc_algorithm(self, data, alpha=0.05):
        """PC算法：基于条件独立性测试"""
        n = len(self.variables)

        # 步骤1：完全连接图
        graph = nx.complete_graph(self.variables)

        # 步骤2：基于条件独立性测试删除边
        for i in range(n):
            for j in range(i+1, n):
                var_i = self.variables[i]
                var_j = self.variables[j]

                # 测试无条件独立性
                if self.independence_test(data, var_i, var_j, [], alpha):
                    graph.remove_edge(var_i, var_j)
                    continue

                # 测试条件独立性
                for k in range(n):
                    if k != i and k != j:
                        cond = [self.variables[k]]
                        if self.independence_test(data, var_i, var_j, cond, alpha):
                            graph.remove_edge(var_i, var_j)
                            break

        # 步骤3：定向边
        self.orient_edges(graph, data)

        return graph

    def independence_test(self, data, x, y, cond, alpha):
        """条件独立性测试（使用偏相关）"""
        if not cond:
            corr, p_value = pearsonr(data[x], data[y])
        else:
            # 计算偏相关
            residuals_x = self.residuals(data[x], [data[c] for c in cond])
            residuals_y = self.residuals(data[y], [data[c] for c in cond])
            corr, p_value = pearsonr(residuals_x, residuals_y)

        return p_value > alpha

    def orient_edges(self, graph, data):
        """基于v-结构定向边"""
        for node in graph.nodes():
            neighbors = list(graph.neighbors(node))
            for i in range(len(neighbors)):
                for j in range(i+1, len(neighbors)):
                    # 检查v-结构
                    if not graph.has_edge(neighbors[i], neighbors[j]):
                        # 定向为 neighbors[i] -> node <- neighbors[j]
                        self.causal_graph.add_edge(neighbors[i], node)
                        self.causal_graph.add_edge(neighbors[j], node)
```

**因果效应估计**：

```python
class CausalEffectEstimator:
    def __init__(self, causal_graph):
        self.graph = causal_graph

    def estimate_ate(self, treatment, outcome, data, method='backdoor'):
        """估计平均处理效应（ATE）"""
        if method == 'backdoor':
            return self.backdoor_adjustment(treatment, outcome, data)
        elif method == 'frontdoor':
            return self.frontdoor_adjustment(treatment, outcome, data)
        elif method == 'iv':
            return self.instrumental_variable(treatment, outcome, data)

    def backdoor_adjustment(self, treatment, outcome, data):
        """后门调整"""
        # 找到满足后门准则的变量集
        adjustment_set = self.find_backdoor_set(treatment, outcome)

        # 计算调整后的因果效应
        if not adjustment_set:
            # 无混杂变量，直接比较
            treated = data[data[treatment] == 1][outcome].mean()
            control = data[data[treatment] == 0][outcome].mean()
            return treated - control

        # 分层计算
        effect = 0
        for stratum in self.get_strata(data, adjustment_set):
            treated = stratum[stratum[treatment] == 1][outcome].mean()
            control = stratum[stratum[treatment] == 0][outcome].mean()
            weight = len(stratum) / len(data)
            effect += weight * (treated - control)

        return effect

    def find_backdoor_set(self, treatment, outcome):
        """找到满足后门准则的调整变量集"""
        # 找到所有从treatment到outcome的后门路径
        backdoor_paths = self.find_backdoor_paths(treatment, outcome)

        # 找到能够阻断所有后门路径的变量集
        adjustment_set = set()
        for path in backdoor_paths:
            # 路径上的变量（不包括treatment和outcome）
            path_vars = path[1:-1]
            adjustment_set.update(path_vars)

        return adjustment_set
```

### 51.3 元学习模型

元学习（学习如何学习）使Agent能够快速适应新任务。

**模型无关元学习（MAML）**：

```python
class MAML:
    def __init__(self, model, meta_lr=0.001, inner_lr=0.01, inner_steps=5):
        self.model = model
        self.meta_lr = meta_lr
        self.inner_lr = inner_lr
        self.inner_steps = inner_steps
        self.meta_optimizer = torch.optim.Adam(model.parameters(), lr=meta_lr)

    def inner_loop(self, task_data):
        """在单个任务上进行内循环优化"""
        # 克隆模型参数
        fast_weights = [p.clone() for p in self.model.parameters()]

        # 内循环梯度下降
        for step in range(self.inner_steps):
            loss = self.compute_loss(self.model, task_data['train'], fast_weights)
            grads = torch.autograd.grad(loss, fast_weights, create_graph=True)
            fast_weights = [w - self.inner_lr * g for w, g in zip(fast_weights, grads)]

        return fast_weights

    def meta_step(self, batch_tasks):
        """元优化步骤"""
        meta_loss = 0

        for task in batch_tasks:
            # 内循环
            fast_weights = self.inner_loop(task)

            # 在测试集上评估
            test_loss = self.compute_loss(self.model, task['test'], fast_weights)
            meta_loss += test_loss

        # 元梯度下降
        self.meta_optimizer.zero_grad()
        meta_loss.backward()
        self.meta_optimizer.step()

        return meta_loss.item()

    def adapt(self, new_task_data):
        """快速适应新任务"""
        # 使用内循环进行快速适应
        adapted_weights = self.inner_loop(new_task_data)

        # 更新模型参数
        for p, w in zip(self.model.parameters(), adapted_weights):
            p.data = w.data
```

**基于记忆的元学习**：

```python
class MemoryAugmentedMetaLearning:
    def __init__(self, model, memory_size=128, memory_dim=64):
        self.model = model
        self.memory = Neural TuringMachine(memory_size, memory_dim)

    def forward(self, x, context):
        # 从记忆中读取相关信息
        memory_output = self.memory.read(context)

        # 结合输入和记忆信息
        combined = torch.cat([x, memory_output], dim=-1)

        # 生成预测
        prediction = self.model(combined)

        return prediction

    def update_memory(self, context, target):
        # 将新信息写入记忆
        self.memory.write(context, target)
```

---

## 第五十二章：高级驱力与动机系统

### 52.1 好奇心驱动的探索

**基于预测误差的好奇心**：

```python
class CuriosityDrive:
    def __init__(self, forward_model, inverse_model):
        self.forward_model = forward_model  # 预测下一状态
        self.inverse_model = inverse_model  # 预测动作

    def compute_intrinsic_reward(self, state, action, next_state):
        # 前向模型预测下一状态
        predicted_next = self.forward_model(state, action)

        # 预测误差作为内在奖励
        prediction_error = F.mse_loss(predicted_next, next_state)

        return prediction_error.item()
```

**基于信息增益的好奇心**：

```python
class InformationGainCuriosity:
    def __init__(self, ensemble_model):
        self.ensemble = ensemble_model  # 集成模型

    def compute_intrinsic_reward(self, state, action):
        # 获取集成模型的多个预测
        predictions = self.ensemble.predict_all(state, action)

        # 预测方差作为不确定性度量
        uncertainty = torch.var(predictions, dim=0).mean()

        return uncertainty.item()
```

**基于状态新颖性的好奇心**：

```python
class NoveltySeeking:
    def __init__(self, state_encoder, density_model):
        self.encoder = state_encoder
        self.density = density_model  # 状态密度模型

    def compute_intrinsic_reward(self, state):
        # 编码状态
        encoded = self.encoder(state)

        # 计算状态密度
        density = self.density.probability(encoded)

        # 密度越低（越新颖），奖励越高
        novelty = -torch.log(density + 1e-8)

        # 更新密度模型
        self.density.update(encoded)

        return novelty.item()
```

### 52.2 社会驱力

**模仿学习**：

```python
class ImitationDrive:
    def __init__(self, expert_policy):
        self.expert = expert_policy
        self.imitation_model = None

    def compute_reward(self, state, action):
        # 专家动作
        expert_action = self.expert(state)

        # 模仿误差
        imitation_error = F.mse_loss(action, expert_action)

        return -imitation_error.item()

    def learn_from_expert(self, expert_trajectories):
        # 训练模仿模型
        self.imitation_model = BehavioralCloning()
        self.imitation_model.train(expert_trajectories)
```

**竞争驱力**：

```python
class CompetitiveDrive:
    def __init__(self, opponent):
        self.opponent = opponent
        self.win_count = 0
        self.total_games = 0

    def compute_reward(self, outcome):
        self.total_games += 1

        if outcome == 'win':
            self.win_count += 1
            return 1.0
        elif outcome == 'draw':
            return 0.0
        else:
            return -1.0

    def get_win_rate(self):
        return self.win_count / max(self.total_games, 1)
```

**合作驱力**：

```python
class CooperativeDrive:
    def __init__(self, teammates):
        self.teammates = teammates
        self.shared_goals = []

    def compute_reward(self, team_outcome, individual_contribution):
        # 团队成果
        team_reward = team_outcome

        # 个人贡献
        contribution_reward = individual_contribution

        # 合作奖励 = 团队奖励 + 个人贡献
        return 0.7 * team_reward + 0.3 * contribution_reward
```

### 52.3 创造驱力

**新颖性生成**：

```python
class CreativityDrive:
    def __init__(self, generator, discriminator):
        self.generator = generator
        self.discriminator = discriminator

    def compute_reward(self, generated_output):
        # 判别器评分（新颖性）
        novelty = self.discriminator(generated_output)

        # 质量评分
        quality = self.evaluate_quality(generated_output)

        # 创造性奖励 = 新颖性 * 质量
        return novelty * quality

    def evaluate_quality(self, output):
        # 基于任务特定标准评估质量
        pass
```

**组合创新**：

```python
class CombinatorialCreativity:
    def __init__(self, concept_space):
        self.concepts = concept_space
        self.combinations = []

    def generate_novel_combination(self):
        # 随机选择两个概念
        concept_a = random.choice(self.concepts)
        concept_b = random.choice(self.concepts)

        # 组合概念
        combination = self.combine(concept_a, concept_b)

        # 检查新颖性
        if self.is_novel(combination):
            self.combinations.append(combination)
            return combination

        return None

    def combine(self, a, b):
        # 概念组合操作
        return {
            'components': [a, b],
            'features': a['features'] + b['features'],
            'relations': self.infer_relations(a, b)
        }
```

---

## 第五十三章：高级学习算法

### 53.1 持续学习

**弹性权重巩固（EWC）**：

```python
class EWC:
    def __init__(self, model, lambda_ewc=1000):
        self.model = model
        self.lambda_ewc = lambda_ewc
        self.fisher_dict = {}  # Fisher信息矩阵
        self.optimal_params = {}  # 最优参数

    def compute_fisher(self, dataloader):
        """计算Fisher信息矩阵"""
        fisher = {n: torch.zeros_like(p) for n, p in self.model.named_parameters()}

        for batch in dataloader:
            self.model.zero_grad()
            output = self.model(batch)
            loss = F.nll_loss(output, batch.target)
            loss.backward()

            for n, p in self.model.named_parameters():
                if p.grad is not None:
                    fisher[n] += p.grad.pow(2) / len(dataloader)

        return fisher

    def update_ewc_params(self, task_id, dataloader):
        """更新EWC参数"""
        self.fisher_dict[task_id] = self.compute_fisher(dataloader)
        self.optimal_params[task_id] = {
            n: p.clone().detach() for n, p in self.model.named_parameters()
        }

    def penalty(self):
        """计算EWC惩罚项"""
        loss = 0
        for task_id in self.fisher_dict:
            for n, p in self.model.named_parameters():
                if n in self.fisher_dict[task_id]:
                    fisher = self.fisher_dict[task_id][n]
                    optimal = self.optimal_params[task_id][n]
                    loss += (fisher * (p - optimal).pow(2)).sum()

        return self.lambda_ewc * loss

    def train(self, dataloader, task_id):
        for batch in dataloader:
            self.model.zero_grad()
            output = self.model(batch)
            loss = F.nll_loss(output, batch.target) + self.penalty()
            loss.backward()
            self.optimizer.step()
```

**渐进神经网络**：

```python
class ProgressiveNeuralNetwork:
    def __init__(self, input_size, output_size, hidden_size=256):
        self.columns = []
        self.input_size = input_size
        self.output_size = output_size
        self.hidden_size = hidden_size

    def add_column(self, task_id):
        """为新任务添加新列"""
        column = nn.ModuleDict({
            'h': nn.Linear(self.input_size, self.hidden_size),
            'out': nn.Linear(self.hidden_size, self.output_size)
        })

        # 添加横向连接
        for prev_column in self.columns:
            lateral = nn.Linear(self.hidden_size, self.hidden_size)
            column[f'lateral_{len(self.columns)}'] = lateral

        self.columns.append(column)

    def forward(self, x, task_id):
        """前向传播，使用所有列"""
        column = self.columns[task_id]

        # 基础隐藏状态
        h = F.relu(column['h'](x))

        # 添加横向连接
        for i, prev_column in enumerate(self.columns[:task_id]):
            prev_h = F.relu(prev_column['h'](x))
            lateral = column[f'lateral_{i}'](prev_h)
            h = h + lateral

        # 输出
        output = column['out'](h)
        return output
```

### 53.2 分层强化学习

**选项框架（Options Framework）**：

```python
class Option:
    def __init__(self, initiation_set, policy, termination_condition):
        self.initiation_set = initiation_set  # 可启动该选项的状态集
        self.policy = policy  # 选项内部策略
        self.termination = termination_condition  # 终止条件

    def can_initiate(self, state):
        return state in self.initiation_set

    def execute(self, env, state):
        """执行选项直到终止"""
        trajectory = []
        current_state = state

        while not self.termination(current_state):
            action = self.policy(current_state)
            next_state, reward, done, _ = env.step(action)
            trajectory.append((current_state, action, reward))
            current_state = next_state

            if done:
                break

        return trajectory, current_state

class HierarchicalRL:
    def __init__(self, primitive_actions, options):
        self.primitive_actions = primitive_actions
        self.options = options
        self.meta_policy = None  # 高层策略（选择选项或原始动作）

    def select_action(self, state):
        # 高层决策：选择选项或原始动作
        available_options = [o for o in self.options if o.can_initiate(state)]
        all_choices = self.primitive_actions + available_options

        return self.meta_policy(state, all_choices)

    def train(self, env, episodes):
        for episode in episodes:
            state = env.reset()
            done = False

            while not done:
                choice = self.select_action(state)

                if isinstance(choice, Option):
                    # 执行选项
                    trajectory, state = choice.execute(env, state)
                    # 使用选项内部的经验训练选项策略
                    choice.policy.train(trajectory)
                else:
                    # 执行原始动作
                    next_state, reward, done, _ = env.step(choice)
                    state = next_state
```

**封建制强化学习**：

```python
class FeudalRL:
    def __init__(self, state_dim, n_managers, n_workers):
        self.managers = [Manager(state_dim) for _ in range(n_managers)]
        self.workers = [Worker(state_dim) for _ in range(n_workers)]

    def act(self, state):
        # 管理者设定目标
        goals = [manager.set_goal(state) for manager in self.managers]

        # 工作者执行动作以实现目标
        actions = []
        for worker, goal in zip(self.workers, goals):
            action = worker.act(state, goal)
            actions.append(action)

        return actions

class Manager:
    def __init__(self, state_dim, goal_dim=16):
        self.goal_network = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, goal_dim)
        )
        self.goal_period = 10  # 目标持续时间

    def set_goal(self, state):
        goal = self.goal_network(state)
        return goal

class Worker:
    def __init__(self, state_dim, action_dim, goal_dim=16):
        self.policy = nn.Sequential(
            nn.Linear(state_dim + goal_dim, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )

    def act(self, state, goal):
        x = torch.cat([state, goal], dim=-1)
        action_probs = F.softmax(self.policy(x), dim=-1)
        action = torch.multinomial(action_probs, 1)
        return action
```

### 53.3 离线强化学习

**保守Q学习（CQL）**：

```python
class CQL:
    def __init__(self, q_network, policy, alpha=1.0):
        self.q_network = q_network
        self.policy = policy
        self.alpha = alpha

    def cql_loss(self, q_values, dataset_q_values):
        """CQL正则化项"""
        # 数据集Q值
        dataset_q = dataset_q_values.mean()

        # 所有动作的Q值（logsumexp）
        all_q = torch.logsumexp(q_values, dim=-1).mean()

        # CQL损失：鼓励数据集动作的Q值高，其他动作的Q值低
        cql_loss = all_q - dataset_q

        return cql_loss

    def train(self, dataset, batch_size=256):
        for batch in DataLoader(dataset, batch_size=batch_size):
            state, action, reward, next_state, done = batch

            # 标准贝尔曼误差
            q_values = self.q_network(state)
            q_value = q_values.gather(1, action.unsqueeze(1)).squeeze(1)

            with torch.no_grad():
                next_q = self.q_network(next_state).max(1)[0]
                target_q = reward + 0.99 * next_q * (1 - done)

            bellman_loss = F.mse_loss(q_value, target_q)

            # CQL正则化
            cql_loss = self.cql_loss(q_values, q_value)

            # 总损失
            total_loss = bellman_loss + self.alpha * cql_loss

            # 优化
            self.q_optimizer.zero_grad()
            total_loss.backward()
            self.q_optimizer.step()
```

---

## 第五十四章：神经符号集成

### 54.1 可微分逻辑

**逻辑神经网络**：

```python
class LogicNN:
    def __init__(self, predicates, rules):
        self.predicates = predicates
        self.rules = rules

        # 为每个规则学习权重
        self.rule_weights = nn.Parameter(torch.ones(len(rules)))

    def forward(self, facts):
        """前向推理"""
        # 初始化已知事实
        beliefs = facts.clone()

        # 迭代应用规则
        for iteration in range(10):
            new_beliefs = beliefs.clone()

            for i, rule in enumerate(self.rules):
                # 计算规则触发度
                trigger = self.evaluate_rule(rule, beliefs)

                # 加权更新
                weight = torch.sigmoid(self.rule_weights[i])
                conclusion = rule.conclusion
                new_beliefs[conclusion] += weight * trigger

            # 收敛检查
            if torch.allclose(beliefs, new_beliefs, atol=1e-6):
                break

            beliefs = new_beliefs

        return torch.sigmoid(beliefs)

    def evaluate_rule(self, rule, beliefs):
        """评估规则的触发程度"""
        if rule.type == 'AND':
            return torch.min(beliefs[rule.premises])
        elif rule.type == 'OR':
            return torch.max(beliefs[rule.premises])
        elif rule.type == 'NOT':
            return 1 - beliefs[rule.premises[0]]
```

**神经定理证明**：

```python
class NeuralTheoremProver:
    def __init__(self, knowledge_base):
        self.kb = knowledge_base
        self.unification_net = UnificationNetwork()
        self.proof_policy = ProofPolicyNetwork()

    def prove(self, goal, max_depth=10):
        """尝试证明目标"""
        proof_state = ProofState(goal)
        proof_trace = []

        for step in range(max_depth):
            # 选择下一个证明步骤
            action = self.proof_policy.select_action(proof_state)

            if action.type == 'unify':
                # 尝试与知识库中的事实统一
                success, substitution = self.unification_net.unify(
                    proof_state.current_goal,
                    action.target
                )

                if success:
                    proof_state.apply_substitution(substitution)
                    proof_trace.append(('unify', action.target, substitution))
                else:
                    proof_trace.append(('fail', action.target))

            elif action.type == 'resolve':
                # 使用规则进行归结
                new_goals = self.resolve(proof_state.current_goal, action.rule)
                proof_state.push_goals(new_goals)
                proof_trace.append(('resolve', action.rule, new_goals))

            elif action.type == 'success':
                return True, proof_trace

            if proof_state.is_empty():
                return True, proof_trace

        return False, proof_trace
```

### 54.2 神经程序合成

**可微分编程**：

```python
class DifferentiableProgram:
    def __init__(self, operations, controller):
        self.operations = operations  # 可微分操作库
        self.controller = controller  # 控制器（选择操作和参数）

    def execute(self, input_data, program_length=10):
        """执行程序"""
        state = input_data
        trace = []

        for step in range(program_length):
            # 控制器选择操作
            op_logits, arg_logits = self.controller(state)
            op_probs = F.softmax(op_logits, dim=-1)
            arg_probs = F.softmax(arg_logits, dim=-1)

            # 软选择操作（可微分）
            op_embedding = torch.matmul(op_probs, self.operation_embeddings)
            arg_embedding = torch.matmul(arg_probs, self.argument_embeddings)

            # 执行操作（可微分近似）
            next_state = self.soft_execute(state, op_embedding, arg_embedding)

            trace.append({
                'op_probs': op_probs,
                'arg_probs': arg_probs,
                'state': next_state
            })

            state = next_state

        return state, trace

    def soft_execute(self, state, op_embedding, arg_embedding):
        """软执行操作（可微分）"""
        # 对所有操作进行加权求和
        result = torch.zeros_like(state)
        for i, op in enumerate(self.operations):
            weight = op_embedding[i]
            op_result = op(state, arg_embedding)
            result += weight * op_result

        return result
```

---

## 第五十五章：量子计算与AI

### 55.1 量子机器学习

**量子神经网络**：

```python
class QuantumNeuralNetwork:
    def __init__(self, n_qubits, n_layers):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.dev = qml.device('default.qubit', wires=n_qubits)

    def build_circuit(self):
        @qml.qnode(self.dev)
        def circuit(inputs, weights):
            # 编码输入
            for i in range(self.n_qubits):
                qml.RY(inputs[i], wires=i)

            # 变分层
            for layer in range(self.n_layers):
                for i in range(self.n_qubits):
                    qml.RX(weights[layer, i, 0], wires=i)
                    qml.RZ(weights[layer, i, 1], wires=i)

                # 纠缠层
                for i in range(self.n_qubits - 1):
                    qml.CNOT(wires=[i, i+1])

            # 测量
            return [qml.expval(qml.PauliZ(i)) for i in range(self.n_qubits)]

        return circuit

    def train(self, X, y, epochs=100):
        circuit = self.build_circuit()
        weights = np.random.randn(self.n_layers, self.n_qubits, 2)
        opt = qml.GradientDescentOptimizer(stepsize=0.01)

        for epoch in range(epochs):
            def cost(w):
                predictions = np.array([circuit(x, w) for x in X])
                return np.mean((predictions - y) ** 2)

            weights = opt.step(cost, weights)

        return weights
```

**量子强化学习**：

```python
class QuantumRL:
    def __init__(self, n_states, n_actions, n_qubits):
        self.n_states = n_states
        self.n_actions = n_actions
        self.n_qubits = n_qubits
        self.dev = qml.device('default.qubit', wires=n_qubits)

    def build_q_value_circuit(self):
        @qml.qnode(self.dev)
        def q_value_circuit(state, weights):
            # 状态编码
            for i in range(min(len(state), self.n_qubits)):
                qml.RY(state[i] * np.pi, wires=i)

            # 变分电路
            for layer in range(len(weights)):
                for i in range(self.n_qubits):
                    qml.RX(weights[layer][i][0], wires=i)
                    qml.RZ(weights[layer][i][1], wires=i)
                for i in range(self.n_qubits - 1):
                    qml.CNOT(wires=[i, i+1])

            # 测量动作价值
            return [qml.expval(qml.PauliZ(i)) for i in range(self.n_actions)]

        return q_value_circuit
```

---

## 第五十六章：生物启发计算

### 56.1 神经形态计算

**脉冲神经网络（SNN）**：

```python
class SpikingNeuron:
    def __init__(self, tau_mem=20e-3, tau_syn=5e-3, v_thresh=1.0, v_reset=0.0):
        self.tau_mem = tau_mem  # 膜时间常数
        self.tau_syn = tau_syn  # 突触时间常数
        self.v_thresh = v_thresh  # 阈值电压
        self.v_reset = v_reset  # 重置电压

        self.v = v_reset  # 膜电位
        self.i = 0.0  # 突触电流

    def update(self, dt, input_current):
        # 更新突触电流
        di = -self.i / self.tau_syn + input_current
        self.i += di * dt

        # 更新膜电位
        dv = (-self.v + self.i) / self.tau_mem
        self.v += dv * dt

        # 检查是否发放脉冲
        spike = self.v >= self.v_thresh
        if spike:
            self.v = self.v_reset

        return spike

class SpikingNeuralNetwork:
    def __init__(self, layers):
        self.layers = []
        for i in range(len(layers) - 1):
            layer = [[SpikingNeuron() for _ in range(layers[i+1])]
                     for _ in range(layers[i])]
            self.layers.append(layer)

    def forward(self, spike_train, T=100):
        """前向传播"""
        dt = 1e-3  # 1ms时间步
        spikes = spike_train

        for layer in self.layers:
            output_spikes = []
            for t in range(T):
                # 计算突触输入
                synaptic_input = self.compute_synaptic_input(spikes, layer)

                # 更新神经元
                layer_spikes = []
                for neuron in layer:
                    spike = neuron.update(dt, synaptic_input)
                    layer_spikes.append(spike)

                output_spikes.append(layer_spikes)

            spikes = output_spikes

        return spikes
```

### 56.2 群体智能

**粒子群优化（PSO）**：

```python
class ParticleSwarmOptimization:
    def __init__(self, n_particles, dim, w=0.7, c1=1.5, c2=1.5):
        self.n_particles = n_particles
        self.dim = dim
        self.w = w  # 惯性权重
        self.c1 = c1  # 认知系数
        self.c2 = c2  # 社会系数

        # 初始化粒子
        self.positions = np.random.randn(n_particles, dim)
        self.velocities = np.random.randn(n_particles, dim) * 0.1

        # 个体最优
        self.pbest = self.positions.copy()
        self.pbest_fitness = np.full(n_particles, float('inf'))

        # 全局最优
        self.gbest = None
        self.gbest_fitness = float('inf')

    def optimize(self, fitness_func, max_iter=100):
        for iteration in range(max_iter):
            # 评估适应度
            fitness = np.array([fitness_func(p) for p in self.positions])

            # 更新个体最优
            improved = fitness < self.pbest_fitness
            self.pbest[improved] = self.positions[improved]
            self.pbest_fitness[improved] = fitness[improved]

            # 更新全局最优
            best_idx = np.argmin(fitness)
            if fitness[best_idx] < self.gbest_fitness:
                self.gbest = self.positions[best_idx].copy()
                self.gbest_fitness = fitness[best_idx]

            # 更新速度和位置
            r1, r2 = np.random.rand(2)
            self.velocities = (
                self.w * self.velocities
                + self.c1 * r1 * (self.pbest - self.positions)
                + self.c2 * r2 * (self.gbest - self.positions)
            )
            self.positions += self.velocities

            print(f"Iteration {iteration}: Best fitness = {self.gbest_fitness}")

        return self.gbest, self.gbest_fitness
```

**蚁群优化（ACO）**：

```python
class AntColonyOptimization:
    def __init__(self, n_ants, n_nodes, alpha=1.0, beta=2.0, rho=0.5):
        self.n_ants = n_ants
        self.n_nodes = n_nodes
        self.alpha = alpha  # 信息素重要性
        self.beta = beta  # 启发式信息重要性
        self.rho = rho  # 信息素蒸发率

        # 初始化信息素
        self.pheromone = np.ones((n_nodes, n_nodes))

    def solve_tsp(self, distance_matrix, max_iter=100):
        best_tour = None
        best_length = float('inf')

        for iteration in range(max_iter):
            all_tours = []
            all_lengths = []

            for ant in range(self.n_ants):
                tour = self.construct_tour(distance_matrix)
                length = self.tour_length(tour, distance_matrix)
                all_tours.append(tour)
                all_lengths.append(length)

                if length < best_length:
                    best_length = length
                    best_tour = tour

            # 更新信息素
            self.update_pheromone(all_tours, all_lengths)

            print(f"Iteration {iteration}: Best length = {best_length}")

        return best_tour, best_length

    def construct_tour(self, distance_matrix):
        tour = [np.random.randint(self.n_nodes)]
        unvisited = set(range(self.n_nodes)) - {tour[0]}

        while unvisited:
            current = tour[-1]
            probabilities = []

            for node in unvisited:
                tau = self.pheromone[current][node] ** self.alpha
                eta = (1.0 / distance_matrix[current][node]) ** self.beta
                probabilities.append(tau * eta)

            probabilities = np.array(probabilities)
            probabilities /= probabilities.sum()

            next_node = np.random.choice(list(unvisited), p=probabilities)
            tour.append(next_node)
            unvisited.remove(next_node)

        return tour

    def update_pheromone(self, tours, lengths):
        # 信息素蒸发
        self.pheromone *= (1 - self.rho)

        # 信息素沉积
        for tour, length in zip(tours, lengths):
            deposit = 1.0 / length
            for i in range(len(tour)):
                j = (i + 1) % len(tour)
                self.pheromone[tour[i]][tour[j]] += deposit
```

---

## 第五十七章：伦理与治理

### 57.1 AI伦理框架

**公平性评估**：

```python
class FairnessEvaluator:
    def __init__(self, predictions, labels, protected_attributes):
        self.predictions = predictions
        self.labels = labels
        self.protected = protected_attributes

    def demographic_parity(self):
        """人口统计均等"""
        groups = np.unique(self.protected)
        rates = []

        for group in groups:
            mask = self.protected == group
            rate = self.predictions[mask].mean()
            rates.append(rate)

        return max(rates) - min(rates)

    def equal_opportunity(self):
        """机会均等"""
        groups = np.unique(self.protected)
        tprs = []

        for group in groups:
            mask = (self.protected == group) & (self.labels == 1)
            if mask.sum() > 0:
                tpr = self.predictions[mask].mean()
                tprs.append(tpr)

        return max(tprs) - min(tprs)

    def calibration(self):
        """校准性"""
        groups = np.unique(self.protected)
        calibration_scores = []

        for group in groups:
            mask = self.protected == group
            pred_probs = self.predictions[mask]
            true_labels = self.labels[mask]

            # 按预测概率分桶
            bins = np.linspace(0, 1, 11)
            for i in range(len(bins) - 1):
                bin_mask = (pred_probs >= bins[i]) & (pred_probs < bins[i+1])
                if bin_mask.sum() > 0:
                    avg_pred = pred_probs[bin_mask].mean()
                    avg_true = true_labels[bin_mask].mean()
                    calibration_scores.append(abs(avg_pred - avg_true))

        return np.mean(calibration_scores)
```

**可解释性方法**：

```python
class Explainability:
    def __init__(self, model):
        self.model = model

    def lime_explanation(self, instance, num_features=10):
        """LIME局部解释"""
        # 在实例附近采样
        samples = self.perturb_instance(instance)

        # 获取预测
        predictions = self.model.predict(samples)

        # 训练局部线性模型
        weights = self.compute_weights(instance, samples)
        local_model = Ridge(alpha=1.0)
        local_model.fit(samples, predictions, sample_weight=weights)

        # 获取最重要的特征
        feature_importance = np.argsort(np.abs(local_model.coef_))[-num_features:]

        return feature_importance, local_model.coef_[feature_importance]

    def shap_explanation(self, instance, background_data):
        """SHAP值解释"""
        explainer = shap.KernelExplainer(self.model.predict, background_data)
        shap_values = explainer.shap_values(instance)

        return shap_values

    def attention_visualization(self, input_data):
        """注意力权重可视化"""
        attention_weights = self.model.get_attention_weights(input_data)

        # 可视化注意力热力图
        plt.figure(figsize=(10, 8))
        sns.heatmap(attention_weights, cmap='viridis')
        plt.title('Attention Weights')
        plt.show()

        return attention_weights
```

### 57.2 治理机制

**价值对齐**：

```python
class ValueAlignment:
    def __init__(self, human_values):
        self.human_values = human_values
        self.value_model = self.build_value_model()

    def build_value_model(self):
        """构建人类价值模型"""
        # 从人类反馈中学习价值函数
        model = nn.Sequential(
            nn.Linear(self.state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, len(self.human_values))
        )
        return model

    def human_preference_learning(self, comparisons):
        """从人类比较中学习"""
        optimizer = torch.optim.Adam(self.value_model.parameters())

        for comparison in comparisons:
            trajectory_a = comparison['trajectory_a']
            trajectory_b = comparison['trajectory_b']
            preference = comparison['preference']  # 0: a preferred, 1: b preferred, 0.5: tie

            # 计算价值
            value_a = self.value_model(trajectory_a).sum()
            value_b = self.value_model(trajectory_b).sum()

            # Bradley-Terry模型
            prob_b_preferred = torch.sigmoid(value_b - value_a)

            # 损失
            if preference == 0.5:
                loss = -torch.log(1 - prob_b_preferred + 1e-8) * 0.5 - torch.log(prob_b_preferred + 1e-8) * 0.5
            else:
                loss = -torch.log(prob_b_preferred + 1e-8) if preference == 1 else -torch.log(1 - prob_b_preferred + 1e-8)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    def evaluate_alignment(self, policy):
        """评估策略与人类价值的一致性"""
        trajectories = policy.generate_trajectories(100)
        values = [self.value_model(t).mean().item() for t in trajectories]
        return np.mean(values)
```

---

## 第五十八章：未来展望

### 58.1 通用人工智能路径

**认知架构演进**：

1. **感知智能**（当前）：识别模式、预测趋势
2. **认知智能**（近期）：理解因果、进行推理
3. **自主智能**（中期）：自主决策、持续学习
4. **通用智能**（远期）：跨领域迁移、创造性解决

**关键里程碑**：

- 2026-2028：自驱Agent在特定领域达到专家水平
- 2028-2030：跨领域迁移学习实现突破
- 2030-2035：通用问题解决能力接近人类
- 2035+：超人类智能出现

### 58.2 技术融合趋势

**脑机接口**：
- 直接读取大脑信号
- 双向信息传输
- 认知增强

**量子计算**：
- 指数级计算加速
- 新型算法可能
- 密码学影响

**生物技术**：
- 生物计算
- DNA存储
- 神经工程

### 58.3 社会影响

**积极影响**：
- 自动化复杂决策
- 加速科学发现
- 个性化教育
- 医疗诊断提升

**挑战与风险**：
- 就业结构变化
- 隐私与安全
- 算法偏见
- 控制与对齐

**治理建议**：
- 建立国际AI治理框架
- 推动透明可解释AI
- 确保价值对齐
- 促进普惠发展

---

**文档结束**

