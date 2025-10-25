# load packages needed for this tutorial
using Knockoffs
using Random
using GLMNet
using Distributions
using LinearAlgebra
using ToeplitzMatrices
using StatsKit
using Plots
using Printf

println("="^60)
println("高维统计推断：Knockoffs方法与Lasso对比分析")
println("="^60)

Random.seed!(2022)
n = 500 # sample size
p = 1000 # number of covariates
rho = 0.4
Σ = Matrix(SymmetricToeplitz(rho .^ (0:(p-1)))) # true covariance matrix
μ = zeros(p) # true mean parameters
L = cholesky(Σ).L
X = randn(n, p) * L # var(X) = L var(N(0, 1)) L' = var(Σ)

# set seed for reproducibility
Random.seed!(123)

# simulate true beta
n_samples, n_vars = size(X)
k = 50 # number of true non-zero coefficients
βtrue = zeros(n_vars)
βtrue[1:k] .= randn(k)
shuffle!(βtrue)

# find true causal variables
correct_position = findall(!iszero, βtrue)
println("\n数据生成参数:")
println("  样本数 n = $n_samples")
println("  变量数 p = $n_vars")
println("  相关系数 ρ = $rho")
println("  真实非零系数个数 k = $k")
println("  真实因果变量位置个数: $(length(correct_position))")

# simulate y
y = X * βtrue + randn(n_samples)

# ==================== LASSO 方法 ====================
println("\n" * "="^60)
println("Lasso变量选择结果")
println("="^60)

# run 10-fold cross validation to find best λ minimizing MSE
lasso_cv = glmnetcv(X, y)
λbest = lasso_cv.lambda[argmin(lasso_cv.meanloss)]

# use λbest to fit LASSO on full data
βlasso = glmnet(X, y, lambda=[λbest]).betas[:, 1]

# check power and false discovery rate
lasso_selected = findall(!iszero, βlasso)
lasso_tp = length(lasso_selected ∩ correct_position)  # true positives
lasso_fp = length(setdiff(lasso_selected, correct_position))  # false positives
lasso_fn = length(setdiff(correct_position, lasso_selected))  # false negatives

lasso_power = lasso_tp / k
lasso_fdr = lasso_fp / max(length(lasso_selected), 1)

println("\nLasso参数: λ = $λbest")
println("  选中的变量个数: $(length(lasso_selected))")
println("  真阳性(TP): $lasso_tp")
println("  假阳性(FP): $lasso_fp")
println("  假阴性(FN): $lasso_fn")
println("  统计幂(Power): $(round(lasso_power, digits=4))")
println("  虚发现率(FDR): $(round(lasso_fdr, digits=4))")

# ==================== Knockoffs 方法 ====================
println("\n" * "="^60)
println("Knockoffs变量选择结果")
println("="^60)

# run 10 simulations and compute empirical power/FDR
nsims = 10
empirical_power = zeros(5)
empirical_fdr = zeros(5)
knockoff_results = []

for sim in 1:nsims
    print("  运行模拟 $sim/$nsims ... ")
    knockoff_filter = fit_lasso(y, X, method=:mvr)
    push!(knockoff_results, knockoff_filter)
    println("完成")

    for j in eachindex(knockoff_filter.fdr_target)
        selected = knockoff_filter.selected[j]
        tp = length(selected ∩ correct_position)
        fp = length(setdiff(selected, correct_position))

        power = tp / k
        fdp = fp / max(length(selected), 1)
        empirical_power[j] += power
        empirical_fdr[j] += fdp
    end
end
empirical_power ./= nsims
empirical_fdr ./= nsims

# 获取目标FDR值
target_fdr = knockoff_results[1].fdr_target

println("\nKnockoffs 方法的目标FDR和实际结果:")
for j in eachindex(target_fdr)
    println(@sprintf("  目标FDR = %.2f: 实际FDR = %.4f, 统计幂 = %.4f",
                     target_fdr[j], empirical_fdr[j], empirical_power[j]))
end

# ==================== 可视化对比 ====================
println("\n" * "="^60)
println("生成对比可视化")
println("="^60)

# 创建对比图表
p1 = plot(target_fdr, empirical_power,
          xlabel="Target FDR", ylabel="Power",
          title="Knockoffs Method: Power vs Target FDR",
          legend=false, linewidth=2, marker=:circle, markersize=5, grid=true)

p2 = plot(target_fdr, empirical_fdr,
          xlabel="Target FDR", ylabel="Empirical FDR",
          title="Knockoffs Method: FDR Control",
          legend=false, linewidth=2, marker=:circle, markersize=5, grid=true)
# 添加参考线y=x
plot!(p2, target_fdr, target_fdr, line=:dash, color=:red, label="Ideal case (y=x)", alpha=0.7)

# 创建方法对比图
p3 = bar([1, 2], [lasso_power, empirical_power[3]],
         title="Power Comparison (Target FDR=0.10)",
         ylabel="Power",
         legend=false,
         xticks=(1:2, ["Lasso", "Knockoffs"]),
         ylim=(0, 1))

p4 = bar([1, 2], [lasso_fdr, empirical_fdr[3]],
         title="FDR Comparison (Target FDR=0.10)",
         ylabel="False Discovery Rate",
         legend=false,
         xticks=(1:2, ["Lasso", "Knockoffs"]),
         ylim=(0, maximum([lasso_fdr, empirical_fdr[3]]) * 1.2))

# 组合所有图表
final_plot = plot(p1, p2, p3, p4, layout=(2, 2), size=(1200, 900))
savefig(final_plot, "knockoffs_vs_lasso.png")
println("  已保存图表: knockoffs_vs_lasso.png")

# ==================== 总结 ====================
println("\n" * "="^60)
println("方法对比总结")
println("="^60)
println("\nLasso方法:")
println("  - 统计幂: $(round(lasso_power, digits=4))")
println("  - 虚发现率: $(round(lasso_fdr, digits=4))")
println("  - 选中变量数: $(length(lasso_selected))")

println("\nKnockoffs方法 (FDR目标=0.10):")
println("  - 统计幂: $(round(empirical_power[3], digits=4))")
println("  - 虚发现率: $(round(empirical_fdr[3], digits=4))")
println("  - 平均选中变量数: $(round(mean([length(knockoff_results[i].selected[3]) for i in 1:nsims]), digits=1))")

if empirical_power[3] > lasso_power
    improvement = round((empirical_power[3] - lasso_power) / lasso_power * 100, digits=2)
    println("\n✓ Knockoffs的统计幂更高，提升 $(improvement)%")
else
    println("\n✓ Lasso的统计幂更高")
end

if empirical_fdr[3] <= 0.10
    println("✓ Knockoffs有效控制了FDR在目标水平以下")
else
    println("✗ Knockoffs的实际FDR超过了目标水平")
end

println("\n" * "="^60)
println("分析完成！")
println("="^60)
