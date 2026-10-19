import json
from pathlib import Path
from typing import Optional
import streamlit as st
from core.data_models import Trajectory

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
SAMPLES = {
    "📗 好案例（全维度高分）": "good_case.json",
    "📕 Gate1 失败（需求理解 FAIL）": "bad_gate1.json",
    "📕 Gate2 失败（回应不完整）": "bad_gate2.json",
    "⚠️ 价格幻觉（card_id 伪造）": "edge_hallucination.json",
}


def render_trajectory_input() -> Optional[Trajectory]:
    """渲染轨迹输入区，返回解析好的 Trajectory 或 None。"""
    st.subheader("输入 Agent 执行轨迹")

    input_mode = st.radio(
        "输入方式",
        ["粘贴 JSON", "上传文件"],
        horizontal=True,
        label_visibility="collapsed",
    )

    json_text = ""
    if input_mode == "粘贴 JSON":
        json_text = st.text_area(
            "JSON 轨迹",
            height=380,
            placeholder='粘贴 Trajectory JSON，或从左侧侧边栏加载示例...',
            key="json_input",
            value=st.session_state.get("loaded_json", ""),
        )
    else:
        uploaded = st.file_uploader("上传 JSON 文件", type=["json"])
        if uploaded:
            json_text = uploaded.read().decode("utf-8")

    # 预览统计
    if json_text.strip():
        try:
            raw = json.loads(json_text)
            traj = Trajectory(**raw)
            tool_calls = traj.get_tool_call_steps()
            card_ids = traj.get_all_card_ids()
            returned_ids = traj.get_all_returned_product_ids()

            cols = st.columns(4)
            cols[0].metric("步骤总数", len(traj.steps))
            cols[1].metric("工具调用", len(tool_calls))
            cols[2].metric("商品卡片", len(card_ids))
            cols[3].metric("有无 CALLER_ERROR", "⚠️ 有" if traj.has_caller_errors() else "✅ 无")

            st.caption(f"trajectory_id: `{traj.trajectory_id}`  |  用户 Query: **{traj.user_query}**")

            if st.button("🚀 开始评分", type="primary", use_container_width=True):
                st.session_state["current_trajectory"] = traj
                st.session_state["active_tab"] = 1
                st.rerun()

        except (json.JSONDecodeError, Exception) as e:
            st.error(f"JSON 解析失败：{e}")
            return None

    return None


def render_sample_sidebar():
    """侧边栏示例加载按钮。"""
    st.sidebar.markdown("### 示例轨迹快速加载")
    for label, filename in SAMPLES.items():
        if st.sidebar.button(label, use_container_width=True):
            path = SAMPLE_DIR / filename
            content = path.read_text(encoding="utf-8")
            st.session_state["loaded_json"] = content
            st.session_state["active_tab"] = 0
            st.rerun()
