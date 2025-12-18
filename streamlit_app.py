import streamlit as st
import requests
from datetime import datetime
import time
from dotenv import load_dotenv
load_dotenv()

# ======================================================
# CONFIG
# ======================================================
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="RFP-Optimize AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    .main-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #4f46e5;
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    .rfp-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #28a745;
    }
    .notification-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        color: #212529;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .sidebar-content {
        background: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ======================================================
# SESSION STATE INIT
# ======================================================
if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# ======================================================
# HELPERS
# ======================================================
def parse_error(response):
    try:
        data = response.json()
        return data.get("detail", "Something went wrong")
    except Exception:
        return f"Error {response.status_code}"


def api_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {}

    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    print(f"DEBUG: API Request - {method} {endpoint}")
    if data:
        print(f"DEBUG: Request data: {data}")

    try:
        if method == "GET":
            res = requests.get(url, headers=headers, params=data, timeout=30)
        elif method == "POST":
            res = requests.post(url, headers=headers, json=data, timeout=60)  # Longer for AI analysis
        elif method == "PUT":
            res = requests.put(url, headers=headers, json=data, timeout=30)
        else:
            return None

        print(f"DEBUG: Response status: {res.status_code}")
        if res.status_code < 400:
            print(f"DEBUG: Response data: {res.json() if res.headers.get('content-type', '').startswith('application/json') else res.text[:200]}")
        else:
            print(f"DEBUG: Error response: {res.text}")

        # 🔥 logout only if token is invalid (not login/register)
        if res.status_code == 401 and endpoint not in ["/login", "/register"]:
            st.session_state.token = None
            st.session_state.user = None
            st.warning("Session expired. Please login again.")
            st.rerun()

        return res

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is FastAPI running?")
        print("DEBUG: ConnectionError - Backend not reachable")
    except requests.exceptions.Timeout:
        st.error("Backend timeout")
        print("DEBUG: TimeoutError - Backend took too long to respond")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        print(f"DEBUG: Unexpected error: {e}")

    return None

# ======================================================
# AUTH PAGE
# ======================================================
def auth_page():
    st.markdown('<h1><i class="fas fa-lock"></i> RFP-Optimize AI</h1>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # ---------------- LOGIN ----------------
    with col1:
        st.subheader("Login")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                if not email or not password:
                    st.warning("Email and password required")
                    return

                res = api_request("POST", "/login", {
                    "email": email,
                    "password": password
                })

                if not res:
                    return

                if res.status_code == 200:
                    token_data = res.json()
                    st.session_state.token = token_data["access_token"]
                    st.session_state.user = token_data.get("user", {"email": email, "role": "unknown"})
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error(parse_error(res))

    # ---------------- REGISTER ----------------
    with col2:
        st.subheader("Register")

        with st.form("register_form"):
            r_email = st.text_input("Email", key="r_email")
            r_password = st.text_input("Password", type="password", key="r_password")
            r_role = st.selectbox("Role", ["client", "admin"])
            submit = st.form_submit_button("Register")

            if submit:
                if not r_email or not r_password:
                    st.warning("All fields required")
                    return

                if len(r_password) < 6:
                    st.warning("Password must be at least 6 characters")
                    return
                
                if len(r_password) > 72:
                    st.warning("Password must be less than 72 characters")
                    return

                res = api_request("POST", "/register", {
                    "email": r_email,
                    "password": r_password,
                    "role": r_role
                })

                if not res:
                    return

                if res.status_code == 201:
                    st.success("Registered successfully! Please login.")
                else:
                    st.error(parse_error(res))

# ======================================================
# DASHBOARD
# ======================================================
def dashboard():
    st.sidebar.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    st.sidebar.markdown('<h2><i class="fas fa-rocket"></i> RFP-Optimize AI</h2>', unsafe_allow_html=True)

    user_role = st.session_state.user.get("role", "client")
    user_email = st.session_state.user.get("email", "")

    st.sidebar.markdown(f"**Welcome, {user_email}**")
    st.sidebar.markdown(f"Role: {user_role.title()}")

    # Show different options based on role
    if user_role == "admin":
        navigation_options = ["Dashboard", "Admin Panel"]
    else:
        navigation_options = ["Dashboard", "Create RFP", "Smart RFP Generator", "Demo Requests"]

    page = st.sidebar.radio("Navigation", navigation_options)

    st.sidebar.markdown("---")

    if st.sidebar.button('Logout', use_container_width=True):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()

    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    if page == "Dashboard":
        render_dashboard()
    elif page == "Create RFP" and user_role == "client":
        render_create_rfp()
    elif page == "Smart RFP Generator" and user_role == "client":
        render_ai_rfp_generator() # New function below
    elif page == "Demo Requests" and user_role == "client":
        render_demo_requests()
    elif page == "Admin Panel" and user_role == "admin":
        render_admin_panel()
    elif page == "Smart Chat":
        render_chat()


# ======================================================
# NOTIFICATIONS
# ======================================================
def show_notifications():
    """Display user notifications"""
    try:
        res = api_request("GET", "/notifications")
        if res and res.status_code == 200:
            notifications = res.json()
            if notifications:
                st.subheader("Notifications")
                for notif in notifications[:5]:  # Show latest 5
                    with st.container():
                        st.markdown(f'<div class="notification-card">', unsafe_allow_html=True)
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"**{notif.get('message', '')}**")
                            st.caption(f"Type: {notif.get('type', '')} | {notif.get('created_at', '')[:10]}")
                        with col2:
                            if not notif.get('is_read', False):
                                if st.button("Mark Read", key=f"read_{notif['id']}", help="Mark as read"):
                                    api_request("PUT", f"/notifications/{notif['id']}/read")
                                    st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                if len(notifications) > 5:
                    st.caption(f"And {len(notifications) - 5} more notifications...")
    except:
        pass  # Silently fail if notifications endpoint not available

