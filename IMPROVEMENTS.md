# Knockoffs.jl 代码改进详解

## 版本对比

### 原始代码的问题

#### 问题1：变量命名冲突（第24行）
```julia
# ❌ 原始代码
n, p = size(X)  # 重新定义n和p，覆盖之前的定义！
```

**问题说明**：
- 第17-18行定义了 `n = 500, p = 1000`
- 第24行重新定义了 `n, p = size(X)`
- 虽然大小相同，但这样做违反了DRY原则，容易出错
- 如果之后改变数据生成的n或p，会导致逻辑混乱

**修复方案**：
```julia
# ✓ 改进后的代码
n_samples, n_vars = size(X)  # 用新变量名，避免覆盖
```

#### 问题2：FDR变量的模糊性（第66行）
```julia
# ❌ 原始代码
power_plot = plot(FDR, empirical_power, ...)  # FDR是什么？
fdr_plot = plot(FDR, empirical_fdr, ...)      # 混淆了概念
```

**问题说明**：
- 变量 `FDR` 来自Lasso结果（第45行）
- 但在绘图时当作目标FDR值使用
- 这两个概念完全不同：
  - Lasso的FDR：单一的观测值（方法评估结果）
  - 目标FDR：Knockoffs的目标水平（方法参数）

**修复方案**：
```julia
# ✓ 改进后的代码
target_fdr = knockoff_results[1].fdr_target  # 明确提取目标FDR
# 后续绘图使用target_fdr作为x轴
```

#### 问题3：统计指标输出不完整
```julia
# ❌ 原始代码只输出
println("Lasso power = $power, FDR = $FDR")
# 缺少关键信息：
# - 选中变量个数
# - 真阳性/假阳性/假阴性的具体计数
# - Knockoffs结果的详细说明
```

**修复方案**：
```julia
# ✓ 改进后的代码
println("  选中的变量个数: $(length(lasso_selected))")
println("  真阳性(TP): $lasso_tp")
println("  假阳性(FP): $lasso_fp")
println("  假阴性(FN): $lasso_fn")
println("  统计幂(Power): $(round(lasso_power, digits=4))")
println("  虚发现率(FDR): $(round(lasso_fdr, digits=4))")
```

#### 问题4：循环变量冲突（第52-54行）
```julia
# ❌ 原始代码
for i in 1:nsims
    knockoff_filter = fit_lasso(y, X, method=:mvr)
    for i in eachindex(knockoff_filter.fdr_target)  # 重复使用i！
```

**问题说明**：
- 外层循环变量是 `i`
- 内层循环也使用 `i`，造成变量覆盖
- 外层循环会因此无法正确迭代

**修复方案**：
```julia
# ✓ 改进后的代码
for sim in 1:nsims                              # 改为sim
    knockoff_filter = fit_lasso(y, X, method=:mvr)
    for j in eachindex(knockoff_filter.fdr_target)  # 改为j
```

#### 问题5：缺少结果保存机制
```julia
# ❌ 原始代码
for i in 1:nsims
    knockoff_filter = fit_lasso(y, X, method=:mvr)
    # 立即计算统计量，没有保存结果对象
```

**问题说明**：
- 每次循环都生成了结果但没有保存
- 无法在循环后访问每个Knockoff结果的详细信息
- 无法计算变量选择的平均值等统计量

**修复方案**：
```julia
# ✓ 改进后的代码
knockoff_results = []  # 存储所有结果
for sim in 1:nsims
    knockoff_filter = fit_lasso(y, X, method=:mvr)
    push!(knockoff_results, knockoff_filter)  # 保存结果
```

---

## 新增功能详解

### 功能1：程序流程标题和分隔符

```julia
println("="^60)
println("高维统计推断：Knockoffs方法与Lasso对比分析")
println("="^60)
```

**作用**：
- 清晰标识程序的三个主要阶段
- 便于阅读和调试长输出结果
- 专业的报告格式

### 功能2：数据生成参数显示

```julia
println("数据生成参数:")
println("  样本数 n = $n_samples")
println("  变量数 p = $n_vars")
println("  相关系数 ρ = $rho")
println("  真实非零系数个数 k = $k")
```

**重要性**：
- 再现性：其他人可以用相同参数重复实验
- 透明性：清楚数据来源和设置
- 调试便利：快速验证参数

### 功能3：详细的结果统计

#### 新增的性能指标
```julia
lasso_tp = length(lasso_selected ∩ correct_position)    # 真阳性
lasso_fp = length(setdiff(lasso_selected, correct_position))  # 假阳性
lasso_fn = length(setdiff(correct_position, lasso_selected))  # 假阴性
```

**这些指标的含义**：

| 指标 | 公式 | 解释 |
|------|------|------|
| TP | 正确识别的因果变量 | 越高越好 |
| FP | 错误标记为因果的变量 | 越低越好 |
| FN | 遗漏的真正因果变量 | 越低越好 |
| Power | TP / k | 检验效能 |
| FDR | FP / max(\|选中\|, 1) | 虚发现率 |

### 功能4：结果对比和自动判断

