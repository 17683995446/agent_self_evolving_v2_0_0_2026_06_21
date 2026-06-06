## 第九卷：深度理论扩展与数学基础

---

## 第七十一章：信息论基础

### 71.1 熵与信息

**香农熵**：

信息论的核心概念是熵，它量化了随机变量的不确定性。

$$H(X) = -\sum_{i} P(x_i) \log P(x_i)$$

熵的性质：
- $H(X) \geq 0$，当且仅当某个事件概率为1时等号成立
- $H(X) \leq \log |X|$，当且仅当均匀分布时等号成立
- 熵是凹函数

**联合熵与条件熵**：

$$H(X, Y) = -\sum_{x,y} P(x,y) \log P(x,y)$$

$$H(Y|X) = -\sum_{x,y} P(x,y) \log P(y|x)$$

**互信息**：

$$I(X;Y) = H(X) - H(X|Y) = H(Y) - H(Y|X)$$

互信息衡量了两个变量之间的依赖程度：
- $I(X;Y) \geq 0$
- $I(X;Y) = 0$ 当且仅当 $X$ 和 $Y$ 独立
- $I(X;Y) = I(Y;X)$

**相对熵（KL散度）**：

$$D_{KL}[P||Q] = \sum_{i} P(x_i) \log \frac{P(x_i)}{Q(x_i)}$$

KL散度的性质：
- $D_{KL}[P||Q] \geq 0$，当且仅当 $P=Q$ 时等号成立
- 不对称：$D_{KL}[P||Q] \neq D_{KL}[Q||P]$
- 不满足三角不等式

### 71.2 信息论与机器学习

**最大熵原理**：

在已知约束条件下，选择熵最大的分布：

$$\max_P H(P) \quad \text{s.t.} \quad \mathbb{E}_P[f_i(x)] = \bar{f}_i$$

解为指数族分布：

$$P(x) = \frac{1}{Z} \exp\left(\sum_i \lambda_i f_i(x)\right)$$

**最小描述长度（MDL）**：

$$L(D, M) = L(D|M) + L(M)$$

其中：
- $L(D|M)$：给定模型时数据的编码长度
- $L(M)$：模型的编码长度

**信息瓶颈理论**：

$$\min_{p(t|x)} I(X;T) - \beta I(T;Y)$$

目标是在保留关于$Y$的信息的同时，压缩$X$的信息。

### 71.3 信息论在Agent系统中的应用

**信息驱动的探索**：

```python
class InformationDrivenExploration:
    def __init__(self, model):
        self.model = model

    def compute_information_gain(self, state, action):
        """计算执行动作后的信息增益"""
        # 当前不确定性
        current_entropy = self.compute_entropy(state)

        # 执行动作后的预期不确定性
        next_states = self.model.predict_next_states(state, action)
        expected_entropy = 0
        for next_state, prob in next_states:
            entropy = self.compute_entropy(next_state)
            expected_entropy += prob * entropy

        # 信息增益
        information_gain = current_entropy - expected_entropy

        return information_gain

    def select_action(self, state, actions):
        """选择信息增益最大的动作"""
        best_action = None
        best_gain = -float('inf')

        for action in actions:
            gain = self.compute_information_gain(state, action)
            if gain > best_gain:
                best_gain = gain
                best_action = action

        return best_action
```

---

## 第七十二章：概率图模型

### 72.1 贝叶斯网络

**定义**：

贝叶斯网络是有向无环图，节点表示随机变量，边表示条件依赖关系。

联合概率分布：

$$P(X_1, X_2, ..., X_n) = \prod_{i=1}^{n} P(X_i | Pa(X_i))$$

其中$Pa(X_i)$是$X_i$的父节点。

**推断**：

```python
class BayesianNetwork:
    def __init__(self, structure, cpts):
        self.structure = structure  # 网络结构
        self.cpts = cpts  # 条件概率表

    def variable_elimination(self, query_vars, evidence):
        """变量消去算法"""
        # 初始化因子
        factors = []
        for node in self.structure.nodes():
            factor = self.cpts[node]
            if node in evidence:
                factor = self.condition(factor, node, evidence[node])
            factors.append(factor)

        # 消去非查询变量
        elim_order = self.get_elimination_order(query_vars, evidence)

        for var in elim_order:
            # 收集包含该变量的因子
            relevant_factors = [f for f in factors if var in f.variables]
            other_factors = [f for f in factors if var not in f.variables]

            # 乘积并求和消去
            product = self.multiply_factors(relevant_factors)
            eliminated = self.sum_out(product, var)

            factors = other_factors + [eliminated]

        # 归一化
        result = self.multiply_factors(factors)
        result = self.normalize(result)

        return result

    def get_elimination_order(self, query_vars, evidence):
        """获取消去顺序（最小填充启发式）"""
        remaining = set(self.structure.nodes()) - set(query_vars) - set(evidence.keys())
        order = []

        while remaining:
            # 选择消去后引入最少填充边的变量
            best_var = min(remaining, key=lambda v: self.fill_edges(v, remaining))
            order.append(best_var)
            remaining.remove(best_var)

        return order
```