# ======================================================
# DASHBOARD VIEW
# ======================================================
def render_dashboard():
    st.markdown('<div class="main-header"><h1><i class="fas fa-chart-line"></i> RFP Dashboard</h1><p>AI-Powered RFP Analysis & Optimization</p></div>', unsafe_allow_html=True)

    # Choose endpoint based on user role
    user_role = st.session_state.user.get("role", "client")
    if user_role == "admin":
        endpoint = "/admin/rfps"
    else:
        endpoint = "/rfps"

    # Show notifications for clients
    if user_role == "client":
        show_notifications()

    res = api_request("GET", endpoint)
    if not res or res.status_code != 200:
        st.error("Failed to load RFPs")
        return

    rfps = res.json().get("rfps", [])
    # Sort by latest first
    rfps.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Modern metrics cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>{len(rfps)}</h3><p>Total RFPs</p></div>', unsafe_allow_html=True)
    with col2:
        high_win = len([r for r in rfps if r.get("win_probability", 0) > 70])
        st.markdown(f'<div class="metric-card"><h3>{high_win}</h3><p>High Win Prob (>70%)</p></div>', unsafe_allow_html=True)
    with col3:
        pending = len([r for r in rfps if r.get("agent_status") != "completed"])
        st.markdown(f'<div class="metric-card"><h3>{pending}</h3><p>Pending AI Analysis</p></div>', unsafe_allow_html=True)
    with col4:
        completed = len([r for r in rfps if r.get("agent_status") == "completed"])
        st.markdown(f'<div class="metric-card"><h3>{completed}</h3><p>AI Completed</p></div>', unsafe_allow_html=True)

    # Admin controls
    if user_role == "admin":
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Start AI Engine on All Pending RFPs", type="primary", use_container_width=True):
                with st.spinner("Starting AI engine..."):
                    res = api_request("POST", "/admin/start-ai-engine")
                    if res and res.status_code == 200:
                        st.success("AI engine started! Check progress below.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Failed to start AI engine")

    st.markdown("---")

    # Classify RFPs
    accepted_rfps = [r for r in rfps if r.get("agent_status") == "completed" and not r.get("recommendation", "").startswith("REJECT")]
    rejected_rfps = [r for r in rfps if r.get("agent_status") == "completed" and r.get("recommendation", "").startswith("REJECT")]
    pending_rfps = [r for r in rfps if r.get("agent_status") != "completed"]
    accepted_after_demo_rfps = [r for r in rfps if r.get("demo_status") == "accepted"]

    tabs = st.tabs(["All RFPs", "Accepted RFPs", "Rejected RFPs", "Pending Analysis", "Accepted After Demo"])

    def render_rfp_list(rfp_list, key_prefix=""):
        for rfp in rfp_list:
            with st.expander(f"{rfp['title']}", expanded=False):
                st.markdown(f'<div class="rfp-card">', unsafe_allow_html=True)

                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write(f"**Description:** {rfp.get('description', 'No description')[:200]}...")
                    st.caption(f"Due: {rfp.get('due_date', 'Not set')}")
                    st.caption(f"Budget: ${rfp.get('approximate_budget', 0):,.0f}")

                    # Status with icons
                    status = rfp.get("agent_status", "idle")
                    if status == "completed":
                        st.success("AI Analysis Completed")
                    elif status == "processing":
                        st.warning("AI Processing...")
                    else:
                        if st.button("Run AI Analysis", key=f"{key_prefix}ai_{rfp['_id']}", help="Start AI analysis for this RFP"):
                            with st.spinner("Running AI analysis..."):
                                res = api_request("POST", f"/rfps/{rfp['_id']}/analyze")
                                if res and res.status_code == 200:
                                    st.success("AI analysis started!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Failed to start AI analysis")

                with col2:
                    wp = max(0, min(100, rfp.get("win_probability", 0)))
                    st.metric("Win Probability", f"{wp}%")
                    st.progress(wp / 100, text=f"{wp}%")

                with col3:
                    sm = rfp.get("spec_match_score", 0)
                    st.metric("Spec Match", f"{sm:.1f}%")
                    st.progress(sm / 100, text=f"{sm:.1f}%")

                # Show AI recommendations and suggestions if analysis is complete
                if rfp.get("agent_status") == "completed" and rfp.get("recommendation"):
                    st.divider()
                    rec_col1, rec_col2 = st.columns(2)

                    with rec_col1:
                        recommendation = rfp.get("recommendation", "")
                        if "SELECT" in recommendation.upper():
                            st.success(f"**{recommendation}**")
                        elif "CONSIDER" in recommendation.upper():
                            st.info(f"**{recommendation}**")
                        elif "REVIEW" in recommendation.upper():
                            st.warning(f"**{recommendation}**")
                        else:
                            st.error(f"**{recommendation}**")

                        reason = rfp.get("recommendation_reason", "")
                        if reason:
                            st.caption(reason)

                    with rec_col2:
                        suggestions = rfp.get("suggestions", [])
                        if suggestions:
                            st.subheader("AI Suggestions")
                            for suggestion in suggestions:
                                st.markdown(f"• {suggestion}")

                    # Demo/Sample Options for accepted RFPs
                    if user_role == "client" and rfp.get("recommendation", "").startswith(("SELECT", "CONSIDER")):
                        st.divider()
                        demo_status = rfp.get("demo_status", "none")

                        if demo_status == "none":
                            st.subheader("🎯 Pre-Deal Demo/Sample")
                            st.caption("Request a demo or sample to evaluate our products before finalizing")

                            # Use session state to persist form visibility
                            form_key = f"show_demo_form_{rfp['_id']}"
                            if form_key not in st.session_state:
                                st.session_state[form_key] = False

                            if st.button("Request Demo/Sample", key=f"{key_prefix}demo_{rfp['_id']}", help="Request a product demo or sample"):
                                st.session_state[form_key] = True
                                st.rerun()

                            if st.session_state[form_key]:
                                # Get demo centers
                                centers_res = api_request("GET", "/demo-centers")
                                if centers_res and centers_res.status_code == 200:
                                    centers = centers_res.json()
                                    if centers:
                                        # Show form directly
                                        st.subheader("📝 Demo Request Form")
                                        with st.form(f"{key_prefix}demo_form_{rfp['_id']}"):
                                            preferred_location = st.selectbox(
                                                "Preferred Demo Center",
                                                [f"{c['name']} - {c['location']}" for c in centers]
                                            )
                                            preferred_date = st.date_input("Preferred Date")
                                            special_requirements = st.text_area("Special Requirements (optional)")

                                            col1, col2 = st.columns(2)
                                            with col1:
                                                if st.form_submit_button("Submit Demo Request"):
                                                    # Extract center name
                                                    center_name = preferred_location.split(" - ")[0]
                                                    demo_data = {
                                                        "preferred_location": center_name,
                                                        "preferred_date": datetime.combine(
                                                            preferred_date, datetime.min.time()
                                                        ).isoformat() if preferred_date else None,
                                                        "special_requirements": special_requirements
                                                    }
                                                    res = api_request("POST", f"/rfps/{rfp['_id']}/request-demo", demo_data)
                                                    if res and res.status_code == 200:
                                                        st.success("Demo request submitted! You will be notified when scheduled.")
                                                        st.session_state[form_key] = False  # Hide form after success
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        error_msg = parse_error(res) if res else "Network error"
                                                        st.error(f"Failed to submit demo request: {error_msg}")
                                            with col2:
                                                if st.form_submit_button("Cancel"):
                                                    st.session_state[form_key] = False
                                                    st.rerun()
                                    else:
                                        st.warning("No demo centers available at the moment. Please contact admin.")
                                        st.session_state[form_key] = False
                                else:
                                    st.error("Unable to load demo centers. Please try again.")
                                    st.session_state[form_key] = False

                        elif demo_status == "requested":
                            st.info("🎯 **Demo Requested** - Waiting for admin scheduling")

                        elif demo_status == "scheduled":
                            st.success("🎯 **Demo Scheduled** - Check your notifications for details")
                            # Show decision buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Accept After Demo", key=f"{key_prefix}accept_{rfp['_id']}", help="Accept the RFP after demo"):
                                    with st.spinner("Updating decision..."):
                                        feedback = st.text_input("Feedback (optional)", key=f"feedback_accept_{rfp['_id']}")
                                        res = api_request("PUT", f"/rfps/{rfp['_id']}/decision", {"final_decision": "accept", "feedback": feedback})
                                        if res and res.status_code == 200:
                                            st.success("RFP accepted!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update decision")
                            with col2:
                                if st.button("❌ Reject After Demo", key=f"{key_prefix}reject_{rfp['_id']}", help="Reject the RFP after demo"):
                                    with st.spinner("Updating decision..."):
                                        feedback = st.text_input("Feedback (optional)", key=f"feedback_reject_{rfp['_id']}")
                                        res = api_request("PUT", f"/rfps/{rfp['_id']}/decision", {"final_decision": "reject", "feedback": feedback})
                                        if res and res.status_code == 200:
                                            st.success("RFP rejected.")
                                            st.rerun()
                                        else:
                                            st.error("Failed to update decision")

                        elif demo_status in ["accepted", "rejected"]:
                            status_icon = "✅" if demo_status == "accepted" else "❌"
                            st.markdown(f"{status_icon} **Demo {demo_status.title()}**")

                st.markdown('</div>', unsafe_allow_html=True)

    with tabs[0]:
        render_rfp_list(rfps, "all_")
    with tabs[1]:
        render_rfp_list(accepted_rfps, "accepted_")
    with tabs[2]:
        render_rfp_list(rejected_rfps, "rejected_")
    with tabs[3]:
        render_rfp_list(pending_rfps, "pending_")
    with tabs[4]:
        render_rfp_list(accepted_after_demo_rfps, "accepted_demo_")

