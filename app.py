import streamlit as st
import json
import os
import pandas as pd

DATA_FILE = 'voting_data.json'

# ================= 核心数据操作 =================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data.get("allowed_users"), list):
                data["allowed_users"] = {}
            for k, v in list(data.get("allowed_users", {}).items()):
                if isinstance(v, str):
                    data["allowed_users"][k] = {"name": "未知", "pwd": v}
            if "admin_pwd" not in data:
                data["admin_pwd"] = "uestc2204"
            return data
    return {"roles": {}, "allowed_users": {}, "user_progress": {}, "admin_pwd": "uestc2204"}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="班委竞选系统", page_icon="🗳️", layout="centered")
data = load_data()

# ================= 状态管理 =================
if "page_mode" not in st.session_state:
    st.session_state.page_mode = None  # None, 'student', 'guide'
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "guide_logged_in" not in st.session_state:
    st.session_state.guide_logged_in = False

# ================= 导航路由 (首页入口) =================
if st.session_state.page_mode is None:
    st.title("🗳️ 班委换届竞选系统")
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 20px; border-radius: 10px; background-color: #f0f2f6;">
            <h3>🎓 学生通道</h3>
            <p>进行身份核验并参与投票</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入学生端", use_container_width=True):
            st.session_state.page_mode = "student"
            st.rerun()
            
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 20px; border-radius: 10px; background-color: #f0f2f6;">
            <h3>👨‍🏫 导生/管理通道</h3>
            <p>现场投屏展示与后台配置</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入导生端", use_container_width=True):
            st.session_state.page_mode = "guide"
            st.rerun()

# ================= 模式 1：学生端 =================
elif st.session_state.page_mode == "student":
    st.button("⬅️ 返回首页", on_click=lambda: st.session_state.update(page_mode=None, current_user=None))
    st.title("🎓 学生投票通道")
    
    if not st.session_state.current_user:
        with st.form("login_form"):
            sid = st.text_input("请输入账号：", placeholder="输入学号")
            pwd = st.text_input("请输入密码：", type="password")
            submit_login = st.form_submit_button("验证身份并登录")
            
            if submit_login:
                if not sid or not pwd:
                    st.warning("账号和密码不能为空。")
                elif not data["allowed_users"]:
                    st.info("🕒 导生尚未录入班级名单。")
                elif sid not in data["allowed_users"]:
                    st.error("⚠️ 该账号不在本次投票名单中！")
                elif str(data["allowed_users"][sid]["pwd"]) != str(pwd).strip():
                    st.error("❌ 密码验证失败。")
                else:
                    st.session_state.current_user = sid
                    if sid not in data["user_progress"]:
                        data["user_progress"][sid] = []
                        save_data(data)
                    st.rerun()
    else:
        sid = st.session_state.current_user
        student_name = data["allowed_users"][sid].get("name", "同学")
        st.success(f"欢迎你，{student_name}（账号：{sid}）！")
        
        with st.expander("🔐 修改我的密码"):
            new_pwd = st.text_input("新密码：", type="password", key="u_pwd1")
            confirm_pwd = st.text_input("确认密码：", type="password", key="u_pwd2")
            if st.button("确认修改"):
                if new_pwd and new_pwd == confirm_pwd:
                    data["allowed_users"][sid]["pwd"] = new_pwd
                    save_data(data)
                    st.success("✅ 修改成功！")
                elif new_pwd != confirm_pwd:
                    st.error("❌ 密码不一致！")
        
        all_roles = list(data["roles"].keys())
        voted_roles = data["user_progress"].get(sid, [])
        unvoted_roles = [r for r in all_roles if r not in voted_roles]
        
        st.markdown("---")
        if not all_roles:
            st.info("🕒 导生尚未配置竞选岗位...")
        elif not unvoted_roles:
            st.balloons()
            st.success("🎉 你已完成所有投票！")
        else:
            current_role = unvoted_roles[0]
            if "just_voted_role" in st.session_state and st.session_state.just_voted_role == current_role:
                st.subheader(f"✅ 【{current_role}】投票成功")
                if st.button("继续进入下一环节"):
                    data["user_progress"][sid].append(current_role)
                    save_data(data)
                    del st.session_state.just_voted_role
                    st.rerun()
            else:
                st.subheader(f"竞选环节：【{current_role}】")
                candidates = list(data["roles"][current_role].keys())
                if candidates:
                    with st.form("vote_form"):
                        chosen = st.radio(f"请选择一位支持的同学：", candidates)
                        if st.form_submit_button(f"确认提交"):
                            data["roles"][current_role][chosen] += 1
                            save_data(data)
                            st.session_state.just_voted_role = current_role
                            st.rerun()
                else:
                    st.warning("暂无报名。")
                    if st.button("跳过"):
                        data["user_progress"][sid].append(current_role)
                        save_data(data)
                        st.rerun()

