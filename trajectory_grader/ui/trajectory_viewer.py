import streamlit as st
from core.data_models import Trajectory

STATUS_COLORS = {
    "SUCCESS": ("✅", "#2ecc71"),
    "CALLER_ERROR": ("❌", "#e74c3c"),
    "SYSTEM_ERROR": ("⚠️", "#f39c12"),
    "TIMEOUT": ("⏱️", "#95a5a6"),
}


def render_trajectory_viewer(trajectory: Trajectory):
    st.subheader("轨迹步骤回放")

    # 用户 Query
    st.markdown(
        f"<div style='background:#f0f4ff;border-left:4px solid #3498db;padding:12px;border-radius:6px'>"
        f"👤 <b>用户 Query</b><br>{trajectory.user_query}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    returned_ids = trajectory.get_all_returned_product_ids()

    for step in trajectory.steps:
        if step.step_type == "tool_call":
            tool_status = "SUCCESS"
            if step.error_type:
                tool_status = step.error_type
            elif step.tool_output:
                tool_status = step.tool_output.status

            icon, color = STATUS_COLORS.get(tool_status, ("🔧", "#888"))
            product_count = len(step.tool_output.products) if step.tool_output else 0

            with st.expander(
                f"Step {step.step_id} · 🔧 工具调用: `{step.tool_name}` · {icon} {tool_status}"
                + (f" · 返回 {product_count} 个商品" if product_count else ""),
                expanded=(tool_status in ("CALLER_ERROR",)),
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**输入参数**")
                    st.json(step.tool_input or {})
                with col2:
                    st.markdown("**工具返回**")
                    if step.tool_output:
                        if step.tool_output.products:
                            for p in step.tool_output.products:
                                st.markdown(
                                    f"- `{p.product_id}` **{p.title}** — ¥{p.price}"
                                    + (" ⭐京东自营" if p.is_jd_self else "")
                                )
                        else:
                            st.json({"status": step.tool_output.status})
                    if step.error_type:
                        st.error(f"错误类型：{step.error_type}")

        elif step.step_type == "final_response":
            st.markdown(
                f"<div style='background:#f0fff4;border-left:4px solid #2ecc71;padding:12px;border-radius:6px'>"
                f"💬 <b>Step {step.step_id} · 最终回复</b></div>",
                unsafe_allow_html=True,
            )
            st.markdown(step.content or trajectory.final_response)

            if step.product_cards:
                st.markdown("**商品卡片**")
                for card in step.product_cards:
                    is_valid = card.card_id in returned_ids
                    validity = "✅ ID 合法" if is_valid else "❌ **幻觉 ID（未出现在工具返回中）**"
                    bg = "#f0fff4" if is_valid else "#fff0f0"
                    st.markdown(
                        f"<div style='background:{bg};padding:8px;border-radius:6px;margin:4px 0'>"
                        f"🛒 <code>{card.card_id}</code> · ¥{card.display_price} · {validity}"
                        f"<br><small>{card.reason}</small></div>",
                        unsafe_allow_html=True,
                    )

        elif step.step_type == "llm_reasoning":
            with st.expander(f"Step {step.step_id} · 🧠 推理过程"):
                st.markdown(step.content or "（无内容）")