# ======================================================
# ADMIN PANEL
# ======================================================
def render_admin_panel():
    st.markdown('<div class="main-header"><h1><i class="fas fa-cog"></i> Admin Panel</h1><p>Manage System Configuration</p></div>', unsafe_allow_html=True)

    tabs = st.tabs(["Qualification Rules", "Product Repository", "Test Repository", "Demo Management", "Cron Jobs"])

    with tabs[0]:
        st.subheader("Qualification Rules (Constraints)")
        render_qualification_rules()

    with tabs[1]:
        st.subheader("Product Pricing Repository")
        render_product_repository()

    with tabs[2]:
        st.subheader("Test Pricing Repository")
        render_test_repository()

    with tabs[3]:
        st.subheader("Demo Management")
        render_demo_management()

    with tabs[4]:
        st.subheader("Automated AI Engine Jobs")
        render_cron_jobs()

def render_qualification_rules():
    # Get existing rules
    res = api_request("GET", "/admin/rules")
    if res and res.status_code == 200:
        rules = res.json()
        for rule in rules:
            with st.expander(f"{rule['name']} ({'Active' if rule['is_active'] else 'Inactive'})"):
                st.write(f"**Description:** {rule.get('description', 'N/A')}")
                st.write(f"**Min Budget:** ${rule.get('min_budget', 0):,.0f}")
                st.write(f"**Max Budget:** ${rule.get('max_budget', 'Unlimited')}")
                st.write(f"**Min Spec Match:** {rule.get('min_spec_match_percent', 0)}%")
                if st.button("Delete", key=f"del_rule_{rule['id']}"):
                    api_request("DELETE", f"/admin/rules/{rule['id']}")
                    st.rerun()

    # Add new rule
    st.markdown("---")
    st.subheader("Add New Qualification Rule")
    with st.form("new_rule"):
        name = st.text_input("Rule Name")
        description = st.text_area("Description")
        min_budget = st.number_input("Min Budget", min_value=0.0)
        max_budget = st.number_input("Max Budget (0 = unlimited)", min_value=0.0)
        min_match = st.slider("Min Spec Match %", 0, 100, 0)
        is_active = st.checkbox("Active", value=True)

        if st.form_submit_button("Add Rule"):
            rule_data = {
                "name": name,
                "description": description,
                "min_budget": min_budget if min_budget > 0 else None,
                "max_budget": max_budget if max_budget > 0 else None,
                "min_spec_match_percent": min_match,
                "is_active": is_active
            }
            res = api_request("POST", "/admin/rules", rule_data)
            if res and res.status_code == 200:
                st.success("Rule added!")
                st.rerun()
            else:
                st.error("Failed to add rule")