### 72.2 马尔可夫随机场

**定义**：

马尔可夫随机场是无向图模型，联合概率由势函数定义：

$$P(X) = \frac{1}{Z} \prod_{c \in C} \psi_c(X_c)$$

其中$C$是最大团集合，$\psi_c$是团势函数，$Z$是归一化常数。

**推断算法**：

```python
class MarkovRandomField:
    def __init__(self, graph, potentials):
        self.graph = graph
        self.potentials = potentials

    def belief_propagation(self, max_iter=100):
        """置信传播算法"""
        # 初始化消息
        messages = {}
        for edge in self.graph.edges():
            messages[edge] = np.ones(self.graph.get_state_size(edge[1]))

        for iteration in range(max_iter):
            new_messages = {}

            for edge in self.graph.edges():
                i, j = edge

                # 计算从i到j的消息
                message = self.compute_message(i, j, messages)
                new_messages[edge] = message

            # 检查收敛
            if self.messages_converged(messages, new_messages):
                break

            messages = new_messages

        # 计算边缘分布
        beliefs = {}
        for node in self.graph.nodes():
            belief = self.compute_belief(node, messages)
            beliefs[node] = belief

        return beliefs

    def compute_message(self, i, j, messages):
        """计算消息"""
        # 收集来自i的其他邻居的消息
        incoming = []
        for neighbor in self.graph.neighbors(i):
            if neighbor != j:
                incoming.append(messages[(neighbor, i)])

        # 计算消息
        message = self.potentials[i].copy()
        for msg in incoming:
            message *= msg

        # 对i求和
        message = np.sum(message, axis=i)

        # 归一化
        message /= np.sum(message)

        return message
```

### 72.3 隐马尔可夫模型

```python
class HiddenMarkovModel:
    def __init__(self, n_states, n_observations):
        self.n_states = n_states
        self.n_observations = n_observations

        # 初始化参数
        self.pi = np.ones(n_states) / n_states  # 初始状态分布
        self.A = np.ones((n_states, n_states)) / n_states  # 转移矩阵
        self.B = np.ones((n_states, n_observations)) / n_observations  # 观测矩阵

    def forward(self, observations):
        """前向算法"""
        T = len(observations)
        alpha = np.zeros((T, self.n_states))

        # 初始化
        alpha[0] = self.pi * self.B[:, observations[0]]

        # 递推
        for t in range(1, T):
            alpha[t] = self.B[:, observations[t]] * (alpha[t-1] @ self.A)

        return alpha

    def backward(self, observations):
        """后向算法"""
        T = len(observations)
        beta = np.zeros((T, self.n_states))

        # 初始化
        beta[T-1] = 1

        # 递推
        for t in range(T-2, -1, -1):
            beta[t] = (self.A * self.B[:, observations[t+1]]) @ beta[t+1]

        return beta

    def viterbi(self, observations):
        """维特比算法"""
        T = len(observations)
        delta = np.zeros((T, self.n_states))
        psi = np.zeros((T, self.n_states), dtype=int)

        # 初始化
        delta[0] = self.pi * self.B[:, observations[0]]

        # 递推
        for t in range(1, T):
            for j in range(self.n_states):
                delta[t, j] = np.max(delta[t-1] * self.A[:, j]) * self.B[j, observations[t]]
                psi[t, j] = np.argmax(delta[t-1] * self.A[:, j])

        # 回溯
        path = np.zeros(T, dtype=int)
        path[T-1] = np.argmax(delta[T-1])

        for t in range(T-2, -1, -1):
            path[t] = psi[t+1, path[t+1]]

        return path, np.max(delta[T-1])

    def baum_welch(self, observations, max_iter=100):
        """Baum-Welch算法（EM）"""
        for iteration in range(max_iter):
            alpha = self.forward(observations)
            beta = self.backward(observations)

            # 计算gamma和xi
            gamma = alpha * beta
            gamma /= np.sum(gamma, axis=1, keepdims=True)

            xi = np.zeros((len(observations)-1, self.n_states, self.n_states))
            for t in range(len(observations)-1):
                for i in range(self.n_states):
                    for j in range(self.n_states):
                        xi[t, i, j] = alpha[t, i] * self.A[i, j] * self.B[j, observations[t+1]] * beta[t+1, j]
                xi[t] /= np.sum(xi[t])

            # 更新参数
            self.pi = gamma[0]
            self.A = np.sum(xi, axis=0) / np.sum(gamma[:-1], axis=0)[:, None]

            # 更新观测矩阵
            for k in range(self.n_observations):
                mask = np.array(observations) == k
                self.B[:, k] = np.sum(gamma[mask], axis=0) / np.sum(gamma, axis=0)
```

