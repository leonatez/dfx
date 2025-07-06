import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import re
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="DataFrameX",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .section-header {
        background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .metric-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .info-box {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'groups' not in st.session_state:
    st.session_state.groups = {}
if 'actions' not in st.session_state:
    st.session_state.actions = []
if 'processed_groups' not in st.session_state:
    st.session_state.processed_groups = {}
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'group_presets' not in st.session_state:
    st.session_state.group_presets = {}

def process_excel_files(files, sheet_name, header_row, header_col):
    """Process multiple Excel files and combine them into a single dataframe"""
    combined_df = pd.DataFrame()
    
    for file in files:
        try:
            # Read Excel file
            df = pd.read_excel(file, sheet_name=sheet_name, header=None)
            
            # Adjust for header row and column (convert to 0-based indexing)
            start_row = header_row - 1
            start_col = header_col - 1
            
            # Extract data starting from specified position
            df_subset = df.iloc[start_row:, start_col:]
            
            # Set first row as column names
            df_subset.columns = df_subset.iloc[0]
            df_subset = df_subset.drop(df_subset.index[0]).reset_index(drop=True)
            
            # Add source file information
            df_subset['_source_file'] = file.name
            
            # Combine with existing dataframe
            if combined_df.empty:
                combined_df = df_subset
            else:
                combined_df = pd.concat([combined_df, df_subset], ignore_index=True)
                
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
    
    return combined_df

def apply_actions(df, actions, processed_groups):
    """Apply all actions to the dataframe"""
    result_df = df.copy()
    
    for action in actions:
        try:
            if action['type'] == 'rename_column':
                if action['old_name'] in result_df.columns:
                    result_df.rename(columns={action['old_name']: action['new_name']}, inplace=True)
                else:
                    st.warning(f"Column '{action['old_name']}' not found for renaming")
            
            elif action['type'] == 'change_type':
                if action['column'] in result_df.columns:
                    if action['new_type'] == 'int':
                        result_df[action['column']] = pd.to_numeric(result_df[action['column']], errors='coerce').astype('Int64')
                    elif action['new_type'] == 'float':
                        result_df[action['column']] = pd.to_numeric(result_df[action['column']], errors='coerce')
                    elif action['new_type'] == 'string':
                        result_df[action['column']] = result_df[action['column']].astype(str)
                    elif action['new_type'] == 'datetime':
                        result_df[action['column']] = pd.to_datetime(result_df[action['column']], errors='coerce')
                else:
                    st.warning(f"Column '{action['column']}' not found for type change")
            
            elif action['type'] == 'filter':
                if action['column'] in result_df.columns:
                    filter_values = [val.strip() for val in action['values'].split(',')]
                    result_df = result_df[result_df[action['column']].isin(filter_values)]
                else:
                    st.warning(f"Column '{action['column']}' not found for filtering")
            
            elif action['type'] == 'create_column':
                try:
                    # Evaluate the formula in the context of the dataframe
                    result_df[action['new_column']] = eval(action['formula'], {'df': result_df, 'pd': pd, 'np': np})
                except Exception as e:
                    st.error(f"Error creating column '{action['new_column']}': {str(e)}")
            
            elif action['type'] == 'drop_columns':
                columns_to_drop = [col.strip() for col in action['columns'].split(',')]
                existing_columns = [col for col in columns_to_drop if col in result_df.columns]
                if existing_columns:
                    result_df.drop(columns=existing_columns, inplace=True)
                else:
                    st.warning(f"None of the specified columns found for dropping")
            
            elif action['type'] == 'merge':
                # Use processed dataframe if available, otherwise use original
                if action['right_df'] in processed_groups:
                    right_df = processed_groups[action['right_df']]
                elif action['right_df'] in st.session_state.groups:
                    right_df = st.session_state.groups[action['right_df']]
                else:
                    st.warning(f"Right dataframe '{action['right_df']}' not found")
                    continue
                    
                if action['key_column'] in result_df.columns and action['key_column'] in right_df.columns:
                    result_df = result_df.merge(right_df, on=action['key_column'], how='left')
                else:
                    st.warning(f"Key column '{action['key_column']}' not found in one or both dataframes")
            
            elif action['type'] == 'sort':
                if action['column'] in result_df.columns:
                    ascending = action['order'] == 'asc'
                    result_df = result_df.sort_values(by=action['column'], ascending=ascending).reset_index(drop=True)
                else:
                    st.warning(f"Column '{action['column']}' not found for sorting")
            
            elif action['type'] == 'group_aggregate':
                group_cols = [col.strip() for col in action['group_columns'].split(',')]
                existing_group_cols = [col for col in group_cols if col in result_df.columns]
                
                if existing_group_cols and action['agg_column'] in result_df.columns:
                    agg_func = action['agg_function']
                    if agg_func == 'count':
                        result_df = result_df.groupby(existing_group_cols)[action['agg_column']].count().reset_index()
                    elif agg_func == 'sum':
                        result_df = result_df.groupby(existing_group_cols)[action['agg_column']].sum().reset_index()
                    elif agg_func == 'mean':
                        result_df = result_df.groupby(existing_group_cols)[action['agg_column']].mean().reset_index()
                    elif agg_func == 'max':
                        result_df = result_df.groupby(existing_group_cols)[action['agg_column']].max().reset_index()
                    elif agg_func == 'min':
                        result_df = result_df.groupby(existing_group_cols)[action['agg_column']].min().reset_index()
                else:
                    st.warning(f"Group or aggregation columns not found")
            
            elif action['type'] == 'remove_duplicates':
                if action.get('columns'):
                    subset_cols = [col.strip() for col in action['columns'].split(',')]
                    existing_cols = [col for col in subset_cols if col in result_df.columns]
                    if existing_cols:
                        result_df = result_df.drop_duplicates(subset=existing_cols).reset_index(drop=True)
                else:
                    result_df = result_df.drop_duplicates().reset_index(drop=True)
            
            elif action['type'] == 'fill_missing':
                if action['column'] in result_df.columns:
                    if action['method'] == 'value':
                        result_df[action['column']].fillna(action['fill_value'], inplace=True)
                    elif action['method'] == 'forward':
                        result_df[action['column']].fillna(method='ffill', inplace=True)
                    elif action['method'] == 'backward':
                        result_df[action['column']].fillna(method='bfill', inplace=True)
                    elif action['method'] == 'mean':
                        mean_val = result_df[action['column']].mean()
                        result_df[action['column']].fillna(mean_val, inplace=True)
                else:
                    st.warning(f"Column '{action['column']}' not found for filling missing values")
            
            elif action['type'] == 'adjust_column_value':
                if action['column'] in result_df.columns:
                    try:
                        # Evaluate the formula and assign the result to the column
                        result_df[action['column']] = eval(action['formula'], {'df': result_df, 'pd': pd, 'np': np})
                    except Exception as e:
                        st.error(f"Error adjusting column '{action['column']}': {str(e)}")
                else:
                    st.warning(f"Column '{action['column']}' not found for adjustment")
        
        except Exception as e:
            st.error(f"Error applying action {action['type']}: {str(e)}")
    
    return result_df

# Main header
st.markdown("""
<div class="main-header">
    <h1>📊 DataFrame Extreme</h1>
    <p>Process Excel files automatically with custom grouping and data transformations</p>
</div>
""", unsafe_allow_html=True)

# Progress indicator
col1, col2, col3 = st.columns(3)
with col1:
    step1_status = "✅" if st.session_state.groups else "📋"
    st.markdown(f"**{step1_status} Step 1: Create Groups**")
with col2:
    step2_status = "✅" if st.session_state.actions else "⚙️"
    st.markdown(f"**{step2_status} Step 2: Define Actions**")
with col3:
    step3_status = "✅" if st.session_state.processed_groups else "🚀"
    st.markdown(f"**{step3_status} Step 3: Process Data**")

st.markdown("---")

# Sidebar for workflow management
st.sidebar.title("🔄 Workflow Management")

# Export workflow
if st.session_state.actions:
    workflow_data = {
        "workflow_name": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "actions": st.session_state.actions,
        "group_presets": st.session_state.group_presets,
        "created_date": datetime.now().isoformat(),
        "total_actions": len(st.session_state.actions),
        "groups_used": list(set(action['group'] for action in st.session_state.actions)),
        "version": "1.0"
    }
    
    workflow_json = json.dumps(workflow_data, indent=2)
    st.sidebar.download_button(
        label="📥 Export Workflow",
        data=workflow_json,
        file_name=f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

# Import workflow
uploaded_workflow = st.sidebar.file_uploader(
    "📤 Import Workflow",
    type=['json'],
    help="Upload a previously saved workflow JSON file"
)

if uploaded_workflow is not None:
    try:
        workflow_content = json.loads(uploaded_workflow.read())
        
        if st.sidebar.button("Load Workflow", type="primary"):
            if "actions" in workflow_content:
                st.session_state.actions = workflow_content["actions"]
                # Load group presets if available
                if "group_presets" in workflow_content:
                    st.session_state.group_presets = workflow_content["group_presets"]
                    st.sidebar.success(f"✅ Loaded {len(workflow_content['actions'])} actions and {len(workflow_content['group_presets'])} group presets!")
                else:
                    st.sidebar.success(f"✅ Loaded {len(workflow_content['actions'])} actions!")
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid workflow file format")
    except Exception as e:
        st.sidebar.error(f"❌ Error loading workflow: {str(e)}")

# Clear all actions
if st.session_state.actions:
    if st.sidebar.button("🗑️ Clear All Actions", help="Remove all configured actions"):
        st.session_state.actions = []
        st.sidebar.success("Actions cleared!")
        st.rerun()

# Current status in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Current Status")
st.sidebar.metric("Groups Created", len(st.session_state.groups))
st.sidebar.metric("Actions Configured", len(st.session_state.actions))
st.sidebar.metric("Processed Groups", len(st.session_state.processed_groups))

# ====================
# STEP 1: CREATE GROUPS
# ====================
st.markdown('<div class="section-header"><h2>📋 Step 1: Create Groups</h2></div>', unsafe_allow_html=True)
st.markdown("Group files with the same template together for processing")

# Group creation form
with st.form("group_form", clear_on_submit=True):
    st.subheader("Group Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        group_name = st.text_input("Group Name", placeholder="e.g., Sales Reports")
        sheet_name = st.text_input("Sheet Name", value="Sheet1", placeholder="Sheet name to process")
    
    with col2:
        header_row = st.number_input("Header Row", min_value=1, value=1, help="Row number where headers start")
        header_col = st.number_input("Header Column", min_value=1, value=1, help="Column number where data starts")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Excel Files",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        help="Upload all files that belong to this group"
    )
    
    # Submit button
    create_group = st.form_submit_button("Create Group", type="primary")
    
    if create_group:
        if group_name and uploaded_files:
            with st.spinner(f"Processing {len(uploaded_files)} files..."):
                combined_df = process_excel_files(uploaded_files, sheet_name, header_row, header_col)
                
                if not combined_df.empty:
                    st.session_state.groups[group_name] = combined_df
                    # Store group preset information
                    st.session_state.group_presets[group_name] = {
                        "group_name": group_name,
                        "sheet_name": sheet_name,
                        "header_row": header_row,
                        "header_column": header_col
                    }
                    st.success(f"✅ Group '{group_name}' created successfully with {len(combined_df)} rows!")
                    
                    # Show preview
                    st.subheader("Preview (First 5 rows)")
                    st.dataframe(combined_df.head(), use_container_width=True)
                    
                    # Show summary
                    st.info(f"📋 Summary: {len(combined_df)} rows, {len(combined_df.columns)} columns from {len(uploaded_files)} files")
                    
                else:
                    st.error("❌ Failed to process files. Please check your settings.")
        else:
            st.error("❌ Please provide a group name and upload at least one file.")

# Display existing groups
if st.session_state.groups:
    st.subheader("📁 Existing Groups")
    for group_name, df in st.session_state.groups.items():
        with st.expander(f"📊 {group_name} ({len(df)} rows, {len(df.columns)} columns)"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.dataframe(df.head(), use_container_width=True)
            with col2:
                if st.button(f"🗑️ Delete {group_name}", key=f"delete_{group_name}"):
                    del st.session_state.groups[group_name]
                    if group_name in st.session_state.group_presets:
                        del st.session_state.group_presets[group_name]
                    st.rerun()

# Display imported group presets
if st.session_state.group_presets:
    st.subheader("📋 Available Group Presets")
    st.markdown("These presets were imported from a workflow. Upload files to create groups using these settings.")
    
    for preset_name, preset_info in st.session_state.group_presets.items():
        if preset_name not in st.session_state.groups:  # Only show presets that haven't been created yet
            with st.expander(f"📋 {preset_name} (Preset)", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Group Name:** {preset_info['group_name']}")
                    st.markdown(f"**Sheet Name:** {preset_info['sheet_name']}")
                    st.markdown(f"**Header Row:** {preset_info['header_row']}")
                    st.markdown(f"**Header Column:** {preset_info['header_column']}")
                
                with col2:
                    # File uploader for this preset
                    preset_files = st.file_uploader(
                        f"Upload files for {preset_name}",
                        type=['xlsx', 'xls'],
                        accept_multiple_files=True,
                        key=f"preset_{preset_name}"
                    )
                    
                    if preset_files and st.button(f"Create from Preset", key=f"create_preset_{preset_name}"):
                        with st.spinner(f"Processing {len(preset_files)} files with preset settings..."):
                            combined_df = process_excel_files(
                                preset_files, 
                                preset_info['sheet_name'], 
                                preset_info['header_row'], 
                                preset_info['header_column']
                            )
                            
                            if not combined_df.empty:
                                st.session_state.groups[preset_name] = combined_df
                                st.success(f"✅ Group '{preset_name}' created from preset with {len(combined_df)} rows!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to process files. Please check your files.")

st.markdown("---")

# ====================
# STEP 2: CREATE ACTIONS
# ====================
st.markdown('<div class="section-header"><h2>⚙️ Step 2: Define Actions</h2></div>', unsafe_allow_html=True)
st.markdown("Define data processing actions to be applied to your groups")

if not st.session_state.groups:
    st.warning("⚠️ Please create at least one group first before defining actions.")
else:
    # Action creation interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Action type selection
        action_type = st.selectbox(
            "Select Action Type",
            ["rename_column", "change_type", "filter", "create_column", "drop_columns", "merge", 
             "sort", "group_aggregate", "remove_duplicates", "fill_missing", "adjust_column_value"],
            format_func=lambda x: x.replace('_', ' ').title()
        )
    
    with col2:
        # Group selection
        selected_group = st.selectbox("Select Group", list(st.session_state.groups.keys()))

    # Action-specific inputs
    with st.form(f"action_form_{action_type}"):
        if action_type == "rename_column":
            col1, col2 = st.columns(2)
            with col1:
                old_name = st.selectbox("Current Column Name", st.session_state.groups[selected_group].columns)
            with col2:
                new_name = st.text_input("New Column Name")
            
            action_data = {"type": "rename_column", "group": selected_group, "old_name": old_name, "new_name": new_name}
        
        elif action_type == "change_type":
            col1, col2 = st.columns(2)
            with col1:
                column = st.selectbox("Column Name", st.session_state.groups[selected_group].columns)
            with col2:
                new_type = st.selectbox("New Type", ["string", "int", "float", "datetime"])
            
            action_data = {"type": "change_type", "group": selected_group, "column": column, "new_type": new_type}
        
        elif action_type == "filter":
            col1, col2 = st.columns(2)
            with col1:
                column = st.selectbox("Column to Filter", st.session_state.groups[selected_group].columns)
            with col2:
                values = st.text_input("Values to Keep (comma-separated)", placeholder="value1, value2, value3")
            
            action_data = {"type": "filter", "group": selected_group, "column": column, "values": values}
        
        elif action_type == "create_column":
            new_column = st.text_input("New Column Name")
            formula = st.text_area("Formula (Pandas syntax)", 
                                 placeholder="Examples:\n'Fixed Value'\ndf['column1'] + df['column2']\ndf['text_col'].str.upper()\nnp.where(df['col'] > 0, 'Positive', 'Negative')",
                                 height=100)
            st.info("💡 Use 'df' to reference the dataframe, 'pd' for pandas functions, 'np' for numpy")
            
            action_data = {"type": "create_column", "group": selected_group, "new_column": new_column, "formula": formula}
        
        elif action_type == "drop_columns":
            columns = st.text_input("Columns to Drop (comma-separated)", 
                                  placeholder="column1, column2, column3")
            
            action_data = {"type": "drop_columns", "group": selected_group, "columns": columns}
        
        elif action_type == "merge":
            col1, col2 = st.columns(2)
            with col1:
                right_df = st.selectbox("Dataframe to Merge With", 
                                      [g for g in st.session_state.groups.keys() if g != selected_group])
            with col2:
                key_column = st.text_input("Key Column for Merging")
            
            action_data = {"type": "merge", "group": selected_group, "right_df": right_df, "key_column": key_column}
        
        elif action_type == "sort":
            col1, col2 = st.columns(2)
            with col1:
                column = st.selectbox("Column to Sort By", st.session_state.groups[selected_group].columns)
            with col2:
                order = st.selectbox("Sort Order", ["asc", "desc"], format_func=lambda x: "Ascending" if x == "asc" else "Descending")
            
            action_data = {"type": "sort", "group": selected_group, "column": column, "order": order}
        
        elif action_type == "group_aggregate":
            col1, col2 = st.columns(2)
            with col1:
                group_columns = st.text_input("Group By Columns (comma-separated)", 
                                            placeholder="column1, column2")
                agg_column = st.selectbox("Column to Aggregate", st.session_state.groups[selected_group].columns)
            with col2:
                agg_function = st.selectbox("Aggregation Function", 
                                          ["count", "sum", "mean", "max", "min"])
            
            action_data = {"type": "group_aggregate", "group": selected_group, 
                         "group_columns": group_columns, "agg_column": agg_column, "agg_function": agg_function}
        
        elif action_type == "remove_duplicates":
            columns = st.text_input("Columns to Check (comma-separated, leave empty for all columns)", 
                                  placeholder="column1, column2 or leave empty")
            
            action_data = {"type": "remove_duplicates", "group": selected_group, "columns": columns}
        
        elif action_type == "fill_missing":
            col1, col2 = st.columns(2)
            with col1:
                column = st.selectbox("Column with Missing Values", st.session_state.groups[selected_group].columns)
                method = st.selectbox("Fill Method", ["value", "forward", "backward", "mean"])
            with col2:
                if method == "value":
                    fill_value = st.text_input("Fill Value")
                else:
                    fill_value = ""
            
            action_data = {"type": "fill_missing", "group": selected_group, "column": column, 
                         "method": method, "fill_value": fill_value}
        
        elif action_type == "adjust_column_value":
            column = st.selectbox("Column to Adjust", st.session_state.groups[selected_group].columns)
            formula = st.text_area("Pandas Formula", 
                                 placeholder="Examples:\ndf['column'].str.replace('^Tỉnh ', '', regex=True)\ndf['column'].str.upper()\ndf['column'] * 2\ndf['column'].fillna('Default')",
                                 height=100)
            st.info("💡 Use 'df[column_name]' to reference columns. The formula will be applied to the selected column.")
            
            action_data = {"type": "adjust_column_value", "group": selected_group, "column": column, "formula": formula}
        
        # Add action button
        add_action = st.form_submit_button("➕ Add Action", type="primary")
        
        if add_action:
            if all(str(value).strip() for value in action_data.values() if value is not None):
                st.session_state.actions.append(action_data)
                st.success(f"✅ Action '{action_type.replace('_', ' ').title()}' added successfully!")
                st.rerun()
            else:
                st.error("❌ Please fill in all required fields.")

# Display existing actions
if st.session_state.actions:
    st.subheader("📋 Configured Actions")
    actions_df = pd.DataFrame([
        {
            "Step": i+1,
            "Action": action['type'].replace('_', ' ').title(),
            "Group": action['group'],
            "Details": f"{action.get('column', action.get('old_name', action.get('new_column', 'N/A')))}"
        }
        for i, action in enumerate(st.session_state.actions)
    ])
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.dataframe(actions_df, use_container_width=True)
    with col2:
        st.write("**Actions:**")
        for i, action in enumerate(st.session_state.actions):
            action_col1, action_col2, action_col3 = st.columns([1, 1, 1])
            with action_col1:
                if st.button(f"⬆️", key=f"up_{i}", help=f"Move action {i+1} up", disabled=(i == 0)):
                    st.session_state.actions[i], st.session_state.actions[i-1] = st.session_state.actions[i-1], st.session_state.actions[i]
                    st.rerun()
            with action_col2:
                if st.button(f"⬇️", key=f"down_{i}", help=f"Move action {i+1} down", disabled=(i == len(st.session_state.actions) - 1)):
                    st.session_state.actions[i], st.session_state.actions[i+1] = st.session_state.actions[i+1], st.session_state.actions[i]
                    st.rerun()
            with action_col3:
                if st.button(f"🗑️", key=f"remove_{i}", help=f"Remove action {i+1}"):
                    st.session_state.actions.pop(i)
                    st.rerun()

st.markdown("---")

# ====================
# STEP 3: PROCESS DATA
# ====================
st.markdown('<div class="section-header"><h2>🚀 Step 3: Process Data</h2></div>', unsafe_allow_html=True)
st.markdown("Execute all configured actions and view the final results")

if not st.session_state.groups:
    st.warning("⚠️ No groups found. Please create groups first.")
elif not st.session_state.actions:
    st.warning("⚠️ No actions configured. Please create actions first.")
else:
    # Show processing summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Groups Created", len(st.session_state.groups))
    with col2:
        st.metric("Actions Configured", len(st.session_state.actions))
    with col3:
        total_rows = sum(len(df) for df in st.session_state.groups.values())
        st.metric("Total Rows", total_rows)
    with col4:
        total_cols = sum(len(df.columns) for df in st.session_state.groups.values())
        st.metric("Total Columns", total_cols)
    
    # Process button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Process All Data", type="primary", use_container_width=True):
            with st.spinner("Processing data..."):
                # Group actions by dataframe
                grouped_actions = {}
                for action in st.session_state.actions:
                    group_name = action['group']
                    if group_name not in grouped_actions:
                        grouped_actions[group_name] = []
                    grouped_actions[group_name].append(action)
                
                # Process each group
                results = {}
                st.session_state.processed_groups = {}
                
                for group_name, actions in grouped_actions.items():
                    df = st.session_state.groups[group_name]
                    processed_df = apply_actions(df, actions, st.session_state.processed_groups)
                    results[group_name] = processed_df
                    st.session_state.processed_groups[group_name] = processed_df
                
                st.success("✅ Processing completed!")
                st.rerun()

# Display results if processed
if st.session_state.processed_groups:
    st.subheader("📊 Processing Results")
    
    for group_name, result_df in st.session_state.processed_groups.items():
        with st.expander(f"📈 Results for '{group_name}'", expanded=True):
            # Show metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Rows", len(result_df))
            with col2:
                st.metric("Total Columns", len(result_df.columns))
            with col3:
                original_rows = len(st.session_state.groups[group_name])
                change = len(result_df) - original_rows
                st.metric("Row Change", f"{change:+d}")
            with col4:
                actions_count = len([a for a in st.session_state.actions if a['group'] == group_name])
                st.metric("Actions Applied", actions_count)
            
            # Show data preview
            if len(result_df) > 0:
                st.subheader("Data Preview")
                st.dataframe(result_df.head(10), use_container_width=True)
                
                # Download buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    # Excel download
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        result_df.to_excel(writer, sheet_name='Processed_Data', index=False)
                    
                    st.download_button(
                        label=f"📥 Download Excel",
                        data=buffer.getvalue(),
                        file_name=f"{group_name}_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # CSV download
                    csv = result_df.to_csv(index=False)
                    st.download_button(
                        label=f"📥 Download CSV",
                        data=csv,
                        file_name=f"{group_name}_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("⚠️ No data remaining after processing")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>📊 DataFrameX - Streamline your data processing workflow</p>
    <p>Linh Nguyen - ShopeePay Credit PM </p>
</div>
""", unsafe_allow_html=True)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
