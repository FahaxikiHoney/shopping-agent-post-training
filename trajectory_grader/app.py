import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import config
from core.grader_engine import GraderEngine
from llm.mock_judge import MockJudge
from ui.trajectory_input import render_trajectory_input, render_sample_sidebar
from ui.score_display import render_score_display
from ui.trajectory_viewer import render_trajectory_viewer

st.set_page_config(
    page_title="oxygen-jingyan 评估系统",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 侧边栏配置 ─────────────────────────────────────────────────────
st.sidebar.title("🛒 评估系统配置")

judge_mode = st.sidebar.selectbox(
    "Judge 模式",
    options=["mock_scenario", "mock_random", "mock_fixed"],
    format_func=lambda x: {
        "mock_scenario": "🎭 Mock·场景感知（推荐）",
        "mock_random": "🎲 Mock·随机",
        "mock_fixed": "📌 Mock·固定高分",
    }[x],
    index=0,
)

st.sidebar.divider()
st.sidebar.markdown("### 权重调节（高级）")
w_d2 = st.sidebar.slider("D2 真实性权重", 0.0, 0.40, config.DIMENSION_WEIGHTS["d2_factuality"], 0.01)
w_d3 = st.sidebar.slider("D3 相关性权重", 0.0, 0.40, config.DIMENSION_WEIGHTS["d3_relevance"], 0.01)
w_d5 = st.sidebar.slider("D5 理由价值感权重", 0.0, 0.30, config.DIMENSION_WEIGHTS["d5_reasoning_value"], 0.01)
st.sidebar.caption(f"基础分(Gate通过): {config.BASE_SCORE_ON_GATE_PASS}  |  满分: {config.BASE_SCORE_ON_GATE_PASS + w_d2 + w_d3 + w_d5:.2f}")

st.sidebar.divider()
render_sample_sidebar()

# 动态覆盖权重
config.DIMENSION_WEIGHTS = {"d2_factuality": w_d2, "d3_relevance": w_d3, "d5_reasoning_value": w_d5}

# ── 初始化 session state ───────────────────────────────────────────
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = 0
if "current_trajectory" not in st.session_state:
    st.session_state["current_trajectory"] = None
if "current_grade_result" not in st.session_state:
    st.session_state["current_grade_result"] = None

# ── 主标题 ─────────────────────────────────────────────────────────
st.title("🛒 trajectory_response_quality_grader")
st.caption("京东 oxygen-jingyan-1.0 评估体系复现 · 5维度打分 + Gate机制 · 侦探查案式轨迹审查")

st.divider()

# ── 3 Tab 布局 ─────────────────────────────────────────────────────
tab0, tab1, tab2 = st.tabs(["📥 输入轨迹", "📊 评分结果", "🔍 轨迹回放"])

with tab0:
    render_trajectory_input()

with tab1:
    traj = st.session_state.get("current_trajectory")
    if traj is None:
        st.info("请先在「输入轨迹」Tab 加载一条轨迹并点击「开始评分」。")
    else:
        # 每次 Tab 切换到这里且有新轨迹时重新评分
        last_traj_id = st.session_state.get("last_graded_id", "")
        last_mode = st.session_state.get("last_judge_mode", "")
        if traj.trajectory_id != last_traj_id or judge_mode != last_mode:
            with st.spinner("正在评分中..."):
                judge = MockJudge(mode=judge_mode)
                engine = GraderEngine(judge)
                result = engine.grade(traj)
                st.session_state["current_grade_result"] = result
                st.session_state["last_graded_id"] = traj.trajectory_id
                st.session_state["last_judge_mode"] = judge_mode

        result = st.session_state.get("current_grade_result")
        if result:
            render_score_display(result)

with tab2:
    traj = st.session_state.get("current_trajectory")
    if traj is None:
        st.info("请先在「输入轨迹」Tab 加载一条轨迹。")
    else:
        render_trajectory_viewer(traj)