---

## 第七十三章：优化理论

### 73.1 凸优化

**凸集与凸函数**：

集合$C$是凸集，如果对于任意$x, y \in C$和$\theta \in [0, 1]$：

$$\theta x + (1-\theta) y \in C$$

函数$f$是凸函数，如果对于任意$x, y$和$\theta \in [0, 1]$：

$$f(\theta x + (1-\theta) y) \leq \theta f(x) + (1-\theta) f(y)$$

**凸优化问题**：

$$\min_x f(x) \quad \text{s.t.} \quad g_i(x) \leq 0, \quad h_j(x) = 0$$

其中$f$和$g_i$是凸函数，$h_j$是仿射函数。

**拉格朗日对偶**：

$$L(x, \lambda, \nu) = f(x) + \sum_i \lambda_i g_i(x) + \sum_j \nu_j h_j(x)$$

对偶函数：

$$g(\lambda, \nu) = \inf_x L(x, \lambda, \nu)$$

对偶问题：

$$\max_{\lambda \geq 0, \nu} g(\lambda, \nu)$$

**KKT条件**：

对于凸优化问题，KKT条件是全局最优的充分必要条件：

1. 原始可行性：$g_i(x) \leq 0$，$h_j(x) = 0$
2. 对偶可行性：$\lambda_i \geq 0$
3. 互补松弛：$\lambda_i g_i(x) = 0$
4. 梯度条件：$\nabla f(x) + \sum_i \lambda_i \nabla g_i(x) + \sum_j \nu_j \nabla h_j(x) = 0$

### 73.2 随机优化

**随机梯度下降**：

```python
class StochasticGradientDescent:
    def __init__(self, lr=0.01, momentum=0.9):
        self.lr = lr
        self.momentum = momentum
        self.velocity = None

    def step(self, params, gradient):
        if self.velocity is None:
            self.velocity = np.zeros_like(params)

        # 动量更新
        self.velocity = self.momentum * self.velocity + gradient

        # 参数更新
        params -= self.lr * self.velocity

        return params
```

**方差缩减方法**：

```python
class SVRG:
    def __init__(self, model, lr=0.01):
        self.model = model
        self.lr = lr
        self.snapshot_params = None
        self.snapshot_gradients = []

    def stage(self, data, n_inner=100):
        """SVRG的一个阶段"""
        # 计算全梯度快照
        self.snapshot_params = self.model.get_params().copy()
        self.snapshot_gradients = []

        for sample in data:
            grad = self.model.gradient(sample, self.snapshot_params)
            self.snapshot_gradients.append(grad)

        full_gradient = np.mean(self.snapshot_gradients, axis=0)

        # 内循环
        for _ in range(n_inner):
            # 随机采样
            idx = np.random.randint(len(data))
            sample = data[idx]

            # 计算当前梯度
            current_grad = self.model.gradient(sample)

            # 计算快照梯度
            snapshot_grad = self.snapshot_gradients[idx]

            # 方差缩减梯度
            reduced_grad = current_grad - snapshot_grad + full_gradient

            # 更新参数
            params = self.model.get_params()
            params -= self.lr * reduced_grad
            self.model.set_params(params)
```

### 73.3 贝叶斯优化