def render_product_repository():
    # Get existing products
    res = api_request("GET", "/admin/product-prices")
    if res and res.status_code == 200:
        products = res.json()
        for product in products:
            with st.expander(f"{product['sku_name']} ({product['_id']})"):
                st.write(f"**Price:** ${product['base_unit_price']:,.2f} {product['currency']}")
                if st.button("Delete", key=f"del_prod_{product['_id']}"):
                    api_request("DELETE", f"/admin/product-prices/{product['_id']}")
                    st.rerun()

    # Add new product
    st.markdown("---")
    st.subheader("Add New Product")
    with st.form("new_product"):
        sku_id = st.text_input("SKU ID")
        sku_name = st.text_input("Product Name")
        price = st.number_input("Base Unit Price", min_value=0.0)
        currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])

        if st.form_submit_button("Add Product"):
            product_data = {
                "sku_id": sku_id,
                "sku_name": sku_name,
                "base_unit_price": price,
                "currency": currency
            }
            res = api_request("POST", "/admin/product-prices", product_data)
            if res and res.status_code == 200:
                st.success("Product added!")
                st.rerun()
            else:
                st.error("Failed to add product")

def render_test_repository():
    # Get existing tests
    res = api_request("GET", "/admin/test-prices")
    if res and res.status_code == 200:
        tests = res.json()
        for test in tests:
            with st.expander(f"{test['test_name']} ({test['_id']})"):
                st.write(f"**Price:** ${test['test_price']:,.2f} {test['currency']}")
                if st.button("Delete", key=f"del_test_{test['_id']}"):
                    api_request("DELETE", f"/admin/test-prices/{test['_id']}")
                    st.rerun()

    # Add new test
    st.markdown("---")
    st.subheader("Add New Test Service")
    with st.form("new_test"):
        test_code = st.text_input("Test Code")
        test_name = st.text_input("Test Name")
        price = st.number_input("Test Price", min_value=0.0)
        currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])

        if st.form_submit_button("Add Test"):
            test_data = {
                "test_code": test_code,
                "test_name": test_name,
                "test_price": price,
                "currency": currency
            }
            res = api_request("POST", "/admin/test-prices", test_data)
            if res and res.status_code == 200:
                st.success("Test added!")
                st.rerun()
            else:
                st.error("Failed to add test")