```julia
if empirical_power[3] > lasso_power
    improvement = round((empirical_power[3] - lasso_power) /
                        lasso_power * 100, digits=2)
    println("✓ Knockoffs的统计幂更高，提升 $(improvement)%")
else
    println("✓ Lasso的统计幂更高")
end

if empirical_fdr[3] <= 0.10
    println("✓ Knockoffs有效控制了FDR在目标水平以下")
else
    println("✗ Knockoffs的实际FDR超过了目标水平")
end
```

**优势**：
- 自动化的结果解读
- 量化的改进度计算
- 清晰的结论显示

### 功能5：多维可视化

#### 图表1：Knockoffs方法的幂-FDR权衡
```julia
p1 = plot(target_fdr, empirical_power,
          xlabel="目标FDR", ylabel="统计幂(Power)",
          title="Knockoffs方法: FDR与统计幂的关系",
          legend=false, linewidth=2, marker=:circle, ...)
```

**展示内容**：FDR目标如何影响选中变量数和幂

#### 图表2：FDR控制效果
```julia
p2 = plot(target_fdr, empirical_fdr, ...)
plot!(p2, target_fdr, target_fdr, line=:dash,
      color=:red, label="理想情况(y=x)", alpha=0.7)
```

**展示内容**：Knockoffs是否成功控制了FDR

#### 图表3&4：两种方法的直接对比
```julia
p3 = bar([1, 2], [lasso_power, empirical_power[3]], ...)  # 幂对比
p4 = bar([1, 2], [lasso_fdr, empirical_fdr[3]], ...)     # FDR对比
```

**展示内容**：Lasso vs Knockoffs的定量对比

---

## 代码改进的系统性

### 1. 模块化结构

```
┌─ 数据生成和参数设置
├─ Lasso变量选择模块
│  ├─ 交叉验证找最优λ
│  ├─ 拟合模型
│  └─ 计算性能指标
├─ Knockoffs变量选择模块
│  ├─ 多次模拟运行
│  ├─ 结果存储和累积
│  └─ 平均性能计算
├─ 可视化和对比模块
│  ├─ Knockoffs单独分析
│  ├─ 两种方法对比
│  └─ 保存图表文件
└─ 结果总结和判断
```

### 2. 可读性改进

**前**：变量名混乱，逻辑不清
```julia
for i in 1:nsims
    @time knockoff_filter = fit_lasso(y, X, method=:mvr)
    for i in eachindex(knockoff_filter.fdr_target)
        selected = knockoff_filter.selected[i]
        ...
    end
end
```

**后**：清晰的流程和有意义的变量名
```julia
for sim in 1:nsims
    print("  运行模拟 $sim/$nsims ... ")
    knockoff_filter = fit_lasso(y, X, method=:mvr)
    push!(knockoff_results, knockoff_filter)
    println("完成")

    for j in eachindex(knockoff_filter.fdr_target)
        selected = knockoff_filter.selected[j]
        tp = length(selected ∩ correct_position)
        fp = length(setdiff(selected, correct_position))
        ...
    end
end
```

### 3. 输出信息的层次化

```
1级：项目标题和大分隔符
2级：方法名和功能分隔符
3级：参数和结果详情
4级：具体的统计数值
```

---

## 技术细节

### 关键Julia语言特性的使用

#### 1. 集合操作
```julia
# 交集：找到既在lasso_selected又在correct_position中的元素
lasso_selected ∩ correct_position

# 差集：找到在lasso_selected但不在correct_position中的元素
setdiff(lasso_selected, correct_position)
```

#### 2. 字符串格式化
```julia
# Printf宏提供C风格的格式化
@sprintf("目标FDR = %.2f: 实际FDR = %.4f, 统计幂 = %.4f",
         target_fdr[j], empirical_fdr[j], empirical_power[j])

# 四舍五入到指定位数
round(lasso_power, digits=4)
```

#### 3. 数组操作
```julia
# 向量化操作：逐元素除法
empirical_power ./= nsims

# 平均值计算
mean([length(knockoff_results[i].selected[3]) for i in 1:nsims])
```

---

## 性能优化建议

### 1. 并行化Knockoffs模拟

如果计算时间过长，可以使用并行计算：

```julia
using Distributed
addprocs(4)  # 添加4个进程

@distributed for sim in 1:nsims
    knockoff_filter = fit_lasso(y, X, method=:mvr)
    # ... 计算逻辑
end
```

### 2. 缓存协方差矩阵

避免重复计算：

```julia
# 预先计算
Σ = Matrix(SymmetricToeplitz(rho .^ (0:(p-1))))
L = cholesky(Σ).L

# 后续直接使用L而不是重新计算
```

### 3. 内存优化

对于非常大的矩阵，考虑不保存所有中间结果。

---

## 验证清单

使用改进后的代码时，请验证：

- [ ] Julia环境已安装所有必需包
- [ ] 工作目录正确
- [ ] 输出中显示了完整的参数信息
- [ ] 生成了PNG格式的图表文件
- [ ] 控制台输出中包含了对比结论
- [ ] FDR控制是否按预期工作

---

## 总结

改进后的代码在以下方面得到了显著改进：

✓ **准确性**：修复了5个代码逻辑问题
✓ **完整性**：新增了详细的统计指标输出
✓ **可读性**：改进了变量命名和代码组织
✓ **专业性**：添加了格式化的报告输出
✓ **可视化**：生成了综合的对比分析图表
✓ **再现性**：详细记录了所有参数设置
