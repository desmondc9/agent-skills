#!/usr/bin/env python3
"""
撇开成本与历史的企业 / 资产估值计算器
基于吴军《财商训练课》「企业估值」一讲的方法论。

核心思想：一项经营型资产的价值，不取决于它的成本或历史价格，
只取决于两件事 —— 未来能持续产生多少自由现金流（FCF），以及这件事的风险有多大。

本脚本实现三个步骤：
  1. 风险调整后的折现率   d = 1 + r + β·(rm − r)     （CAPM 思路）
  2. 逐年折现自由现金流   DCFₜ = FCFₜ / dᵗ
  3. 折现现金流求和       ΣDCF = Σ DCFₜ
     并按吴军的「等价存款本金」口径换算估值：
       估值 = ΣDCF / [(1 + r)ⁿ − 1]
     （即：需要多少本金存银行 n 年、按无风险利率 r 复利，
       才能产生与 ΣDCF 等额的利润。）

用法示例：
  # 直接传入逐年 FCF（单位随意，结果同单位）
  python dcf_valuation.py --fcf 500 1020 800 1300 1100 1400 1600 1500 1700 1900 \
      --r 0.03 --rm 0.05 --beta 2.0

  # 从 JSON 文件读取（见 --help）
  python dcf_valuation.py --json case.json

  # 风险固定收益类资产的期望收益（票据 / 理财）口径
  python dcf_valuation.py --expected 10500:0.87 10000:0.05 5000:0.05 0:0.03 \
      --r 0.03
"""
import argparse
import json
import sys


def discounted_cash_flows(fcf, r, rm, beta):
    """逐年风险调整折现。返回 (每年 DCF 列表, 折现率 d)。"""
    d = 1 + r + beta * (rm - r)
    dcfs = [cf / (d ** (t + 1)) for t, cf in enumerate(fcf)]
    return dcfs, d


def valuation_from_dcf(sum_dcf, r, n):
    """吴军「等价存款本金」口径：估值 = ΣDCF / [(1+r)^n − 1]。"""
    growth = (1 + r) ** n - 1
    if growth == 0:
        return float("inf")
    return sum_dcf / growth


def expected_return(scenarios):
    """风险固定收益资产的期望收益。scenarios: [(payoff, prob), ...]。"""
    total_prob = sum(p for _, p in scenarios)
    ev = sum(payoff * p for payoff, p in scenarios)
    return ev, total_prob


def fmt(x):
    return f"{x:,.2f}"


def run_dcf(fcf, r, rm, beta):
    n = len(fcf)
    dcfs, d = discounted_cash_flows(fcf, r, rm, beta)
    sum_dcf = sum(dcfs)
    pv_valuation = sum_dcf  # 标准 DCF 口径：折现现金流之和即现值
    deposit_valuation = valuation_from_dcf(sum_dcf, r, n)

    print("=" * 60)
    print("企业 / 资产估值 — 折现自由现金流 (DCF)")
    print("=" * 60)
    print(f"无风险利率 r        : {r:.2%}")
    print(f"市场平均回报 rm      : {rm:.2%}")
    print(f"风险系数 β           : {beta}")
    print(f"风险调整折现率 d     : {d:.4f}  (= 1 + r + β·(rm − r))")
    print(f"年限 n               : {n}")
    print("-" * 60)
    print(f"{'年份 t':>6} {'FCF':>14} {'折现 DCFₜ':>16}")
    for t, (cf, dcf) in enumerate(zip(fcf, dcfs), start=1):
        print(f"{t:>6} {fmt(cf):>14} {fmt(dcf):>16}")
    print("-" * 60)
    print(f"折现现金流之和 ΣDCF                : {fmt(sum_dcf)}")
    print(f"估值（标准现值口径 = ΣDCF）        : {fmt(pv_valuation)}")
    print(f"估值（吴军等价存款本金口径）        : {fmt(deposit_valuation)}")
    print("=" * 60)
    print("提醒：风险越大(β越高)折现越狠，估值越低；现金流越稳越高，估值越高。")
    return {
        "discount_rate": d,
        "dcfs": dcfs,
        "sum_dcf": sum_dcf,
        "valuation_present_value": pv_valuation,
        "valuation_deposit_equivalent": deposit_valuation,
    }


def run_expected(scenarios, r):
    ev, total_prob = expected_return(scenarios)
    print("=" * 60)
    print("风险固定收益资产 — 期望收益与基准线对比")
    print("=" * 60)
    if abs(total_prob - 1.0) > 1e-6:
        print(f"⚠ 概率之和为 {total_prob:.2%}，应为 100%，请检查输入。")
    print(f"{'到期payoff':>14} {'概率':>10}")
    for payoff, p in scenarios:
        print(f"{fmt(payoff):>14} {p:>10.2%}")
    print("-" * 60)
    print(f"期望收益 E            : {fmt(ev)}")
    if r is not None:
        true_value = ev / (1 + r)
        print(f"无风险利率 r          : {r:.2%}")
        print(f"折回今天的真实价值    : {fmt(true_value)}  (= E / (1+r))")
        print("（即存这么多钱进银行，到期能拿到与该资产期望值相同的钱）")
    print("=" * 60)
    return {"expected_value": ev, "risk_free_rate": r}


def parse_scenarios(items):
    out = []
    for item in items:
        payoff, prob = item.split(":")
        out.append((float(payoff), float(prob)))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="撇开成本与历史的企业/资产估值计算器 (DCF + 风险调整)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="JSON 格式: {\"fcf\":[...], \"r\":0.03, \"rm\":0.05, \"beta\":2.0}",
    )
    ap.add_argument("--fcf", nargs="+", type=float, help="逐年自由现金流序列")
    ap.add_argument("--r", type=float, help="无风险利率，如 0.03")
    ap.add_argument("--rm", type=float, default=0.05, help="市场平均回报，默认 0.05")
    ap.add_argument("--beta", type=float, default=1.0, help="风险系数 β，默认 1.0")
    ap.add_argument("--json", help="从 JSON 文件读取 fcf/r/rm/beta")
    ap.add_argument(
        "--expected",
        nargs="+",
        help="风险固定收益资产期望收益，格式 payoff:prob，可多个",
    )
    args = ap.parse_args()

    if args.expected:
        scenarios = parse_scenarios(args.expected)
        run_expected(scenarios, args.r)
        return

    if args.json:
        with open(args.json, encoding="utf-8") as f:
            cfg = json.load(f)
        fcf = cfg["fcf"]
        r = cfg.get("r", args.r)
        rm = cfg.get("rm", args.rm)
        beta = cfg.get("beta", args.beta)
    else:
        fcf = args.fcf
        r = args.r
        rm = args.rm
        beta = args.beta

    if not fcf or r is None:
        ap.error("需要提供 --fcf 与 --r（或通过 --json 提供），或使用 --expected。")

    run_dcf(fcf, r, rm, beta)


if __name__ == "__main__":
    main()