def render_cron_jobs():
    # Get existing jobs
    res = api_request("GET", "/admin/cron-jobs")
    if res and res.status_code == 200:
        jobs = res.json()
        for job in jobs:
            with st.expander(f"{job['name']} ({'Enabled' if job['enabled'] else 'Disabled'})"):
                st.write(f"**Type:** {job['schedule_type']}")
                if job['schedule_type'] == 'interval':
                    st.write(f"**Interval:** {job.get('interval_minutes', 0)} minutes")
                else:
                    st.write(f"**Min Pending RFPs:** {job.get('min_pending_rfps', 0)}")
                st.write(f"**Last Run:** {job.get('last_run', 'Never')}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Toggle Enable/Disable", key=f"toggle_{job['id']}"):
                        api_request("PUT", f"/admin/cron-jobs/{job['id']}", {"enabled": not job['enabled']})
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"del_job_{job['id']}"):
                        # Note: Need to implement delete endpoint
                        st.info("Delete functionality coming soon")

    # Add new cron job
    st.markdown("---")
    st.subheader("Add New Cron Job")
    with st.form("new_cron"):
        name = st.text_input("Job Name")
        schedule_type = st.selectbox("Schedule Type", ["interval", "count_based"])
        enabled = st.checkbox("Enabled", value=False)

        if schedule_type == "interval":
            interval = st.number_input("Interval (minutes)", min_value=1, value=60)
            min_pending = None
        else:
            interval = None
            min_pending = st.number_input("Min Pending RFPs", min_value=1, value=5)

        if st.form_submit_button("Add Cron Job"):
            job_data = {
                "name": name,
                "enabled": enabled,
                "schedule_type": schedule_type,
                "interval_minutes": interval,
                "min_pending_rfps": min_pending
            }
            res = api_request("POST", "/admin/cron-jobs", job_data)
            if res and res.status_code == 200:
                st.success("Cron job added!")
                st.rerun()
            else:
                st.error("Failed to add cron job")