```python
class BayesianOptimizer:
    def __init__(self, objective, bounds, acquisition='ei'):
        self.objective = objective
        self.bounds = bounds
        self.acquisition = acquisition
        self.gp = GaussianProcess()
        self.X = []
        self.y = []

    def optimize(self, n_iterations=100):
        """贝叶斯优化"""
        # 初始采样
        self.initial_sample()

        for iteration in range(n_iterations):
            # 拟合高斯过程
            self.gp.fit(self.X, self.y)

            # 最大化采集函数
            next_x = self.maximize_acquisition()

            # 评估目标函数
            next_y = self.objective(next_x)

            # 更新观测
            self.X.append(next_x)
            self.y.append(next_y)

        # 返回最优解
        best_idx = np.argmin(self.y)
        return self.X[best_idx], self.y[best_idx]

    def maximize_acquisition(self):
        """最大化采集函数"""
        def neg_acquisition(x):
            return -self.acquisition_function(x)

        # 多起点优化
        best_x = None
        best_value = float('inf')

        for _ in range(10):
            x0 = np.random.uniform(self.bounds[:, 0], self.bounds[:, 1])
            result = minimize(neg_acquisition, x0, method='L-BFGS-B', bounds=self.bounds)

            if result.fun < best_value:
                best_value = result.fun
                best_x = result.x

        return best_x

    def acquisition_function(self, x):
        """采集函数"""
        mu, sigma = self.gp.predict(x)

        if self.acquisition == 'ei':
            # 期望改进
            best_y = np.min(self.y)
            improvement = best_y - mu
            z = improvement / sigma
            ei = improvement * stats.norm.cdf(z) + sigma * stats.norm.pdf(z)
            return ei

        elif self.acquisition == 'ucb':
            # 上置信界
            kappa = 2.0
            return mu - kappa * sigma

        elif self.acquisition == 'pi':
            # 改进概率
            best_y = np.min(self.y)
            z = (best_y - mu) / sigma
            return stats.norm.cdf(z)
```

---

## 第七十四章：动力系统理论

### 74.1 非线性动力学

**相空间与轨迹**：

动力系统由微分方程描述：

$$\frac{dx}{dt} = f(x, t)$$

相空间是所有可能状态的集合，轨迹是系统在相空间中的演化路径。

**不动点与稳定性**：

不动点$x^*$满足$f(x^*) = 0$。

稳定性分析：
- 线性化：$\frac{d\delta x}{dt} = J(x^*) \delta x$
- $J$是雅可比矩阵
- 如果$J$的所有特征值实部都为负，则不动点稳定

**李雅普诺夫指数**：

$$\lambda = \lim_{t \to \infty} \frac{1}{t} \ln \frac{\|\delta x(t)\|}{\|\delta x(0)\|}$$

- $\lambda < 0$：轨迹收敛
- $\lambda > 0$：混沌

### 74.2 吸引子与混沌

**吸引子类型**：

1. **不动点吸引子**：系统收敛到固定点
2. **极限环**：周期振荡
3. **环面**：准周期运动
4. **奇异吸引子**：混沌运动

**混沌特征**：

- 对初始条件敏感
- 确定性但不可预测
- 具有分形结构
- 遍历性

**洛伦兹系统**：

```python
class LorenzSystem:
    def __init__(self, sigma=10, rho=28, beta=8/3):
        self.sigma = sigma
        self.rho = rho
        self.beta = beta

    def dynamics(self, state, t):
        x, y, z = state
        dx = self.sigma * (y - x)
        dy = x * (self.rho - z) - y
        dz = x * y - self.beta * z
        return np.array([dx, dy, dz])

    def simulate(self, initial_state, t_span, dt=0.01):
        """数值模拟"""
        t = np.arange(t_span[0], t_span[1], dt)
        states = np.zeros((len(t), 3))
        states[0] = initial_state

        for i in range(1, len(t)):
            # 龙格-库塔法
            k1 = self.dynamics(states[i-1], t[i-1])
            k2 = self.dynamics(states[i-1] + 0.5*dt*k1, t[i-1] + 0.5*dt)
            k3 = self.dynamics(states[i-1] + 0.5*dt*k2, t[i-1] + 0.5*dt)
            k4 = self.dynamics(states[i-1] + dt*k3, t[i-1] + dt)

            states[i] = states[i-1] + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)

        return t, states
```

### 74.3 分形与自相似

**分形维数**：

盒计数维数：

$$D = \lim_{\epsilon \to 0} \frac{\log N(\epsilon)}{\log(1/\epsilon)}$$

其中$N(\epsilon)$是覆盖集合所需边长为$\epsilon$的盒子数。

**分形生成**：

```python
class FractalGenerator:
    def __init__(self):
        pass

    def mandelbrot(self, c, max_iter=100):
        """曼德勃罗集"""
        z = 0
        for n in range(max_iter):
            if abs(z) > 2:
                return n
            z = z*z + c
        return max_iter

    def julia(self, z, c, max_iter=100):
        """朱利亚集"""
        for n in range(max_iter):
            if abs(z) > 2:
                return n
            z = z*z + c
        return max_iter

    def generate_mandelbrot_set(self, width, height, x_min=-2.5, x_max=1, y_min=-1, y_max=1):
        """生成曼德勃罗集图像"""
        image = np.zeros((height, width))

        for i in range(height):
            for j in range(width):
                x = x_min + (x_max - x_min) * j / width
                y = y_min + (y_max - y_min) * i / height
                c = complex(x, y)
                image[i, j] = self.mandelbrot(c)

        return image
```

