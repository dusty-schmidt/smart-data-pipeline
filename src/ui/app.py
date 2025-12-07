"""
Smart Data Pipeline - Control Center Dashboard

Streamlit UI for monitoring and controlling the autonomous pipeline.
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Hack to find local modules: Add root directory to path
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from src.core.plugins import PluginRegistry
from src.core.mcp import MCPManager
from src.orchestration import Orchestrator, TaskQueue, HealthTracker, SourceState

# Database Connection
DB_PATH = os.getenv("PIPELINE_DB_PATH", "data/pipeline.db")
DB_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DB_URL)

# Page Config
st.set_page_config(
    page_title="Smart Data Pipeline", 
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for status colors
st.markdown("""
<style>
    .status-active { color: #00c853; font-weight: bold; }
    .status-degraded { color: #ffab00; font-weight: bold; }
    .status-quarantined { color: #ff5722; font-weight: bold; }
    .status-dead { color: #d32f2f; font-weight: bold; }
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Smart Data Pipeline")
st.caption("Autonomous data ingestion with self-healing capabilities")

# Initialize components
@st.cache_resource
def get_orchestrator():
    return Orchestrator(DB_PATH)

orch = get_orchestrator()

# Tabs
tabs = st.tabs([
    "📊 Health Dashboard", 
    "📋 Task Queue", 
    "🩺 Fix History",
    "💾 Data Browser", 
    "🧩 Registry", 
    "🛠 Tools"
])

# === TAB 1: HEALTH DASHBOARD ===
with tabs[0]:
    st.header("Source Health Monitor")
    
    # Refresh button
    if st.button("🔄 Refresh", key="refresh_health"):
        st.cache_resource.clear()
        st.rerun()
    
    # Get status
    status = orch.status()
    
    # Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Sources", status['total_sources'])
    col2.metric("✅ Active", status['healthy'], delta=None)
    col3.metric("⚠️ Degraded", status['degraded'], delta=None, delta_color="inverse")
    col4.metric("🔒 Quarantined", status['quarantined'], delta=None, delta_color="inverse")
    col5.metric("💀 Dead", status['dead'], delta=None, delta_color="inverse")
    
    st.divider()
    
    # Source Health Table
    if status['sources']:
        st.subheader("Source Status")
        
        # Build dataframe
        health_data = []
        for s in status['sources']:
            state = s['state']
            icon = {'ACTIVE': '✅', 'DEGRADED': '⚠️', 'QUARANTINED': '🔒', 'DEAD': '💀'}.get(state, '❓')
            health_data.append({
                'Status': f"{icon} {state}",
                'Source': s['name'],
                'Failures': s['failures'],
                'Last Success': s['last_success'][:16] if s['last_success'] else 'Never',
            })
        
        df = pd.DataFrame(health_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Detailed view for selected source
        st.subheader("Source Details")
        source_names = [s['name'] for s in status['sources']]
        selected = st.selectbox("Select source", source_names)
        
        if selected:
            health = orch.health_tracker.get_health(selected)
            if health:
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**State:**", health.state.value)
                    st.write("**Success Count:**", health.success_count)
                    st.write("**Failure Count:**", health.failure_count)
                    st.write("**Consecutive Failures:**", health.consecutive_failures)
                with col2:
                    st.write("**Fix Attempts Today:**", health.fix_attempts_today)
                    st.write("**Last Success:**", health.last_success_at or "Never")
                    st.write("**Last Failure:**", health.last_failure_at or "Never")
                    if health.quarantine_until:
                        st.write("**Quarantine Until:**", health.quarantine_until)
                
                if health.last_error:
                    st.error(f"**Last Error:** {health.last_error[:500]}")
                
                # Actions
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🔧 Force Repair", key=f"fix_{selected}"):
                        task = orch.fix_source(selected)
                        st.success(f"Queued repair task [{task.task_id}]")
                        st.rerun()
                with col2:
                    if st.button("▶️ Refresh Data", key=f"refresh_{selected}"):
                        task = orch.refresh_source(selected)
                        st.success(f"Queued refresh task [{task.task_id}]")
                with col3:
                    if health.state == SourceState.QUARANTINED:
                        if st.button("🔓 Release from Quarantine", key=f"release_{selected}"):
                            # Reset to degraded
                            session = orch.health_tracker.Session()
                            from src.storage.models import SourceHealthRecord
                            record = session.query(SourceHealthRecord).filter(
                                SourceHealthRecord.source_name == selected
                            ).first()
                            if record:
                                record.state = 'DEGRADED'
                                record.quarantine_until = None
                                session.commit()
                            session.close()
                            st.success("Released from quarantine")
                            st.rerun()
    else:
        st.info("No sources registered yet. Use the CLI to add sources:")
        st.code("python -m src add 'https://example.com/data'")
    
    # Storage Stats
    st.divider()
    st.subheader("Storage Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Bronze Layer (Raw)**")
        try:
            count = pd.read_sql("SELECT count(*) as cnt FROM bronze_logs", engine).iloc[0]['cnt']
            st.metric("Raw Records", count)
        except:
            st.metric("Raw Records", 0)
    
    with col2:
        st.write("**Silver Layer (Refined)**")
        try:
            count = pd.read_sql("SELECT count(*) as cnt FROM silver_entities", engine).iloc[0]['cnt']
            st.metric("Entities", count)
        except:
            st.metric("Entities", 0)


# === TAB 2: TASK QUEUE ===
with tabs[1]:
    st.header("Task Queue")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", key="refresh_tasks"):
            st.rerun()
    
    # Pending count
    pending = orch.task_queue.get_pending_count()
    st.metric("Pending Tasks", pending)
    
    # Task list
    try:
        tasks_df = pd.read_sql("""
            SELECT 
                id as ID,
                task_type as Type,
                state as State,
                target as Target,
                priority as Priority,
                created_at as Created,
                error_message as Error
            FROM task_queue 
            ORDER BY created_at DESC 
            LIMIT 50
        """, engine)
        
        if not tasks_df.empty:
            # Color-code states
            def style_state(val):
                colors = {
                    'PENDING': 'background-color: #fff3cd',
                    'IN_PROGRESS': 'background-color: #cce5ff',
                    'COMPLETED': 'background-color: #d4edda',
                    'FAILED': 'background-color: #f8d7da',
                }
                return colors.get(val, '')
            
            st.dataframe(
                tasks_df.style.applymap(style_state, subset=['State']),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No tasks in queue")
    except Exception as e:
        st.warning(f"Task queue table not found: {e}")
    
    # Add new source
    st.divider()
    st.subheader("Add New Source")
    
    with st.form("add_source"):
        url = st.text_input("URL to analyze", placeholder="https://example.com/data")
        priority = st.slider("Priority", 1, 10, 5)
        process_now = st.checkbox("Process immediately")
        
        if st.form_submit_button("🚀 Add Source"):
            if url:
                task = orch.add_source(url, priority)
                st.success(f"Task queued: [{task.task_id}] ADD_SOURCE → {url}")
                
                if process_now:
                    with st.spinner("Processing..."):
                        orch.startup()
                        orch.process_task(task)
                    st.success("Processing complete!")
                st.rerun()
            else:
                st.error("Please enter a URL")


# === TAB 3: FIX HISTORY ===
with tabs[2]:
    st.header("Fix History (Doctor Audit Log)")
    
    try:
        fixes_df = pd.read_sql("""
            SELECT 
                id as ID,
                source_name as Source,
                error_type as "Error Type",
                root_cause as "Root Cause",
                success as Success,
                created_at as Timestamp
            FROM fix_history 
            ORDER BY created_at DESC 
            LIMIT 50
        """, engine)
        
        if not fixes_df.empty:
            # Summary metrics
            total = len(fixes_df)
            successful = fixes_df['Success'].sum()
            rate = (successful / total * 100) if total > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Fix Attempts", total)
            col2.metric("Successful Fixes", int(successful))
            col3.metric("Success Rate", f"{rate:.0f}%")
            
            st.divider()
            
            # History table
            st.dataframe(fixes_df, use_container_width=True, hide_index=True)
            
            # Detailed view
            st.subheader("Fix Details")
            fix_id = st.selectbox("Select fix to view details", fixes_df['ID'].tolist())
            
            if fix_id:
                detail = pd.read_sql(f"SELECT * FROM fix_history WHERE id = {fix_id}", engine)
                if not detail.empty:
                    row = detail.iloc[0]
                    st.write("**Source:**", row['source_name'])
                    st.write("**Error Type:**", row['error_type'])
                    st.write("**Success:**", "✅ Yes" if row['success'] else "❌ No")
                    
                    if row.get('error_message'):
                        st.error(f"**Error:** {row['error_message'][:500]}")
                    
                    if row.get('root_cause'):
                        st.info(f"**Root Cause:** {row['root_cause']}")
                    
                    if row.get('patch_applied'):
                        with st.expander("View Applied Patch"):
                            st.code(row['patch_applied'][:3000], language='python')
        else:
            st.info("No fix attempts recorded yet")
    except Exception as e:
        st.warning(f"Fix history table not found: {e}")


# === TAB 4: DATA BROWSER ===
with tabs[3]:
    st.header("Data Browser")
    
    sub_tabs = st.tabs(["Silver (Refined)", "Bronze (Raw)"])
    
    with sub_tabs[0]:
        try:
            sources = pd.read_sql("SELECT DISTINCT source FROM silver_entities", engine)['source'].tolist()
            types = pd.read_sql("SELECT DISTINCT type FROM silver_entities", engine)['type'].tolist()
            
            col1, col2 = st.columns(2)
            selected_source = col1.selectbox("Filter by Source", ["All"] + sources)
            selected_type = col2.selectbox("Filter by Type", ["All"] + types)
            
            query = "SELECT * FROM silver_entities WHERE 1=1"
            if selected_source != "All":
                query += f" AND source = '{selected_source}'"
            if selected_type != "All":
                query += f" AND type = '{selected_type}'"
            query += " ORDER BY updated_at DESC LIMIT 100"
            
            df = pd.read_sql(query, engine)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.info("No silver data found")
    
    with sub_tabs[1]:
        try:
            df = pd.read_sql("""
                SELECT id, source, ingested_at, version 
                FROM bronze_logs 
                ORDER BY ingested_at DESC 
                LIMIT 50
            """, engine)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except:
            st.info("No bronze data found")


# === TAB 5: REGISTRY ===
with tabs[4]:
    st.header("Parser Registry")
    
    registry = PluginRegistry()
    registry.discover_parsers()
    
    parsers = registry.parsers
    st.success(f"Loaded {len(parsers)} Parsers")
    
    for name, cls in parsers.items():
        with st.expander(f"📦 {name}"):
            st.code(cls.__module__)
            st.text(cls.__doc__ or "No documentation")
    
    # Staging directory
    st.divider()
    st.subheader("Staging Registry")
    staging_path = "src/registry/staging"
    if os.path.exists(staging_path):
        staged_files = [f for f in os.listdir(staging_path) if f.endswith('.py') and f != '__init__.py']
        if staged_files:
            st.warning(f"{len(staged_files)} patches in staging")
            for f in staged_files:
                st.write(f"📝 {f}")
        else:
            st.info("No patches in staging")
    else:
        st.info("Staging directory not found")


# === TAB 6: TOOLS ===
with tabs[5]:
    st.header("System Tools")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("MCP Servers")
        manager = MCPManager()
        servers = manager.list_servers()
        st.json(servers)
    
    with col2:
        st.subheader("Configuration")
        from src.core.config import llm_config, pipeline_config
        
        cfg = llm_config()
        st.write("**LLM Provider:**", cfg.provider)
        st.write("**LLM Model:**", cfg.model)
        st.write("**Timeout:**", f"{cfg.timeout_seconds}s")
        
        pcfg = pipeline_config()
        st.write("**Database:**", pcfg.db_path)
        st.write("**Max Fix Attempts:**", pcfg.max_fix_attempts_per_day)
        st.write("**Quarantine Threshold:**", pcfg.quarantine_threshold)
    
    st.divider()
    st.subheader("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Run Orchestrator Once"):
            with st.spinner("Processing one task..."):
                orch.startup()
                task = orch.process_queue()
                if task:
                    st.success(f"Processed: [{task.task_id}] {task.task_type.value}")
                else:
                    st.info("Queue empty")
    
    with col2:
        if st.button("🧹 Cleanup Stale Tasks"):
            count = orch.task_queue.cleanup_stale_tasks()
            st.success(f"Cleaned up {count} stale tasks")
    
    with col3:
        if st.button("🔍 Check Degraded Sources"):
            count = orch.check_health_and_queue_fixes()
            st.success(f"Queued {count} fix tasks")


# Footer
st.divider()
st.caption("Smart Data Pipeline v1.0 | Tier 2: Autonomy Kernel")