# ================= 模式 2：导生管理端 =================
elif st.session_state.page_mode == "guide":
    st.button("⬅️ 退出管理并返回", on_click=lambda: st.session_state.update(page_mode=None, guide_logged_in=False))
    
    if not st.session_state.guide_logged_in:
        st.title("👨‍🏫 导生身份验证")
        guide_pwd = st.text_input("请输入管理控制密码", type="password")
        if st.button("登入管理中心"):
            if guide_pwd == data.get("admin_pwd", "uestc2204"):
                st.session_state.guide_logged_in = True
                st.rerun()
            else:
                st.error("密码错误")
    else:
        st.title("👨‍🏫 导生管理控制中心")
        tab_display, tab_config = st.tabs(["📺 现场大屏展示", "⚙️ 后台数据配置"])
        
        # --- 导生专区：现场大屏渲染 ---
        with tab_display:
            st.markdown("### 📊 实时竞选战况")
            st.caption("💡 提示：在班会现场投屏此页面。点击右上角 🔄 按钮或按 'R' 键可手动刷新最新票数。")
            
            if not data["roles"]:
                st.info("尚未配置职位数据。")
            
            for role, candidates in data["roles"].items():
                st.markdown(f"#### 🏆 {role}")
                if candidates:
                    # 使用 st.bar_chart 渲染柱状图，并在上方展示票数最高的人
                    st.bar_chart(candidates, height=250)
                else:
                    st.write("暂无候选人数据")
                st.markdown("---")
                
        # --- 导生专区：底层配置面板 ---
        with tab_config:
            sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs(["📝 职位与人员", "📂 名单管理", "💾 备份导出", "🔒 密码修改"])
            
            with sub_t1:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**1. 新增职位**")
                    new_role = st.text_input("职位名称")
                    if st.button("新建"):
                        if new_role and new_role not in data["roles"]:
                            data["roles"][new_role] = {}
                            save_data(data)
                            st.rerun()
                with col2:
                    st.markdown("**2. 添加候选人**")
                    if data["roles"]:
                        target_role = st.selectbox("选择职位", list(data["roles"].keys()))
                        new_cand = st.text_input("姓名")
                        if st.button("添加"):
                            if new_cand and new_cand not in data["roles"][target_role]:
                                data["roles"][target_role][new_cand] = 0
                                save_data(data)
                                st.rerun()
                                
            with sub_t2:
                st.markdown("#### 👤 手动添加单人")
                c1, c2, c3 = st.columns(3)
                single_name = c1.text_input("名字", key="sn")
                single_account = c2.text_input("账号", key="sa")
                single_pwd = c3.text_input("密码", key="sp")
                if st.button("保存单个账号"):
                    if single_name and single_account and single_pwd:
                        data["allowed_users"][single_account] = {"name": single_name, "pwd": single_pwd}
                        save_data(data)
                        st.success("已保存！")
                        
                st.markdown("#### 📁 Excel 批量导入 (表头: 名字, 账号, 密码)")
                uploaded_file = st.file_uploader("上传 .xlsx", type=["xlsx", "xls"])
                if uploaded_file is not None and st.button("开始导入"):
                    df = pd.read_excel(uploaded_file)
                    if all(col in df.columns for col in ["名字", "账号", "密码"]):
                        df = df.dropna(subset=['名字', '账号', '密码'])
                        for _, row in df.iterrows():
                            acc = str(row["账号"]).split('.')[0].strip()
                            data["allowed_users"][acc] = {
                                "name": str(row["名字"]).strip(),
                                "pwd": str(row["密码"]).split('.')[0].strip()
                            }
                        save_data(data)
                        st.success("批量导入成功！")
            
            with sub_t3:
                with open(DATA_FILE, "rb") as file:
                    st.download_button("⬇️ 下载全量数据包 (JSON)", file, "voting_backup.json", "application/json")
            
            with sub_t4:
                new_admin_pwd = st.text_input("新导生密码", type="password")
                if st.button("确认修改") and new_admin_pwd:
                    data["admin_pwd"] = new_admin_pwd
                    save_data(data)
                    st.success("密码已更新！")
