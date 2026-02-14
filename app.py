import streamlit as st
import google.generativeai as genai
from utils import generate_docx, update_sheet
from datetime import datetime
from awards import format_examples_for_prompt, get_citation_examples


# ============================================================================
# CONFIGURATION SECTION - Edit API model versions here if needed
# ============================================================================
st.set_page_config(layout="wide", page_title="SAFAISA Award Vetter")

MODEL_PRO = 'gemini-2.5-pro'      # Primary model for complex logic
MODEL_FLASH = 'gemini-2.5-flash'  # Fallback model for speed

# ============================================================================
# AWARD RULES CONFIGURATION
# ============================================================================
AWARD_WORD_LIMITS = {
    "CO Coin": 100,
    "RSM Coin": 100,
    "CTO Coin": 100,    # Edit word limit here
    "FSM Coin": 100,    # Edit word limit here
    "BSOM": 150,
}
# ============================================================================

# --- CSS STYLING ---
st.markdown("""
    <style>
    /* Remove default top padding */
    .block-container { 
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    
    /* Gradient Separator between columns */
    [data-testid="stColumn"]:nth-of-type(2) {
        border-left: 2px solid;
        border-image: linear-gradient(to bottom, transparent, #8f8d8f, transparent) 1;
        padding-left: 2rem;
    }
    
    /* Make buttons more distinct */
    .stButton button { 
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Primary button styling */
    .stButton button[kind="primary"] {
        background: linear-gradient(90deg, #1976D2, #2196F3);
    }
    
    /* Spacing between elements */
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    
    /* Text area styling */
    .stTextArea textarea {
        border-radius: 6px;
        border: 1.5px solid #e0e0e0;
    }
    
    /* Success message styling */
    .stSuccess {
        border-radius: 6px;
    }
    
    /* Logo styling */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1rem;
    }
    .sidebar-logo img {
        width: 40px;
        height: 40px;
        object-fit: contain;
    }
    
    /* Word count styling */
    .word-count {
        text-align: right;
        color: #666;
        font-size: 0.85em;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    
    /* Copy notification styling */
    .copy-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if "history" not in st.session_state:
    st.session_state.history = []
if "curr_idx" not in st.session_state:
    st.session_state.curr_idx = -1
if "batch_list" not in st.session_state:
    st.session_state.batch_list = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_month" not in st.session_state:
    st.session_state.current_month = ""
if "current_unit" not in st.session_state:
    st.session_state.current_unit = ""
if "show_copy_notification" not in st.session_state:
    st.session_state.show_copy_notification = False
if "notification_message" not in st.session_state:
    st.session_state.notification_message = ""

# --- CALLBACKS ---
def clear_form_callback():
    """Clears input widgets safely using callback"""
    keys_to_clear = [
        "i_rank", "i_fname", "i_lname", "i_award_name", "i_award_rules",
        "i_role_man", "i_draft", "i_cite_draft", "i_ippt", "i_bmi", "i_atp"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            st.session_state[key] = ""

def sync_text_callback(field_type):
    """Auto-saves edited text to history"""
    idx = st.session_state.curr_idx
    if idx >= 0:
        if field_type == "brief":
            st.session_state.history[idx]["brief"] = st.session_state[f"brief_box_{idx}"]
        elif field_type == "cite":
            st.session_state.history[idx]["cite"] = st.session_state[f"cite_box_{idx}"]

# --- AI ENGINE ---
def call_gemini(prompt):
    """Calls Gemini API with fallback support"""
    if "GEMINI_API_KEY" not in st.secrets:
        return "Error: API Key missing in secrets.toml"
    
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    try:
        model = genai.GenerativeModel(MODEL_PRO)
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        try:
            model = genai.GenerativeModel(MODEL_FLASH)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI Error: {str(e)}"

# --- LOGIN SCREEN ---
if not st.session_state.authenticated:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>Award Vetter</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: grey;'>SAFAISA System</p>", unsafe_allow_html=True)
        pwd = st.text_input("Enter Password", type="password", placeholder="Enter system password")
        if st.button("Login", use_container_width=True, type="primary"):
            if pwd == "NSAF123":  #password
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid Password")
    st.stop()

# --- MAIN APP ---
st.title("Award Vetter System")
st.markdown("*SAFAISA - Award Justification Generator*")

# Sidebar
with st.sidebar:
    # Logo and Header Section
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image("logo.png", width=50)
    with col2:
        st.markdown("<h2 style='margin-top: 5px;'>SAFAISA</h2>", unsafe_allow_html=True)

    # Option 2: emoji-based header (default)
    #st.header("📋 SAFAISA")

    
    st.success("✓ System Ready")
    st.markdown("---")
    
    # ============================================================================
    # GOOGLE SHEET LINK
    # ============================================================================
    GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1xykMC3Jb-qQUeyiDuqp2jQjOqhxwqjUJHd04qj67rmM/edit"
    # ============================================================================
    
    st.link_button(
        "Award Tracking Sheet",
        GOOGLE_SHEET_URL,
        use_container_width=True,
        help="View all nominated awards"
    )
    st.markdown("---")
    
    # Batch Status
    if st.session_state.batch_list:
        st.metric("Batch Count", len(st.session_state.batch_list))
        if st.button("Clear Batch", use_container_width=True):
            st.session_state.batch_list = []
            st.rerun()
    
    st.markdown("---")
    if st.button("🔓 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# Main Layout
left_col, right_col = st.columns(2)

# ================= LEFT COLUMN: INPUTS =================
with left_col:
    st.subheader("Input Details")
    
    # 1. Award Selection
    award = st.selectbox(
        "Award Type",
        ["CO Coin", "RSM Coin", "CTO Coin", "FSM Coin", "BSOM", "OTHER"],
        help="Select the type of award to generate justification for"
    )
    
    # Dynamic Rules
    actual_award_name = award
    award_rule_text = f"{AWARD_WORD_LIMITS.get(award, 160)} words"
    
    if award == "OTHER":
        actual_award_name = st.text_input("Award Name", key="i_award_name", placeholder="Enter custom award name")
        custom_rules = st.text_input("Word Limit", placeholder="e.g., 300 words", key="i_award_rules")
        if custom_rules:
            award_rule_text = custom_rules

    # 2. Role Selection
    ROLES = [
        "Transport Operator (TO)",
        "Transport Supervisor",
        "Transport Leader",
        "Platoon Commander",
        "Others"
    ]
    role_sel = st.selectbox("Serviceman Vocation", ROLES)
    actual_role = role_sel
    if role_sel == "Others":
        actual_role = st.text_input("Specify Vocation", key="i_role_man", placeholder="Enter Vocation manually")

    # 3. Unit & Person
    COMPANIES = [
        "Alpha COY",
        "Khatib Node",
        "Charlie COY",
        "HQ COY",
        "Kranji Node",
        "Mandai Hill Node",
        "Light Transport COY",
        "Combat Sustainment COY"
    ]
    s_unit = st.selectbox("Company / Node", COMPANIES)
    st.session_state.current_unit = s_unit  # Save for later use
    
    c1, c2, c3 = st.columns(3)
    s_rank = c1.text_input("Rank", key="i_rank", placeholder="e.g., CPL")
    s_fname = c2.text_input("Full Name", key="i_fname", placeholder="JOHN DEO").upper()
    s_lname = c3.text_input("Preferred / First Name", key="i_lname", placeholder="DEO").upper()
    
    full_name_caps = f"{s_fname}".strip()

    # Month of Award Presentation
    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    current_year = datetime.now().year
    
    month_col, year_col = st.columns(2)
    award_month = month_col.selectbox("Award Month", MONTHS, help="Month when award will be presented")
    award_year = year_col.selectbox("Award Year", [current_year, current_year + 1], help="Year of award presentation")
    
    # Store formatted month for Google Sheets
    st.session_state.current_month = f"{award_month} {award_year}"

    # 5. Extra Fields (CTO/FSM Awards Only)
    if award in ["CTO Coin", "FSM Coin"]:
        st.markdown("**Additional Information**")
        q1, q2, q3 = st.columns(3)
        ippt = q1.text_input("IPPT Score", key="i_ippt", placeholder="85")
        bmi = q2.text_input("BMI", key="i_bmi", placeholder="22.5")
        atp = q3.text_input("ATP Score", key="i_atp", placeholder="33")
        cite_draft = st.text_area("Citation Draft", key="i_cite_draft", height=100, placeholder="Brief citation content...")

    # 6. Main Draft Input with live word count
    main_draft = st.text_area(
        "Draft Write-up",
        height=200,
        key="i_draft",
        placeholder="Enter the rough draft or key achievements here..."
    )
    
    # Live word count for draft input
    if main_draft:
        draft_word_count = len(main_draft.split())
        st.markdown(f"<p class='word-count'>Word count: {draft_word_count}</p>", unsafe_allow_html=True)
    
    # === GENERATION BUTTON ===
    if st.button("✨ Generate Justification", type="primary", use_container_width=True):
        if not main_draft:
            st.warning("⚠️ Please enter a draft before generating.")
        elif not s_rank or not full_name_caps:
            st.warning("⚠️ Please enter rank and name.")
        else:
            with st.spinner("Processing with Gemini AI..."):
                
                # ============================================================================
                # AI PROMPT CONFIGURATION - EDIT GENERATION RULES HERE
                # ============================================================================
                  # Get examples for this award type
                examples_text = format_examples_for_prompt(actual_award_name)
 
                prompt_text = f"""
Role: {actual_role}
Unit: {s_unit}
Award: {actual_award_name}
Subject: {s_rank} {full_name_caps}

INSTRUCTIONS:
1. Tense: Use strictly Past or Present tense only
2. Exercise Names: Remove ALL exercise names (e.g., Ex Wallaby, Ex Thunder) instead mention them as exercise or overseas exercise
3. Opening Line: Start with 'Being a [appropriate adjective] {actual_role} from {s_unit}...'
4. Name Usage: Use '{s_rank} {s_lname}'
5. Length: Approximately {award_rule_text}
6. Tone: Professional, formal military writing
7. Focus: Highlight any two or three of the serviceman's specific achievements, leadership, primary and secondary duties, inspiration to peers, attitude, safety, punctuality and contributions depending on the context given by user
8. Style: Match the format, structure, and tone of the examples below
9. Formatting Rules:
   - Do NOT use asterisks (*) for emphasis or highlighting
   - Do NOT use bold, italics, or any special formatting
   - Write in plain text only
   - Do NOT end with recommendation phrases like "I recommend him", "he deserves", "worthy of this award", etc.
   - End with the last achievement or quality statement
10. Output: Provide ONLY the final justification text in plain text format with no explanations, no meta-commentary, no formatting marks

{examples_text}
DRAFT CONTENT:
{main_draft}

Generate the final award justification following all rules above. Remember: plain text only, no asterisks, no recommendation ending.
"""
                # ============================================================================
                
                # Call AI for Brief
                brief_out = call_gemini(prompt_text)
                
                # Call AI for Citation (CTO/FSM only)
                cite_out = ""
                if award in ["CTO Coin", "FSM Coin"]:
                    # ============================================================================
                    # CITATION PROMPT - EDIT CITATION RULES HERE
                    # ============================================================================
                    cite_prompt = f"""
Write a formal military citation for {s_rank} {full_name_caps} from the perspective of a commander.

Requirements:
- 2 pages in length
- Formal, professional tone
- Highlight key achievements, duties and performance of the serviceman
- Base content strictly on the provided context - do not hallucinate or invent achievements
- No exercise names - refer to them as "exercise" or "overseas exercise"
- Plain text only - NO asterisks (*), NO bold, NO italics, NO special formatting
- Do NOT include any meta-commentary, explanations, or notes
- Do NOT end with recommendation phrases
- Output ONLY the citation text in plain text format

Context: {cite_draft if cite_draft else main_draft}

Generate the citation now. Remember: plain text only, no formatting marks, no comments.
"""
                    # ============================================================================
                    cite_out = call_gemini(cite_prompt)
                
                # Save to History
                st.session_state.history.append({
                    "brief": brief_out,
                    "cite": cite_out,
                    "rank": s_rank,
                    "name": full_name_caps,
                    "award": actual_award_name,
                    "unit": s_unit,
                    "month": st.session_state.current_month
                })
                st.session_state.curr_idx = len(st.session_state.history) - 1
                st.rerun()

# ================= RIGHT COLUMN: OUTPUTS =================
with right_col:
    st.subheader("📄 Generated Output")

    if st.session_state.curr_idx >= 0:
        curr = st.session_state.history[st.session_state.curr_idx]
        
        # --- BRIEFING WRITEUP ---
        st.markdown(f"**{curr['rank']} {curr['name']}** - *{curr['award']}*")
        
        # Editable Text Area with auto-save
        val_brief = st.text_area(
            "Justification",
            value=curr["brief"],
            height=250,
            key=f"brief_box_{st.session_state.curr_idx}",
            on_change=sync_text_callback,
            args=("brief",),
            help="Edit the text directly - changes are saved automatically"
        )
        
        # Live word count display for brief
        word_count_brief = len(val_brief.split()) if val_brief.strip() else 0
        st.markdown(f"<p class='word-count'>Word count: {word_count_brief}</p>", unsafe_allow_html=True)
        
        # Controls Row
        c1, c2 = st.columns([1, 2])
        
        # Copy Button - Using Streamlit's code block method
        if c1.button("📋 Copy Text", key="copy_brief", use_container_width=True):
            st.code(val_brief, language=None)
            st.info("👆 Click the copy icon in the top-right corner of the text box above to copy")
        
        # Redo Brief
        redo_note_brief = c2.text_input(
            "Modification Instructions",
            placeholder="e.g., Make more humble, add more details such as..",
            label_visibility="collapsed"
        )
        if c2.button("🔄 Regenerate", key="redo_brief", use_container_width=True):
            if redo_note_brief:
                with st.spinner("🔄 Regenerating brief..."):
                    # ============================================================================
                    # REDO PROMPT - EDIT MODIFICATION RULES HERE
                    # ============================================================================
                    redo_prompt = f"""
Rewrite the following text with these modifications: {redo_note_brief}

Maintain the same structure and professionalism.
Output ONLY the revised text, no explanations.

Original Text:
{val_brief}
"""
                    # ============================================================================
                    new_b = call_gemini(redo_prompt)
                    
                    # Append new version
                    st.session_state.history.append({
                        "brief": new_b,
                        "cite": curr["cite"],
                        "rank": curr["rank"],
                        "name": curr["name"],
                        "award": curr["award"],
                        "unit": curr["unit"],
                        "month": curr["month"]
                    })
                    st.session_state.curr_idx += 1
                    st.rerun()
            else:
                st.warning("Please enter modification instructions")

        # --- CITATION SECTION (if applicable) ---
        if curr["cite"]:
            st.divider()
            st.markdown("**Citation**")
            val_cite = st.text_area(
                "Citation Text",
                value=curr["cite"],
                height=120,
                key=f"cite_box_{st.session_state.curr_idx}",
                on_change=sync_text_callback,
                args=("cite",),
                help="Edit citation - changes saved automatically"
            )
            
            # Live word count display for citation
            word_count_cite = len(val_cite.split()) if val_cite.strip() else 0
            st.markdown(f"<p class='word-count'>Word count: {word_count_cite}</p>", unsafe_allow_html=True)
            
            d1, d2 = st.columns([1, 2])
            
            # Copy Citation - Using Streamlit's code block method
            if d1.button("📋 Copy", key="copy_cite", use_container_width=True):
                st.code(val_cite, language=None)
                st.info("👆 Click the copy icon in the top-right corner of the text box above to copy")
            
            # Redo Citation
            redo_note_cite = d2.text_input(
                "Citation Modifications",
                placeholder="e.g., More formal",
                label_visibility="collapsed"
            )
            if d2.button("🔄 Regenerate", key="redo_cite", use_container_width=True):
                if redo_note_cite:
                    with st.spinner("🔄 Regenerating citation..."):
                        redo_prompt_cite = f"""
Rewrite this citation with modifications: {redo_note_cite}

Keep 2 page word limit, formal tone.
Output ONLY the revised citation, no explanations.

Original:
{val_cite}
"""
                        new_c = call_gemini(redo_prompt_cite)
                        
                        st.session_state.history.append({
                            "brief": curr["brief"],
                            "cite": new_c,
                            "rank": curr["rank"],
                            "name": curr["name"],
                            "award": curr["award"],
                            "unit": curr["unit"],
                            "month": curr["month"]
                        })
                        st.session_state.curr_idx += 1
                        st.rerun()
                else:
                    st.warning("Please enter modification instructions")

        st.divider()

        # --- VERSION NAVIGATION ---
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        
        if col_prev.button("⬅️ Previous", use_container_width=True, disabled=(st.session_state.curr_idx == 0)):
            st.session_state.curr_idx -= 1
            st.rerun()
        
        total_versions = len(st.session_state.history)
        col_info.markdown(
            f"<div style='text-align:center; padding-top:8px; color:grey;'>Version {st.session_state.curr_idx + 1} of {total_versions}</div>",
            unsafe_allow_html=True
        )
        
        if col_next.button("Next ➡️", use_container_width=True, disabled=(st.session_state.curr_idx >= total_versions - 1)):
            st.session_state.curr_idx += 1
            st.rerun()

        st.markdown("---")

        # --- ACTION BUTTONS (REDESIGNED) ---
        b1, b2 = st.columns(2)
        
        # Button 1: Accept and Add to Batch (for multiple entries)
        if b1.button("✅ Accept & Add More", on_click=clear_form_callback, use_container_width=True):
            # Add brief to batch
            entry_brief = {
                "rank": curr["rank"],
                "name": curr["name"],
                "text": st.session_state.history[st.session_state.curr_idx]["brief"],
                "award": curr["award"],
                "unit": curr["unit"],
                "month": curr["month"]
            }
            st.session_state.batch_list.append(entry_brief)
            
            # Add citation if exists
            if curr["cite"]:
                entry_cite = {
                    "rank": curr["rank"],
                    "name": curr["name"] + " (CITATION)",
                    "text": st.session_state.history[st.session_state.curr_idx]["cite"],
                    "award": curr["award"],
                    "unit": curr["unit"],
                    "month": curr["month"]
                }
                st.session_state.batch_list.append(entry_cite)
            
            # Update Google Sheet
            update_sheet([entry_brief])
            
            st.success(f"✓ Accepted {curr['name']} and added to tracking sheet!")
            st.rerun()

        # Button 2: Accept and Export (finalizes current + batch)
        if b2.button("💾 Accept & Export", use_container_width=True, type="primary"):
            # Create current entry
            current_entry = {
                "rank": curr["rank"],
                "name": curr["name"],
                "text": st.session_state.history[st.session_state.curr_idx]["brief"],
                "award": curr["award"],
                "unit": curr["unit"],
                "month": curr["month"]
            }
            
            # Prepare all data for export (batch + current)
            export_data = st.session_state.batch_list.copy()
            
            # Check if current entry is already in batch
            is_in_batch = any(
                item["rank"] == current_entry["rank"] and 
                item["name"] == current_entry["name"] and
                "(CITATION)" not in item["name"]
                for item in export_data
            )
            
            # If not in batch, add current entry
            if not is_in_batch:
                export_data.append(current_entry)
                
                # Add citation if exists
                if curr["cite"]:
                    export_data.append({
                        "rank": curr["rank"],
                        "name": curr["name"] + " (CITATION)",
                        "text": st.session_state.history[st.session_state.curr_idx]["cite"],
                        "award": curr["award"],
                        "unit": curr["unit"],
                        "month": curr["month"]
                    })
                
                # Update Google Sheet for current entry only
                update_sheet([current_entry])
            
            # Generate Word document with all data
            doc_bytes = generate_docx(export_data)
            
            # Download button
            st.download_button(
                label="📥 Download Word Document",
                data=doc_bytes,
                file_name=f"Award_Justifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
            
            # Clear batch after export
            st.session_state.batch_list = []
            st.success("✓ Document generated! All entries sent to tracking sheet.")
            
    else:
        st.info("👈 Enter details on the left and click 'Generate Justification' to begin.")
        st.markdown("---")
        st.markdown("""
        **How to use:**
        1. Select award type and role
        2. Enter serviceman details and award month
        3. Provide draft write-up
        4. Click Generate
        5. Edit and refine output
        6. Choose action:
           - **Accept & Add More**: Save to batch and enter another award
           - **Accept & Export**: Finalize and download Word document
        """)