---

## 第七十五章：复杂网络理论

### 75.1 网络基础

**基本度量**：

- 度分布：$P(k)$，随机选择一个节点度为$k$的概率
- 平均路径长度：$L = \frac{1}{N(N-1)} \sum_{i \neq j} d_{ij}$
- 聚类系数：$C = \frac{1}{N} \sum_i C_i$，其中$C_i = \frac{2E_i}{k_i(k_i-1)}$
- 介数中心性：$B(v) = \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}$

**网络类型**：

1. **随机网络**：Erdős-Rényi模型
2. **小世界网络**：Watts-Strogatz模型
3. **无标度网络**：Barabási-Albert模型

### 75.2 网络演化

**优先连接**：

```python
class BarabasiAlbertNetwork:
    def __init__(self, n_nodes, m_edges):
        self.n = n_nodes
        self.m = m_edges
        self.graph = nx.Graph()

    def generate(self):
        """生成BA网络"""
        # 初始化
        self.graph.add_nodes_from(range(self.m + 1))
        for i in range(self.m + 1):
            for j in range(i + 1, self.m + 1):
                self.graph.add_edge(i, j)

        # 优先连接
        for new_node in range(self.m + 1, self.n):
            # 计算连接概率
            degrees = dict(self.graph.degree())
            total_degree = sum(degrees.values())
            probabilities = [degrees[node] / total_degree for node in self.graph.nodes()]

            # 选择m个节点连接
            targets = np.random.choice(
                list(self.graph.nodes()),
                size=self.m,
                replace=False,
                p=probabilities
            )

            for target in targets:
                self.graph.add_edge(new_node, target)

        return self.graph
```

### 75.3 网络传播

**SIR模型**：

```python
class SIRModel:
    def __init__(self, network, beta=0.3, gamma=0.1):
        self.network = network
        self.beta = beta  # 感染率
        self.gamma = gamma  # 恢复率

    def simulate(self, initial_infected, max_steps=100):
        """模拟SIR传播"""
        N = len(self.network.nodes())

        # 初始化状态
        states = {node: 'S' for node in self.network.nodes()}
        for node in initial_infected:
            states[node] = 'I'

        history = [{'S': N - len(initial_infected),
                   'I': len(initial_infected),
                   'R': 0}]

        for step in range(max_steps):
            new_states = states.copy()

            for node in self.network.nodes():
                if states[node] == 'S':
                    # 计算感染概率
                    infected_neighbors = sum(1 for neighbor in self.network.neighbors(node)
                                           if states[neighbor] == 'I')
                    infection_prob = 1 - (1 - self.beta) ** infected_neighbors

                    if np.random.random() < infection_prob:
                        new_states[node] = 'I'

                elif states[node] == 'I':
                    # 恢复
                    if np.random.random() < self.gamma:
                        new_states[node] = 'R'

            states = new_states

            counts = {'S': 0, 'I': 0, 'R': 0}
            for state in states.values():
                counts[state] += 1
            history.append(counts)

            if counts['I'] == 0:
                break

        return history
```

---

## 第七十六章：博弈论

### 76.1 基本博弈

**纳什均衡**：

策略组合$(s_1^*, s_2^*, ..., s_n^*)$是纳什均衡，如果对于每个玩家$i$：

$$u_i(s_i^*, s_{-i}^*) \geq u_i(s_i, s_{-i}^*), \quad \forall s_i$$

**囚徒困境**：

|  | 合作 | 背叛 |
|--|------|------|
| 合作 | (-1, -1) | (-3, 0) |
| 背叛 | (0, -3) | (-2, -2) |

### 76.2 演化博弈

**复制者动态**：

$$\dot{x}_i = x_i [f_i(x) - \bar{f}(x)]$$

其中：
- $x_i$：策略$i$的频率
- $f_i(x)$：策略$i$的适应度
- $\bar{f}(x) = \sum_j x_j f_j(x)$：平均适应度

