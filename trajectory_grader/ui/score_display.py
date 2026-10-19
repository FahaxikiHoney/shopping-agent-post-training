import plotly.graph_objects as go
import streamlit as st
from core.data_models import GradeResult

DIM_LABELS = {
    "d1_intent_understanding": "需求理解",
    "d2_factuality": "真实性",
    "d3_relevance": "推荐相关性",
    "d4_completeness": "回应完整性",
    "d5_reasoning_value": "理由价值感",
}
GATE_DIMS = {"d1_intent_understanding", "d4_completeness"}
VERDICT_COLORS = {"PASS": "#2ecc71", "FAIL": "#e74c3c"}


def render_score_display(result: GradeResult):
    # ── 总分 Banner ────────────────────────────────────────────────
    if result.is_gate_failed:
        failure_labels = []
        for f in result.gate_failures:
            if f in DIM_LABELS:
                failure_labels.append(f"维度失败：{DIM_LABELS[f]}")
            else:
                failure_labels.append(f"规则检查失败：{f}")
        st.error(f"### 🔴 GATE FAILED — 总分：0\n\n" + "  |  ".join(failure_labels))
    else:
        score = result.final_score
        color = "#2ecc71" if score >= 0.75 else "#f39c12" if score >= 0.5 else "#e74c3c"
        st.markdown(
            f"<div style='text-align:center;padding:20px;border-radius:12px;background:#f8f9fa'>"
            f"<span style='font-size:56px;font-weight:bold;color:{color}'>{score:.3f}</span>"
            f"<br><span style='color:#888;font-size:16px'>综合评分（满分 1.000）</span></div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Extra Gate 状态行 ────────────────────────────────────────────
    st.markdown("**规则型 Gate 检查**")
    gate_cols = st.columns(3)
    for i, eg in enumerate(result.extra_gate_results):
        icon = "✅" if eg.passed else "❌"
        label_map = {
            "card_id_validator": "商品ID合法性",
            "tool_call_failure_rate": "工具调用错误",
            "text_quality_penalty": "文本质量",
        }
        label = label_map.get(eg.name, eg.name)
        with gate_cols[i]:
            st.markdown(f"{icon} **{label}**")
            if not eg.passed:
                detail = eg.detail
                if "hallucinated_ids" in detail and detail["hallucinated_ids"]:
                    st.caption(f"幻觉 ID: {detail['hallucinated_ids']}")
                if "caller_errors" in detail and detail["caller_errors"]:
                    st.caption(f"错误步骤: {detail['caller_errors']}")
                if "issues" in detail and detail["issues"]:
                    st.caption(f"问题: {detail['issues']}")

    st.divider()

    if not result.dimension_scores:
        st.info("Gate 检查失败，跳过维度评分。")
        return

    # ── 图表：雷达图 + 瀑布图 ────────────────────────────────────────
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**5 维度评分雷达图**")
        labels = [DIM_LABELS.get(k, k) for k in DIM_LABELS]
        values = [result.dimension_scores.get(k).score if result.dimension_scores.get(k) else 0 for k in DIM_LABELS]
        fig_radar = go.Figure(go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            fillcolor="rgba(52,152,219,0.25)",
            line=dict(color="#3498db", width=2),
            marker=dict(size=7),
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=10))),
            showlegend=False,
            margin=dict(l=40, r=40, t=30, b=30),
            height=300,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with chart_col2:
        if not result.is_gate_failed:
            st.markdown("**分数构成瀑布图**")
            sb = result.score_breakdown
            fig_wf = go.Figure(go.Waterfall(
                name="分数分解",
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["基础分(Gate通过)", "真实性贡献", "相关性贡献", "价值感贡献", "总分"],
                y=[sb.base_score, sb.d2_contribution, sb.d3_contribution, sb.d5_contribution, 0],
                connector=dict(line=dict(color="rgb(63,63,63)")),
                increasing=dict(marker_color="#2ecc71"),
                totals=dict(marker_color="#3498db"),
            ))
            fig_wf.update_layout(
                showlegend=False,
                yaxis=dict(range=[0, 1.05], tickformat=".2f"),
                margin=dict(l=20, r=20, t=30, b=30),
                height=300,
            )
            st.plotly_chart(fig_wf, use_container_width=True)

    st.divider()

    # ── 维度详情折叠卡片 ────────────────────────────────────────────
    st.markdown("**各维度详情**")
    for dim_id, label in DIM_LABELS.items():
        dr = result.dimension_scores.get(dim_id)
        if not dr:
            continue
        is_gate = dim_id in GATE_DIMS
        gate_badge = "🔒 Gate 维度" if is_gate else ""
        verdict_color = VERDICT_COLORS[dr.verdict]
        verdict_icon = "✅" if dr.verdict == "PASS" else "❌"

        header = f"{verdict_icon} **{label}** {gate_badge}  —  score: `{dr.score:.2f}`"
        with st.expander(header, expanded=(dr.verdict == "FAIL")):
            st.progress(dr.score, text=f"{dr.score:.0%}")
            badge_html = (
                f"<span style='background:{verdict_color};color:white;"
                f"padding:2px 10px;border-radius:10px;font-size:13px'>{dr.verdict}</span>"
            )
            st.markdown(badge_html, unsafe_allow_html=True)
            st.markdown(f"**评估说明：** {dr.reasoning}")
            if dr.evidence:
                st.markdown("**证据引用：**")
                for ev in dr.evidence:
                    st.markdown(f"- `{ev}`")

    st.caption(f"Judge 模式: `{result.judge_mode}`  |  Trajectory ID: `{result.trajectory_id}`")
