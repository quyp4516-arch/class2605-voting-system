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
            # 兼容旧版本：如果以前的 allowed_users 是列表，将其清空转换为字典
            if isinstance(data.get("allowed_users"), list):
                data["allowed_users"] = {}
            return data
    return {"roles": {}, "allowed_users": {}, "user_progress": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="班委线上竞选", page_icon="🗳️", layout="centered")
data = load_data()

# 初始化用户登录状态
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# ================= 模块 1：用户交互端 =================
st.title("🗳️ 班委线上竞选系统")

# 1. 登录拦截（加入手机号密码验证）
if not st.session_state.current_user:
    st.markdown("请进行身份核验进入投票环节。")
    
    with st.form("login_form"):
        sid = st.text_input("请输入学号（账号）：", placeholder="例如: 20220001")
        pwd = st.text_input("请输入手机号（密码）：", type="password", placeholder="请输入登记的手机号码")
        submit_login = st.form_submit_button("验证身份并登录")
        
        if submit_login:
            if not sid or not pwd:
                st.warning("学号和手机号不能为空。")
            elif not data["allowed_users"]:
                st.info("🕒 管理员尚未导入班级名单，暂不支持登录。")
            elif sid not in data["allowed_users"]:
                st.error("⚠️ 该学号不在本次投票名单中！")
            elif str(data["allowed_users"][sid]) != str(pwd).strip():
                st.error("❌ 密码（手机号）验证失败，请检查是否输入正确。")
            else:
                st.session_state.current_user = sid
                # 记录新用户的进度
                if sid not in data["user_progress"]:
                    data["user_progress"][sid] = []
                    save_data(data)
                st.rerun()
else:
    sid = st.session_state.current_user
    st.success(f"欢迎你，学号：{sid}！")
    
    # 2. 核心逻辑：计算该用户未投票的职位
    all_roles = list(data["roles"].keys())
    voted_roles = data["user_progress"].get(sid, [])
    unvoted_roles = [r for r in all_roles if r not in voted_roles]
    
    st.markdown("---")
    
    if not all_roles:
        st.info("🕒 管理员尚未配置竞选岗位，请稍后再来...")
    
    elif not unvoted_roles:
        # 所有环节完成
        st.balloons()
        st.success("🎉 你已完成所有职位的投票！感谢参与。")
        if st.button("退出登录"):
            st.session_state.current_user = None
            st.rerun()
            
    else:
        # 3. 单环节展示与投票
        current_role = unvoted_roles[0]
        
        # 判断是否刚刚投完票，需要展示图表
        if "just_voted_role" in st.session_state and st.session_state.just_voted_role == current_role:
            st.subheader(f"📊 【{current_role}】实时票数概况")
            st.bar_chart(data["roles"][current_role])
            
            # 点击按钮后，真正将进度向后推进一步
            if st.button("✅ 继续进入下一环节"):
                data["user_progress"][sid].append(current_role)
                save_data(data)
                del st.session_state.just_voted_role
                st.rerun()
        else:
            # 正常的投票界面
            st.subheader(f"当前环节：竞选【{current_role}】")
            candidates = list(data["roles"][current_role].keys())
            
            if candidates:
                with st.form("vote_form"):
                    chosen = st.radio(f"请选择一位支持的同学：", candidates)
                    submit = st.form_submit_button(f"确认提交【{current_role}】选票")
                    
                    if submit:
                        data["roles"][current_role][chosen] += 1
                        save_data(data)
                        st.session_state.just_voted_role = current_role
                        st.rerun()
            else:
                st.warning(f"本职位暂无同学报名。")
                if st.button("跳过此环节"):
                    data["user_progress"][sid].append(current_role)
                    save_data(data)
                    st.rerun()

# ================= 模块 2：管理员超级后台 =================
st.markdown("<br><br><br><br>", unsafe_allow_html=True) 
with st.expander("⚙️ 管理员后台面板"):
    admin_pwd = st.text_input("请输入管理员密码", type="password", key="pwd")
    if admin_pwd == "uestc2204":
        tab1, tab2, tab3 = st.tabs(["📝 职位与候选人", "📂 导入 Excel 名单", "💾 数据备份与图表"])
        
        with tab1:
            st.markdown("#### 添加新职位")
            new_role = st.text_input("职位名称 (如: 班长)")
            if st.button("新建职位"):
                if new_role and new_role not in data["roles"]:
                    data["roles"][new_role] = {}
                    save_data(data)
                    st.success("添加成功！")
                    st.rerun()
                    
            if data["roles"]:
                st.markdown("#### 添加候选人")
                target_role = st.selectbox("选择职位", list(data["roles"].keys()))
                new_cand = st.text_input(f"竞选【{target_role}】的同学姓名")
                if st.button("添加候选人"):
                    if new_cand and new_cand not in data["roles"][target_role]:
                        data["roles"][target_role][new_cand] = 0
                        save_data(data)
                        st.success("添加成功！")
                        st.rerun()
                        
        with tab2:
            st.markdown("#### 📁 一键导入学号与密码")
            st.info("请确保你的 Excel 文件中包含名为 **学号** 和 **手机号** 的两列（表头名字必须一致）。")
            
            uploaded_file = st.file_uploader("上传班级花名册 (.xlsx / .xls)", type=["xlsx", "xls"])
            
            if uploaded_file is not None:
                if st.button("开始解析并导入"):
                    try:
                        # 读取 Excel
                        df = pd.read_excel(uploaded_file)
                        
                        # 检查列名是否存在
                        if "学号" in df.columns and "手机号" in df.columns:
                            # 预处理数据：去除空值，将数字转换为字符串，并去掉可能附带的 '.0'
                            df = df.dropna(subset=['学号', '手机号'])
                            df['学号'] = df['学号'].astype(str).apply(lambda x: x.split('.')[0] if x.endswith('.0') else x).str.strip()
                            df['手机号'] = df['手机号'].astype(str).apply(lambda x: x.split('.')[0] if x.endswith('.0') else x).str.strip()
                            
                            new_users = {}
                            for index, row in df.iterrows():
                                sid_val = row["学号"]
                                pwd_val = row["手机号"]
                                if sid_val and sid_val != "nan":
                                    new_users[sid_val] = pwd_val
                                    
                            data["allowed_users"] = new_users
                            save_data(data)
                            st.success(f"✅ 成功导入 {len(new_users)} 位同学的账号信息！")
                            st.balloons()
                        else:
                            st.error("❌ 格式错误：Excel 中必须包含名为『学号』和『手机号』的列头！")
                    except Exception as e:
                        st.error(f"解析文件时发生错误: {e}")
            
            # 显示当前系统内的账号数
            st.caption(f"当前系统已录入账号数：{len(data.get('allowed_users', {}))} 人")
            
        with tab3:
            st.markdown("#### 所有数据总览与导出")
            for r, c in data["roles"].items():
                st.write(f"**{r}** 票数：")
                if c:
                    st.bar_chart(c)
                else:
                    st.write("无")
            
            st.markdown("---")
            st.markdown("#### 🚨 数据安全备份")
            with open(DATA_FILE, "rb") as file:
                st.download_button(
                    label="⬇️ 下载投票数据包 (voting_data.json)",
                    data=file,
                    file_name="class_voting_data_backup.json",
                    mime="application/json"
                )
    elif admin_pwd:
        st.error("密码错误")