```python
class EvolutionaryGame:
    def __init__(self, payoff_matrix):
        self.payoff_matrix = payoff_matrix

    def replicator_dynamics(self, x, t):
        """复制者动态"""
        n = len(x)
        fitness = self.payoff_matrix @ x
        avg_fitness = x @ fitness

        dx = x * (fitness - avg_fitness)
        return dx

    def find_ess(self):
        """寻找演化稳定策略"""
        # 数值求解
        from scipy.integrate import odeint

        # 多个初始点
        ess_candidates = []
        for _ in range(100):
            x0 = np.random.dirichlet(np.ones(len(self.payoff_matrix)))
            trajectory = odeint(self.replicator_dynamics, x0, np.linspace(0, 100, 1000))
            ess_candidates.append(trajectory[-1])

        # 找到稳定点
        stable_points = []
        for candidate in ess_candidates:
            # 检查稳定性
            jacobian = self.compute_jacobian(candidate)
            eigenvalues = np.linalg.eigvals(jacobian)

            if np.all(np.real(eigenvalues) < 0):
                stable_points.append(candidate)

        return stable_points
```

### 76.3 多智能体博弈

**随机博弈**：

```python
class StochasticGame:
    def __init__(self, n_agents, n_states, n_actions, transition, rewards):
        self.n_agents = n_agents
        self.n_states = n_states
        self.n_actions = n_actions
        self.transition = transition
        self.rewards = rewards

    def nash_q_learning(self, max_episodes=10000):
        """Nash Q学习"""
        # 初始化Q值
        Q = [np.zeros((self.n_states, self.n_actions[i])) for i in range(self.n_agents)]

        for episode in range(max_episodes):
            state = np.random.randint(self.n_states)

            for step in range(100):
                # 选择动作（epsilon-greedy）
                actions = []
                for i in range(self.n_agents):
                    if np.random.random() < 0.1:
                        action = np.random.randint(self.n_actions[i])
                    else:
                        action = np.argmax(Q[i][state])
                    actions.append(action)

                # 执行动作
                next_state = self.sample_transition(state, actions)
                rewards = [self.rewards[i][state][actions[i]] for i in range(self.n_agents)]

                # 计算Nash均衡
                nash_values = self.compute_nash_equilibrium(Q, next_state)

                # 更新Q值
                for i in range(self.n_agents):
                    Q[i][state][actions[i]] += 0.1 * (rewards[i] + 0.9 * nash_values[i] - Q[i][state][actions[i]])

                state = next_state

        return Q

    def compute_nash_equilibrium(self, Q, state):
        """计算Nash均衡（简化版）"""
        # 构建收益矩阵
        payoff_matrices = []
        for i in range(self.n_agents):
            payoff = np.zeros(tuple(self.n_actions))
            # 填充收益矩阵...
            payoff_matrices.append(payoff)

        # 求解Nash均衡（使用支持枚举法等）
        # 这里简化处理，返回最大Q值
        return [np.max(Q[i][state]) for i in range(self.n_agents)]
```

---

## 第七十七章：统计力学

### 77.1 统计系综

**微正则系综**：

孤立系统，能量$E$固定：

$$\Omega(E) = \sum_i \delta(E - E_i)$$

$$S = k_B \ln \Omega(E)$$

**正则系综**：

系统与热库接触，温度$T$固定：

$$Z = \sum_i e^{-\beta E_i}$$

$$P_i = \frac{e^{-\beta E_i}}{Z}$$

$$F = -k_B T \ln Z$$

**巨正则系综**：

系统与粒子库接触，化学势$\mu$固定：

$$\Xi = \sum_i e^{\beta(\mu N_i - E_i)}$$

### 77.2 相变与临界现象

**序参量**：

描述系统有序程度的量，如磁化强度$M$。

**临界指数**：

在临界点附近：
- $M \sim |T - T_c|^{\beta}$
- $\chi \sim |T - T_c|^{-\gamma}$
- $\xi \sim |T - T_c|^{-\nu}$

**伊辛模型**：