# ======================================================
# DEMO MANAGEMENT (ADMIN)
# ======================================================
def render_demo_management():
    st.subheader("Demo Centers")
    # Get demo centers
    res = api_request("GET", "/admin/demo-centers")
    if res and res.status_code == 200:
        centers = res.json()
        for center in centers:
            with st.expander(f"{center['name']} ({'Active' if center['is_active'] else 'Inactive'})"):
                st.write(f"**Location:** {center['location']}")
                st.write(f"**Address:** {center['address']}")
                st.write(f"**Contact:** {center.get('contact_phone', 'N/A')} | {center.get('contact_email', 'N/A')}")
                st.write(f"**Available Slots:** {', '.join(center.get('available_slots', []))}")

    # Add new center
    st.markdown("---")
    st.subheader("Add New Demo Center")
    with st.form("new_center"):
        name = st.text_input("Center Name")
        location = st.text_input("Location (City, State/Country)")
        address = st.text_area("Full Address")
        contact_phone = st.text_input("Contact Phone")
        contact_email = st.text_input("Contact Email")
        available_slots = st.text_area("Available Slots (one per line, format: YYYY-MM-DD HH:MM)")
        is_active = st.checkbox("Active", value=True)

        if st.form_submit_button("Add Center"):
            slots_list = [slot.strip() for slot in available_slots.split('\n') if slot.strip()]
            center_data = {
                "name": name,
                "location": location,
                "address": address,
                "contact_phone": contact_phone,
                "contact_email": contact_email,
                "available_slots": slots_list,
                "is_active": is_active
            }
            res = api_request("POST", "/admin/demo-centers", center_data)
            if res and res.status_code == 200:
                st.success("Demo center added!")
                st.rerun()
            else:
                st.error("Failed to add demo center")

    st.markdown("---")
    st.subheader("Demo Requests")

    # Get demo requests
    res = api_request("GET", "/admin/demo-requests")
    if res and res.status_code == 200:
        demo_requests = res.json()
        for req in demo_requests:
            with st.expander(f"Demo Request: {req.get('rfp_id', 'Unknown')} - {req.get('status', 'Unknown').title()}", expanded=False):
                st.write(f"**Client:** {req.get('user_id', 'Unknown')}")
                st.write(f"**Preferred Location:** {req.get('preferred_location', 'Not specified')}")
                if req.get('preferred_date'):
                    st.write(f"**Preferred Date:** {req.get('preferred_date', 'Not specified')[:10]}")
                if req.get('special_requirements'):
                    st.write(f"**Special Requirements:** {req.get('special_requirements')}")

                if req.get('status') == 'requested':
                    # Show scheduling options
                    centers_res = api_request("GET", "/demo-centers")
                    if centers_res and centers_res.status_code == 200:
                        centers = centers_res.json()
                        with st.form(f"schedule_form_{req['_id']}"):
                            center_options = [f"{c['_id']} - {c['name']}" for c in centers if c['is_active']]
                            selected_center = st.selectbox("Select Center", center_options)
                            scheduled_date = st.date_input("Scheduled Date")
                            scheduled_time = st.time_input("Scheduled Time")
                            admin_notes = st.text_area("Admin Notes")

                            if st.form_submit_button("Schedule Demo"):
                                center_id = selected_center.split(" - ")[0]
                                scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
                                schedule_data = {
                                    "center_id": center_id,
                                    "scheduled_datetime": scheduled_datetime.isoformat(),
                                    "admin_notes": admin_notes
                                }
                                res = api_request("PUT", f"/admin/demo-requests/{req['_id']}/schedule", schedule_data)
                                if res and res.status_code == 200:
                                    st.success("Demo scheduled!")
                                    st.rerun()
                                else:
                                    st.error("Failed to schedule demo")

                elif req.get('status') == 'scheduled':
                    st.write(f"**Scheduled Center:** {req.get('scheduled_center_id', 'N/A')}")
                    st.write(f"**Scheduled Date/Time:** {req.get('scheduled_datetime', 'N/A')}")
                    if req.get('admin_notes'):
                        st.write(f"**Admin Notes:** {req.get('admin_notes')}")

                elif req.get('status') == 'completed':
                    if req.get('final_decision'):
                        decision_icon = "✅" if req.get('final_decision') == "accept" else "❌"
                        st.write(f"**Final Decision:** {decision_icon} {req.get('final_decision').title()}")
                        if req.get('client_feedback'):
                            st.write(f"**Client Feedback:** {req.get('client_feedback')}")

                st.caption(f"Created: {req.get('created_at', '')[:10]}")

