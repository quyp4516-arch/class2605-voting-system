import streamlit as st
import json
import os
import pandas as pd
import altair as alt  # 新增：引入高级图表库
from streamlit_autorefresh import st_autorefresh

DATA_FILE = 'voting_data.json'

# ================= 核心数据操作 =================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "user_choices" not in data:
                data["user_choices"] = {} 
            for k, v in list(data.get("allowed_users", {}).items()):
                if isinstance(v, str):
                    data["allowed_users"][k] = {"name": "未知", "pwd": v}
            if "admin_pwd" not in data:
                data["admin_pwd"] = "uestc2204"
            return data
    return {"roles": {}, "allowed_users": {}, "user_progress": {}, "user_choices": {}, "admin_pwd": "uestc2204"}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="班委竞选系统", page_icon="🗳️", layout="centered")
data = load_data()

if "page_mode" not in st.session_state:
    st.session_state.page_mode = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "guide_logged_in" not in st.session_state:
    st.session_state.guide_logged_in = False

# ================= 导航路由 (首页) =================
if st.session_state.page_mode is None:
    st.title("🗳️ 班委换届竞选系统")
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div style='text-align:center;padding:20px;background:#f0f2f6;border-radius:10px;'><h3>🎓 学生通道</h3></div>", unsafe_allow_html=True)
        if st.button("进入投票", use_container_width=True):
            st.session_state.page_mode = "student"
            st.rerun()
    with col2:
        st.markdown("<div style='text-align:center;padding:20px;background:#f0f2f6;border-radius:10px;'><h3>👨‍🏫 管理通道</h3></div>", unsafe_allow_html=True)
        if st.button("进入后台", use_container_width=True):
            st.session_state.page_mode = "guide"
            st.rerun()

# ================= 模式 1：学生端 =================
elif st.session_state.page_mode == "student":
    col_back, col_out = st.columns([1, 1])
    with col_back:
        st.button("⬅️ 返回首页", on_click=lambda: st.session_state.update(page_mode=None))
    
    if not st.session_state.current_user:
        st.title("🎓 学生验证")
        with st.form("login_form"):
            sid = st.text_input("账号")
            pwd = st.text_input("密码", type="password")
            if st.form_submit_button("登录"):
                if sid in data.get("allowed_users", {}) and str(data["allowed_users"][sid]["pwd"]) == str(pwd).strip():
                    st.session_state.current_user = sid
                    if sid not in data["user_progress"]:
                        data["user_progress"][sid] = []
                    if sid not in data["user_choices"]:
                        data["user_choices"][sid] = {}
                    save_data(data)
                    st.rerun()
                else:
                    st.error("验证失败，请检查账号密码。")
    else:
        sid = st.session_state.current_user
        with col_out:
            if st.button("🚪 安全注销", use_container_width=True):
                st.session_state.current_user = None
                st.rerun()
                
        name = data["allowed_users"][sid].get("name", "同学")
        st.success(f"欢迎，{name}！")
        
        all_roles = list(data["roles"].keys())
        
        st.markdown("### 📝 我的选票")
        for role in all_roles:
            if role in data["user_progress"].get(sid, []):
                chosen_cand = data["user_choices"].get(sid, {}).get(role, "未知")
                col_role, col_mod = st.columns([3, 1])
                col_role.info(f"**{role}**：已投给 {chosen_cand}")
                if col_mod.button("修改", key=f"mod_{role}"):
                    if chosen_cand in data["roles"][role] and data["roles"][role][chosen_cand] > 0:
                        data["roles"][role][chosen_cand] -= 1
                    data["user_progress"][sid].remove(role)
                    data["user_choices"][sid].pop(role, None)
                    save_data(data)
                    st.rerun()
        
        st.markdown("---")
        unvoted_roles = [r for r in all_roles if r not in data["user_progress"].get(sid, [])]
        if not unvoted_roles:
            st.balloons()
            st.success("所有环节已投票完毕！")
        else:
            current_role = unvoted_roles[0]
            st.subheader(f"竞选环节：【{current_role}】")
            candidates = list(data["roles"][current_role].keys())
            if candidates:
                with st.form(f"vote_{current_role}"):
                    chosen = st.radio("请选择：", candidates)
                    if st.form_submit_button("确认提交"):
                        data["roles"][current_role][chosen] += 1
                        data["user_progress"][sid].append(current_role)
                        data["user_choices"][sid][current_role] = chosen
                        save_data(data)
                        st.rerun()