```python
class IsingModel:
    def __init__(self, L, T, J=1):
        self.L = L
        self.T = T
        self.J = J
        self.spins = np.random.choice([-1, 1], size=(L, L))
        self.beta = 1 / T

    def energy(self):
        """计算系统能量"""
        E = 0
        for i in range(self.L):
            for j in range(self.L):
                s = self.spins[i, j]
                neighbors = [
                    self.spins[(i+1)%self.L, j],
                    self.spins[i, (j+1)%self.L]
                ]
                E -= self.J * s * sum(neighbors)
        return E

    def magnetization(self):
        """计算磁化强度"""
        return np.mean(self.spins)

    def monte_carlo_step(self):
        """蒙特卡洛步骤（Metropolis算法）"""
        for _ in range(self.L * self.L):
            # 随机选择自旋
            i = np.random.randint(self.L)
            j = np.random.randint(self.L)

            # 计算能量变化
            s = self.spins[i, j]
            neighbors = [
                self.spins[(i-1)%self.L, j],
                self.spins[(i+1)%self.L, j],
                self.spins[i, (j-1)%self.L],
                self.spins[i, (j+1)%self.L]
            ]
            delta_E = 2 * self.J * s * sum(neighbors)

            # Metropolis准则
            if delta_E < 0 or np.random.random() < np.exp(-self.beta * delta_E):
                self.spins[i, j] *= -1

    def simulate(self, n_steps=10000):
        """模拟"""
        energies = []
        magnetizations = []

        for step in range(n_steps):
            self.monte_carlo_step()

            if step % 100 == 0:
                energies.append(self.energy())
                magnetizations.append(self.magnetization())

        return energies, magnetizations
```

---

## 第七十八章：量子力学基础

### 78.1 量子态与算符

**量子态**：

量子态用希尔伯特空间中的向量表示：

$$|\psi\rangle = \sum_i c_i |i\rangle$$

其中$\sum_i |c_i|^2 = 1$。

**测量**：

测量算符$\{M_m\}$满足$\sum_m M_m^\dagger M_m = I$。

测量后状态：

$$|\psi_m\rangle = \frac{M_m |\psi\rangle}{\sqrt{\langle\psi|M_m^\dagger M_m|\psi\rangle}}$$

测量概率：

$$p(m) = \langle\psi|M_m^\dagger M_m|\psi\rangle$$

**密度矩阵**：

$$\rho = \sum_i p_i |\psi_i\rangle\langle\psi_i|$$

性质：
- $\rho^\dagger = \rho$
- $\text{tr}(\rho) = 1$
- $\rho \geq 0$

### 78.2 量子纠缠

**贝尔态**：

$$|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$$

$$|\Phi^-\rangle = \frac{1}{\sqrt{2}}(|00\rangle - |11\rangle)$$

$$|\Psi^+\rangle = \frac{1}{\sqrt{2}}(|01\rangle + |10\rangle)$$

$$|\Psi^-\rangle = \frac{1}{\sqrt{2}}(|01\rangle - |10\rangle)$$

**纠缠熵**：

$$S_A = -\text{tr}(\rho_A \log \rho_A)$$

其中$\rho_A = \text{tr}_B(\rho_{AB})$。

### 78.3 量子计算

**量子门**：

```python
import numpy as np

class QuantumGate:
    def __init__(self):
        # 常用量子门
        self.H = 1/np.sqrt(2) * np.array([[1, 1], [1, -1]])  # Hadamard
        self.X = np.array([[0, 1], [1, 0]])  # Pauli-X
        self.Y = np.array([[0, -1j], [1j, 0]])  # Pauli-Y
        self.Z = np.array([[1, 0], [0, -1]])  # Pauli-Z
        self.CNOT = np.array([[1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, 0, 1],
                              [0, 0, 1, 0]])

class QuantumCircuit:
    def __init__(self, n_qubits):
        self.n_qubits = n_qubits
        self.state = np.zeros(2**n_qubits, dtype=complex)
        self.state[0] = 1  # 初始化为|0...0>

    def apply_gate(self, gate, target, control=None):
        """应用量子门"""
        if control is None:
            # 单量子门
            full_gate = self.expand_gate(gate, target)
        else:
            # 受控门
            full_gate = self.expand_controlled_gate(gate, control, target)

        self.state = full_gate @ self.state

    def expand_gate(self, gate, target):
        """将单量子门扩展到全空间"""
        result = 1
        for i in range(self.n_qubits):
            if i == target:
                result = np.kron(result, gate)
            else:
                result = np.kron(result, np.eye(2))
        return result

    def measure(self, qubit):
        """测量量子比特"""
        # 计算概率
        prob_0 = 0
        prob_1 = 0

        for i in range(2**self.n_qubits):
            if (i >> qubit) & 1 == 0:
                prob_0 += abs(self.state[i])**2
            else:
                prob_1 += abs(self.state[i])**2

        # 采样
        result = 1 if np.random.random() < prob_1 else 0

        # 坍缩
        mask = [(i >> qubit) & 1 == result for i in range(2**self.n_qubits)]
        self.state[~np.array(mask)] = 0
        self.state /= np.sqrt(prob_1 if result == 1 else prob_0)

        return result
```

---

## 第七十九章：拓扑学基础