# ======================================================
# DEMO REQUESTS
# ======================================================
def render_demo_requests():
    st.title("Demo Requests")
    st.caption("Manage your product demo and sample requests")

    # Get demo requests
    res = api_request("GET", "/demo-requests")
    if not res or res.status_code != 200:
        st.error("Failed to load demo requests")
        return

    demo_requests = res.json()
    if not demo_requests:
        st.info("No demo requests found. Demo requests will appear here after you submit them for accepted RFPs.")
        return

    for req in demo_requests:
        with st.expander(f"Demo Request for RFP: {req.get('rfp_id', 'Unknown')}", expanded=False):
            st.write(f"**Status:** {req.get('status', 'Unknown').title()}")
            st.write(f"**Preferred Location:** {req.get('preferred_location', 'Not specified')}")
            if req.get('preferred_date'):
                st.write(f"**Preferred Date:** {req.get('preferred_date', 'Not specified')[:10]}")
            if req.get('special_requirements'):
                st.write(f"**Special Requirements:** {req.get('special_requirements')}")

            if req.get('scheduled_center_id'):
                st.write(f"**Scheduled Center:** {req.get('scheduled_center_id')}")
            if req.get('scheduled_datetime'):
                st.write(f"**Scheduled Date/Time:** {req.get('scheduled_datetime')}")

            if req.get('admin_notes'):
                st.write(f"**Admin Notes:** {req.get('admin_notes')}")

            if req.get('final_decision'):
                decision_icon = "✅" if req.get('final_decision') == "accept" else "❌"
                st.write(f"**Final Decision:** {decision_icon} {req.get('final_decision').title()}")
                if req.get('client_feedback'):
                    st.write(f"**Your Feedback:** {req.get('client_feedback')}")

            st.caption(f"Created: {req.get('created_at', '')[:10]}")
            
import google.generativeai as genai
import os