# ================= 模式 2：导生管理端 =================
elif st.session_state.page_mode == "guide":
    st.button("⬅️ 退出并返回", on_click=lambda: st.session_state.update(page_mode=None, guide_logged_in=False))
    
    if not st.session_state.guide_logged_in:
        st.title("👨‍🏫 管理验证")
        pwd = st.text_input("密码", type="password")
        if st.button("进入") and pwd == data.get("admin_pwd", "uestc2204"):
            st.session_state.guide_logged_in = True
            st.rerun()
    else:
        st.title("👨‍🏫 管理中心")
        
        admin_mode = st.radio(
            "请选择操作模式：", 
            ["📺 大屏实时监控 (开启1秒刷新)", "⚙️ 后台完整配置 (停止刷新，安全操作)"], 
            horizontal=True
        )
        st.markdown("---")
        
        # --- 现场展示大屏 ---
        if admin_mode == "📺 大屏实时监控 (开启1秒刷新)":
            st_autorefresh(interval=1000, key="datarefresh")
            
            if not data["roles"]:
                st.info("尚未配置职位数据，请切换到【后台配置】添加。")
            for role, candidates in data["roles"].items():
                st.markdown(f"#### 🏆 {role}")
                if candidates:
                    # 1. 将数据转为标准的 Pandas 表格
                    df = pd.DataFrame({
                        "姓名": list(candidates.keys()), 
                        "票数": list(candidates.values())
                    })
                    
                    # 2. 构建基础图表框架 (锁定Y轴最小值为0，强制步长为1)
                    base = alt.Chart(df).encode(
                        x=alt.X('姓名:N', title='', axis=alt.Axis(labelAngle=0, labelFontSize=14)),
                        y=alt.Y('票数:Q', title='', axis=alt.Axis(tickMinStep=1, labelFontSize=12), scale=alt.Scale(domainMin=0))
                    ).properties(height=250)
                    
                    # 3. 绘制圆角柱状图
                    bar = base.mark_bar(
                        color='#4C78A8', 
                        cornerRadiusTopLeft=5, 
                        cornerRadiusTopRight=5
                    )
                    
                    # 4. 在柱子上叠加粗体数值
                    text = base.mark_text(
                        align='center',
                        baseline='bottom',
                        dy=-5,  # 将数字向上偏移一点
                        fontSize=18,
                        fontWeight='bold',
                        color='#333333'
                    ).encode(
                        text='票数:Q'
                    )
                    
                    # 5. 合并渲染图表
                    st.altair_chart(bar + text, use_container_width=True)
                else:
                    st.write("暂无候选人")
                    
        # --- 完整恢复的配置后台 ---
        elif admin_mode == "⚙️ 后台完整配置 (停止刷新，安全操作)":
            sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs(["📝 职位与人员", "📂 名单管理", "💾 备份导出", "🔒 密码修改"])
            
            with sub_t1:
                st.markdown("#### 1. 新增数据")
                col_add1, col_add2 = st.columns(2)
                with col_add1:
                    new_role = st.text_input("新增职位名称", key="new_role_input")
                    if st.button("新建职位"):
                        if new_role and new_role not in data["roles"]:
                            data["roles"][new_role] = {}
                            save_data(data)
                            st.success(f"职位【{new_role}】添加成功！")
                            st.rerun()
                with col_add2:
                    if data["roles"]:
                        target_role = st.selectbox("选择要添加候选人的职位", list(data["roles"].keys()), key="target_role_add")
                        new_cand = st.text_input("新增候选人姓名", key="new_cand_input")
                        if st.button("添加候选人"):
                            if new_cand and new_cand not in data["roles"][target_role]:
                                data["roles"][target_role][new_cand] = 0
                                save_data(data)
                                st.success(f"【{new_cand}】已加入候选名单！")
                                st.rerun()

                st.markdown("---")
                st.markdown("#### 2. ✏️ 修改与删除现有数据")
                if data["roles"]:
                    edit_role = st.selectbox("选择需要管理的职位：", list(data["roles"].keys()), key="edit_role")
                    
                    # 职位级别的修改与删除
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        rename_role = st.text_input(f"重命名【{edit_role}】为：", key="rename_role_input")
                        if st.button("确认重命名职位"):
                            if rename_role and rename_role not in data["roles"]:
                                # 转移数据并删除旧名字，保留原有票数
                                data["roles"][rename_role] = data["roles"].pop(edit_role)
                                save_data(data)
                                st.success("职位重命名成功！")
                                st.rerun()
                    with col_r2:
                        st.write("") 
                        st.write("")
                        if st.button(f"🗑️ 彻底删除【{edit_role}】职位", type="primary"):
                            data["roles"].pop(edit_role)
                            save_data(data)
                            st.success("职位已删除！")
                            st.rerun()
                            
                    # 候选人级别的修改与删除
                    candidates_list = list(data["roles"].get(edit_role, {}).keys())
                    if candidates_list:
                        st.markdown(f"**管理【{edit_role}】的候选人：**")
                        edit_cand = st.selectbox("选择要管理的候选人：", candidates_list, key="edit_cand")
                        
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            rename_cand = st.text_input(f"重命名【{edit_cand}】为：", key="rename_cand_input")
                            if st.button("确认重命名候选人"):
                                if rename_cand and rename_cand not in data["roles"][edit_role]:
                                    # 转移票数
                                    votes = data["roles"][edit_role].pop(edit_cand)
                                    data["roles"][edit_role][rename_cand] = votes
                                    save_data(data)
                                    st.success("候选人重命名成功！")
                                    st.rerun()
                        with col_c2:
                            st.write("")
                            st.write("")
                            if st.button(f"🗑️ 删除候选人【{edit_cand}】"):
                                data["roles"][edit_role].pop(edit_cand)
                                save_data(data)
                                st.success("候选人已删除！")
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
                        st.rerun()
            
            with sub_t3:
                st.markdown("#### 🚨 数据下载存档")
                with open(DATA_FILE, "rb") as file:
                    st.download_button("⬇️ 下载全量数据包 (JSON)", file, "voting_backup.json", "application/json")
            
            with sub_t4:
                st.markdown("#### 🔑 修改后台控制密码")
                new_admin_pwd = st.text_input("输入新密码", type="password")
                if st.button("确认修改") and new_admin_pwd:
                    data["admin_pwd"] = new_admin_pwd
                    save_data(data)
                    st.success("密码已更新！下次请使用新密码登入。")