### 79.1 拓扑空间

**定义**：

拓扑空间$(X, \tau)$，其中$\tau$是$X$的子集族，满足：
1. $\emptyset, X \in \tau$
2. 任意并封闭
3. 有限交封闭

**连续映射**：

$f: X \to Y$连续，如果对于$Y$中任意开集$V$，$f^{-1}(V)$是$X$中的开集。

**同胚**：

$f: X \to Y$是同胚，如果$f$是双射且$f$和$f^{-1}$都连续。

### 79.2 同调群

**单纯复形**：

由顶点、边、面等单纯形组成的复合体。

**链复形**：

$$... \xrightarrow{\partial_{n+1}} C_n \xrightarrow{\partial_n} C_{n-1} \xrightarrow{\partial_{n-1}} ...$$

其中$\partial_n \circ \partial_{n+1} = 0$。

**同调群**：

$$H_n = \ker(\partial_n) / \text{im}(\partial_{n+1})$$

### 79.3 持久同调

```python
class PersistentHomology:
    def __init__(self, filtration):
        self.filtration = filtration

    def compute(self):
        """计算持久同调"""
        # 初始化
        boundary_matrix = self.build_boundary_matrix()
        low = {}  # 每列的最低非零元

        # 约化
        for j in range(len(boundary_matrix)):
            while boundary_matrix[:, j].any():
                # 找到最低非零元
                low_j = self.get_lowest(boundary_matrix[:, j])

                if low_j not in low:
                    low[low_j] = j
                    break
                else:
                    # 消去
                    j_prime = low[low_j]
                    boundary_matrix[:, j] = (boundary_matrix[:, j] + boundary_matrix[:, j_prime]) % 2

        # 提取持久对
        persistence_pairs = []
        for j in range(len(boundary_matrix)):
            if j not in low.values():
                # j是生成元
                if self.get_lowest(boundary_matrix[:, j]) is not None:
                    i = self.get_lowest(boundary_matrix[:, j])
                    birth = self.filtration.get_time(i)
                    death = self.filtration.get_time(j)
                    persistence_pairs.append((birth, death))

        return persistence_pairs

    def get_lowest(self, column):
        """获取列的最低非零元索引"""
        non_zero = np.where(column != 0)[0]
        if len(non_zero) == 0:
            return None
        return non_zero[-1]
```

---

## 第八十章：信息几何

### 80.1 统计流形

**Fisher信息矩阵**：

$$g_{ij}(\theta) = \mathbb{E}\left[\frac{\partial \log p(x|\theta)}{\partial \theta_i} \frac{\partial \log p(x|\theta)}{\partial \theta_j}\right]$$

**自然梯度**：

$$\tilde{\nabla} f = G^{-1} \nabla f$$

其中$G$是Fisher信息矩阵。

### 80.2 散度度量

**KL散度**：

$$D_{KL}[p||q] = \int p(x) \log \frac{p(x)}{q(x)} dx$$

**Jensen-Shannon散度**：

$$D_{JS}[p||q] = \frac{1}{2} D_{KL}[p||m] + \frac{1}{2} D_{KL}[q||m]$$

其中$m = \frac{p+q}{2}$。

**Wasserstein距离**：

$$W_p(p, q) = \left(\inf_{\gamma \in \Gamma(p,q)} \int d(x,y)^p d\gamma(x,y)\right)^{1/p}$$

### 80.3 自然梯度下降

```python
class NaturalGradientDescent:
    def __init__(self, model, lr=0.01):
        self.model = model
        self.lr = lr

    def compute_fisher_information(self, data):
        """计算Fisher信息矩阵"""
        n_params = sum(p.numel() for p in self.model.parameters())
        fisher = torch.zeros(n_params, n_params)

        for sample in data:
            self.model.zero_grad()
            log_prob = self.model.log_prob(sample)
            log_prob.backward()

            grad = torch.cat([p.grad.flatten() for p in self.model.parameters()])
            fisher += torch.outer(grad, grad)

        fisher /= len(data)
        return fisher

    def step(self, gradient, fisher):
        """自然梯度下降步骤"""
        # 添加正则化
        fisher_reg = fisher + 1e-4 * torch.eye(fisher.size(0))

        # 计算自然梯度
        natural_gradient = torch.linalg.solve(fisher_reg, gradient)

        # 更新参数
        idx = 0
        for param in self.model.parameters():
            size = param.numel()
            param.data -= self.lr * natural_gradient[idx:idx+size].view(param.shape)
            idx += size
```

---

**文档结束**