def render_ai_rfp_generator():
    st.markdown('<div class="main-header"><h1><i class="fas fa-robot"></i> Smart RFP Generator</h1><p>Generate high-quality headlines, details, and pricing structures</p></div>', unsafe_allow_html=True)
    
    # Configure Gemini from your ENV
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("GOOGLE_API_KEY not found in environment. Please check your .env file.")
        return
    
    genai.configure(api_key=api_key)

    with st.container():
        st.subheader("Project Inputs")
        with st.form("ai_gen_form"):
            col1, col2 = st.columns(2)
            with col1:
                topic = st.text_input("What are you looking for?", placeholder="e.g., Installation of 500kW Solar Grid")
                industry = st.selectbox("Industry Segment", ["Industrial", "Renewable Energy", "Construction", "IT Infrastructure"])
            with col2:
                budget_hint = st.text_input("Estimated Budget (Optional)", placeholder="e.g., $200k - $250k")
                urgency = st.select_slider("Urgency Level", options=["Low", "Medium", "High"])

            context = st.text_area("Specific Requirements", placeholder="Mention technical specs, quality standards, or specific location needs...")
            
            generate_btn = st.form_submit_button("Generate Professional RFP Draft")

    if generate_btn:
        if not topic or not context:
            st.warning("Please provide the project topic and specific requirements.")
        else:
            with st.spinner("Gemini AI is crafting your RFP..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = f"""
                    As an expert procurement officer, draft a professional RFP based on:
                    TOPIC: {topic}
                    INDUSTRY: {industry}
                    BUDGET CONTEXT: {budget_hint}
                    URGENCY: {urgency}
                    REQUIREMENTS: {context}

                    Strictly format the output as follows:
                    1. RFP HEADLINE: (A compelling, professional title)
                    2. PROJECT DETAILS: (Comprehensive scope of work and technical requirements)
                    3. PRICING GUIDELINES: (Suggested price structure: per unit, milestone-based, or lump sum)
                    4. VENDOR QUALIFICATIONS: (What the bidder must prove)

                    Use professional Markdown formatting.
                    """
                    
                    response = model.generate_content(prompt)
                    ai_content = response.text

                    st.session_state['last_ai_draft'] = ai_content
                    st.session_state['last_ai_title'] = topic

                    st.markdown("### ✨ Generated RFP Draft")
                    st.markdown(f'<div style="background-color: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 20px; border-radius: 10px; border-left: 5px solid #4f46e5;">{ai_content}</div>', unsafe_allow_html=True)
                    
                    st.divider()
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("📋 Copy to 'Create RFP' Form"):
                            st.session_state['auto_fill_rfp'] = True
                            st.success("Draft saved! Navigate to 'Create RFP' to finalize.")
                    with col_b:
                        st.download_button("📥 Download as Text", ai_content, file_name="rfp_draft.txt")

                except Exception as e:
                    st.error(f"Error generating RFP: {str(e)}")
# ======================================================
# CREATE RFP
# ======================================================
def render_create_rfp():
    st.title("Create RFP")

    with st.form("rfp_form"):
        title = st.text_input("Title")
        description = st.text_area("Description")
        budget = st.number_input("Approximate Budget", min_value=0.0)
        due_date = st.date_input("Due Date")

        submit = st.form_submit_button("Create")

        if submit:
            if not title or not description:
                st.warning("Title and description required")
                return

            payload = {
                "title": title,
                "description": description,
                "approximate_budget": budget,
                "due_date": datetime.combine(
                    due_date, datetime.min.time()
                ).isoformat()
            }

            res = api_request("POST", "/rfps", payload)

            if res and res.status_code == 200:
                st.success("RFP created successfully")
                st.rerun()
            else:
                st.error(parse_error(res))

# ======================================================
# SMART CHAT (DEMO)
# ======================================================
def render_chat():
    st.title("Smart Chat")
    st.caption("Ask questions about your RFPs (Demo mode)")

    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "How can I help you today?"
        })

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Ask something..."):
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        st.chat_message("user").write(prompt)

        response = f"Demo response for: {prompt}"

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
        st.chat_message("assistant").write(response)

# ======================================================
# ENTRY POINT
# ======================================================
if st.session_state.token:
    dashboard()
else:
    auth_page()
