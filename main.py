import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import re
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Excel Automation Processor",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'groups' not in st.session_state:
    st.session_state.groups = {}
if 'actions' not in st.session_state:
    st.session_state.actions = []
if 'processed_groups' not in st.session_state:
    st.session_state.processed_groups = {}

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
        
        except Exception as e:
            st.error(f"Error applying action {action['type']}: {str(e)}")
    
    return result_df

# Main app
st.title("📊 Excel Automation Processor")
st.markdown("Process Excel files automatically with custom grouping and data transformations")

# Sidebar for navigation
st.sidebar.title("Navigation")
tab = st.sidebar.radio("Select Operation", ["Create Groups", "Create Actions", "Process Data"])

# Workflow Management in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Workflow Management")

# Export workflow
if st.session_state.actions:
    workflow_data = {
        "workflow_name": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "actions": st.session_state.actions,
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
        import json
        workflow_content = json.loads(uploaded_workflow.read())
        
        if st.sidebar.button("Load Workflow", type="primary"):
            if "actions" in workflow_content:
                st.session_state.actions = workflow_content["actions"]
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

if tab == "Create Groups":
    st.header("1. Create Groups")
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
        st.subheader("Existing Groups")
        for group_name, df in st.session_state.groups.items():
            with st.expander(f"📁 {group_name} ({len(df)} rows, {len(df.columns)} columns)"):
                st.dataframe(df.head(), use_container_width=True)

elif tab == "Workflow Management":
    st.header("🔄 Workflow Management")
    st.markdown("Manage your action workflows - save, load, and reuse them across different datasets")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Export Current Workflow")
        if st.session_state.actions:
            workflow_preview = pd.DataFrame([
                {
                    "Action": action['type'].replace('_', ' ').title(),
                    "Group": action['group'],
                    "Details": str(action)[:50] + "..." if len(str(action)) > 50 else str(action)
                }
                for action in st.session_state.actions
            ])
            
            st.dataframe(workflow_preview, use_container_width=True)
            
            # Workflow metadata
            st.info(f"📊 **Workflow Summary:**\n- Total Actions: {len(st.session_state.actions)}\n- Groups Used: {len(set(action['group'] for action in st.session_state.actions))}")
            
            # Export with custom name
            workflow_name = st.text_input("Workflow Name", value=f"workflow_{datetime.now().strftime('%Y%m%d')}")
            
            if st.button("📤 Export Workflow", type="primary"):
                workflow_data = {
                    "workflow_name": workflow_name,
                    "actions": st.session_state.actions,
                    "created_date": datetime.now().isoformat(),
                    "total_actions": len(st.session_state.actions),
                    "groups_used": list(set(action['group'] for action in st.session_state.actions)),
                    "version": "1.0"
                }
                
                workflow_json = json.dumps(workflow_data, indent=2)
                st.download_button(
                    label="💾 Download Workflow JSON",
                    data=workflow_json,
                    file_name=f"{workflow_name}.json",
                    mime="application/json"
                )
        else:
            st.warning("⚠️ No actions to export. Create some actions first.")
    
    with col2:
        st.subheader("📤 Import Workflow")
        uploaded_workflow = st.file_uploader(
            "Upload Workflow JSON",
            type=['json'],
            help="Upload a previously saved workflow file"
        )
        
        if uploaded_workflow is not None:
            try:
                workflow_content = json.loads(uploaded_workflow.read())
                
                # Display workflow info
                if "workflow_name" in workflow_content:
                    st.success(f"✅ Workflow loaded: **{workflow_content['workflow_name']}**")
                    
                    if "created_date" in workflow_content:
                        created_date = datetime.fromisoformat(workflow_content["created_date"]).strftime("%Y-%m-%d %H:%M")
                        st.info(f"📅 Created: {created_date}")
                    
                    if "total_actions" in workflow_content:
                        st.info(f"🔧 Actions: {workflow_content['total_actions']}")
                    
                    if "groups_used" in workflow_content:
                        st.info(f"📁 Groups: {', '.join(workflow_content['groups_used'])}")
                    
                    # Preview actions
                    if "actions" in workflow_content:
                        preview_df = pd.DataFrame([
                            {
                                "Action": action['type'].replace('_', ' ').title(),
                                "Group": action['group']
                            }
                            for action in workflow_content["actions"]
                        ])
                        st.dataframe(preview_df, use_container_width=True)
                        
                        # Load workflow
                        col1_btn, col2_btn = st.columns(2)
                        with col1_btn:
                            if st.button("🔄 Replace Current Actions", type="primary"):
                                st.session_state.actions = workflow_content["actions"]
                                st.success(f"✅ Loaded {len(workflow_content['actions'])} actions!")
                                st.rerun()
                        
                        with col2_btn:
                            if st.button("➕ Append to Current Actions"):
                                st.session_state.actions.extend(workflow_content["actions"])
                                st.success(f"✅ Added {len(workflow_content['actions'])} actions!")
                                st.rerun()
                else:
                    st.error("❌ Invalid workflow file format")
                    
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file")
            except Exception as e:
                st.error(f"❌ Error loading workflow: {str(e)}")
    
    # Workflow templates
    st.markdown("---")
    st.subheader("📋 Workflow Templates")
    
    templates = {
        "Data Cleaning": [
            {"type": "remove_duplicates", "group": "your_group", "columns": ""},
            {"type": "fill_missing", "group": "your_group", "column": "column_name", "method": "value", "fill_value": "0"}
        ],
        "Sales Analysis": [
            {"type": "create_column", "group": "your_group", "new_column": "Total_Amount", "formula": "df['Quantity'] * df['Unit_Price']"},
            {"type": "group_aggregate", "group": "your_group", "group_columns": "Product", "agg_column": "Total_Amount", "agg_function": "sum"},
            {"type": "sort", "group": "your_group", "column": "Total_Amount", "order": "desc"}
        ],
        "Data Standardization": [
            {"type": "change_type", "group": "your_group", "column": "date_column", "new_type": "datetime"},
            {"type": "rename_column", "group": "your_group", "old_name": "old_name", "new_name": "standardized_name"},
            {"type": "create_column", "group": "your_group", "new_column": "clean_text", "formula": "df['text_column'].str.upper().str.strip()"}
        ]
    }
    
    selected_template = st.selectbox("Choose a template", list(templates.keys()))
    
    col1_temp, col2_temp = st.columns([3, 1])
    with col1_temp:
        st.json(templates[selected_template])
    
    with col2_temp:
        if st.button("📥 Load Template"):
            st.session_state.actions.extend(templates[selected_template])
            st.success(f"✅ Added {selected_template} template!")
            st.rerun()
    st.header("2. Create Actions")
    st.markdown("Define data processing actions to be applied to your groups")
    
    if not st.session_state.groups:
        st.warning("⚠️ Please create at least one group first before defining actions.")
    else:
        # Action type selection
        action_type = st.selectbox(
            "Select Action Type",
            ["rename_column", "change_type", "filter", "create_column", "drop_columns", "merge", 
             "sort", "group_aggregate", "remove_duplicates", "fill_missing"]
        )
        
        # Group selection
        selected_group = st.selectbox("Select Group/Dataframe", list(st.session_state.groups.keys()))
        
        # Action-specific inputs
        with st.form(f"action_form_{action_type}"):
            if action_type == "rename_column":
                st.subheader("Rename Column")
                col1, col2 = st.columns(2)
                with col1:
                    old_name = st.selectbox("Current Column Name", st.session_state.groups[selected_group].columns)
                with col2:
                    new_name = st.text_input("New Column Name")
                
                action_data = {"type": "rename_column", "group": selected_group, "old_name": old_name, "new_name": new_name}
            
            elif action_type == "change_type":
                st.subheader("Change Column Type")
                col1, col2 = st.columns(2)
                with col1:
                    column = st.selectbox("Column Name", st.session_state.groups[selected_group].columns)
                with col2:
                    new_type = st.selectbox("New Type", ["string", "int", "float", "datetime"])
                
                action_data = {"type": "change_type", "group": selected_group, "column": column, "new_type": new_type}
            
            elif action_type == "filter":
                st.subheader("Filter Data")
                col1, col2 = st.columns(2)
                with col1:
                    column = st.selectbox("Column to Filter", st.session_state.groups[selected_group].columns)
                with col2:
                    values = st.text_input("Values to Keep (comma-separated)", placeholder="value1, value2, value3")
                
                action_data = {"type": "filter", "group": selected_group, "column": column, "values": values}
            
            elif action_type == "create_column":
                st.subheader("Create New Column")
                new_column = st.text_input("New Column Name")
                formula = st.text_area("Formula (Pandas syntax)", 
                                     placeholder="Examples:\n'Fixed Value'\ndf['column1'] + df['column2']\ndf['text_col'].str.upper()\nnp.where(df['col'] > 0, 'Positive', 'Negative')",
                                     height=100)
                st.info("💡 Use 'df' to reference the dataframe, 'pd' for pandas functions, 'np' for numpy")
                
                action_data = {"type": "create_column", "group": selected_group, "new_column": new_column, "formula": formula}
            
            elif action_type == "drop_columns":
                st.subheader("Drop Columns")
                columns = st.text_input("Columns to Drop (comma-separated)", 
                                      placeholder="column1, column2, column3")
                
                action_data = {"type": "drop_columns", "group": selected_group, "columns": columns}
            
            elif action_type == "merge":
                st.subheader("Merge Dataframes")
                col1, col2 = st.columns(2)
                with col1:
                    right_df = st.selectbox("Dataframe to Merge With", 
                                          [g for g in st.session_state.groups.keys() if g != selected_group])
                with col2:
                    key_column = st.text_input("Key Column for Merging")
                
                action_data = {"type": "merge", "group": selected_group, "right_df": right_df, "key_column": key_column}
            
            elif action_type == "sort":
                st.subheader("Sort Data")
                col1, col2 = st.columns(2)
                with col1:
                    column = st.selectbox("Column to Sort By", st.session_state.groups[selected_group].columns)
                with col2:
                    order = st.selectbox("Sort Order", ["asc", "desc"], format_func=lambda x: "Ascending" if x == "asc" else "Descending")
                
                action_data = {"type": "sort", "group": selected_group, "column": column, "order": order}
            
            elif action_type == "group_aggregate":
                st.subheader("Group and Aggregate")
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
                st.subheader("Remove Duplicates")
                columns = st.text_input("Columns to Check (comma-separated, leave empty for all columns)", 
                                      placeholder="column1, column2 or leave empty")
                
                action_data = {"type": "remove_duplicates", "group": selected_group, "columns": columns}
            
            elif action_type == "fill_missing":
                st.subheader("Fill Missing Values")
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
            
            # Add action button
            add_action = st.form_submit_button("Add Action", type="primary")
            
            if add_action:
                if all(value for value in action_data.values() if value != ""):
                    st.session_state.actions.append(action_data)
                    st.success(f"✅ Action '{action_type}' added successfully!")
                else:
                    st.error("❌ Please fill in all required fields.")
        
        # Display existing actions
        if st.session_state.actions:
            st.subheader("Configured Actions")
            for i, action in enumerate(st.session_state.actions):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{i+1}.** {action['type'].replace('_', ' ').title()} on '{action['group']}'")
                with col2:
                    if st.button("Remove", key=f"remove_{i}"):
                        st.session_state.actions.pop(i)
                        st.rerun()

elif tab == "Create Actions":
    st.header("2. Create Actions")
    st.markdown("Define data processing actions to be applied to your groups")
    
    if not st.session_state.groups:
        st.warning("⚠️ Please create at least one group first before defining actions.")
    else:
        # Action type selection
        action_type = st.selectbox(
            "Select Action Type",
            ["rename_column", "change_type", "filter", "create_column", "drop_columns", "merge", 
             "sort", "group_aggregate", "remove_duplicates", "fill_missing"]
        )
        
        # Group selection
        selected_group = st.selectbox("Select Group/Dataframe", list(st.session_state.groups.keys()))
        
        # Action-specific inputs
        with st.form(f"action_form_{action_type}"):
            if action_type == "rename_column":
                st.subheader("Rename Column")
                col1, col2 = st.columns(2)
                with col1:
                    old_name = st.selectbox("Current Column Name", st.session_state.groups[selected_group].columns)
                with col2:
                    new_name = st.text_input("New Column Name")
                
                action_data = {"type": "rename_column", "group": selected_group, "old_name": old_name, "new_name": new_name}
            
            elif action_type == "change_type":
                st.subheader("Change Column Type")
                col1, col2 = st.columns(2)
                with col1:
                    column = st.selectbox("Column Name", st.session_state.groups[selected_group].columns)
                with col2:
                    new_type = st.selectbox("New Type", ["string", "int", "float", "datetime"])
                
                action_data = {"type": "change_type", "group": selected_group, "column": column, "new_type": new_type}
            
            elif action_type == "filter":
                st.subheader("Filter Data")
                col1, col2 = st.columns(2)
                with col1:
                    column = st.selectbox("Column to Filter", st.session_state.groups[selected_group].columns)
                with col2:
                    values = st.text_input("Values to Keep (comma-separated)", placeholder="value1, value2, value3")
                
                action_data = {"type": "filter", "group": selected_group, "column": column, "values": values}
            
            elif action_type == "create_column":
                st.subheader("Create New Column")
                new_column = st.text_input("New Column Name")
                formula = st.text_area("Formula (Pandas syntax)", 
                                     placeholder="Examples:\n'Fixed Value'\ndf['column1'] + df['column2']\ndf['text_col'].str.upper()\nnp.where(df['col'] > 0, 'Positive', 'Negative')",
                                     height=100)
                st.info("💡 Use 'df' to reference the dataframe, 'pd' for pandas functions, 'np' for numpy")
                
                action_data = {"type": "create_column", "group": selected_group, "new_column": new_column, "formula": formula}
            
            elif action_type == "drop_columns":
                st.subheader("Drop Columns")
                columns = st.text_input("Columns to Drop (comma-separated)", 
                                      placeholder="column1, column2, column3")
                
                action_data = {"type": "drop_columns", "group": selected_group, "columns": columns}
            
            elif action_type == "merge":
                st.subheader("Merge Dataframes")
                col1, col2 = st.columns(2)
                with col1:
                    right_df = st.selectbox("Dataframe to Merge With", 
                                          [g for g in st.session_state.groups.keys() if g != selected_group])
                with col2:
                    key_column = st.text_input("Key Column for Merging")
                
                action_data = {"type": "merge", "group": selected_group, "right_df": right_df, "key_column": key_column}
            
            elif action_type == "sort":
                st.subheader("Sort Data")
                col1, col2 = st.columns(2)
                with col1:
                    column = st.selectbox("Column to Sort By", st.session_state.groups[selected_group].columns)
                with col2:
                    order = st.selectbox("Sort Order", ["asc", "desc"], format_func=lambda x: "Ascending" if x == "asc" else "Descending")
                
                action_data = {"type": "sort", "group": selected_group, "column": column, "order": order}
            
            elif action_type == "group_aggregate":
                st.subheader("Group and Aggregate")
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
                st.subheader("Remove Duplicates")
                columns = st.text_input("Columns to Check (comma-separated, leave empty for all columns)", 
                                      placeholder="column1, column2 or leave empty")
                
                action_data = {"type": "remove_duplicates", "group": selected_group, "columns": columns}
            
            elif action_type == "fill_missing":
                st.subheader("Fill Missing Values")
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
            
            # Add action button
            add_action = st.form_submit_button("Add Action", type="primary")
            
            if add_action:
                if all(value for value in action_data.values() if value != ""):
                    st.session_state.actions.append(action_data)
                    st.success(f"✅ Action '{action_type}' added successfully!")
                    st.info("💡 Go to 'Process Data' tab to execute all actions")
                else:
                    st.error("❌ Please fill in all required fields.")
        
        # Display existing actions
        if st.session_state.actions:
            st.subheader("Configured Actions")
            for i, action in enumerate(st.session_state.actions):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{i+1}.** {action['type'].replace('_', ' ').title()} on '{action['group']}'")
                with col2:
                    if st.button("Remove", key=f"remove_{i}", help="Remove this action"):
                        st.session_state.actions.pop(i)
                        st.rerun()
            
            # Navigation hint
            st.info("🎯 **Next Step:** Go to the 'Process Data' tab to execute all configured actions!")
        
        else:
            st.info("ℹ️ No actions configured yet. Add your first action above!")

elif tab == "Process Data":
    st.header("3. Process Data")
    st.markdown("Execute all configured actions and view the final results")
    
    if not st.session_state.groups:
        st.warning("⚠️ No groups found. Please create groups first.")
    elif not st.session_state.actions:
        st.warning("⚠️ No actions configured. Please create actions first.")
    else:
        # Show summary
        st.subheader("Processing Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Groups Created", len(st.session_state.groups))
        with col2:
            st.metric("Actions Configured", len(st.session_state.actions))
        
        # Show configured actions preview
        st.subheader("Actions to Execute")
        actions_df = pd.DataFrame([
            {
                "Action": action['type'].replace('_', ' ').title(),
                "Group": action['group'],
                "Details": str(action).replace(action['group'], '').replace(action['type'], '')[:50] + "..."
            }
            for action in st.session_state.actions
        ])
        st.dataframe(actions_df, use_container_width=True)
        
        # Process button - Main CTA
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            process_button = st.button("🚀 Process Now", type="primary", use_container_width=True, 
                                     help="Execute all configured actions and display results")
        
        if process_button:
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
                st.session_state.processed_groups = {}  # Reset processed groups
                
                for group_name, actions in grouped_actions.items():
                    df = st.session_state.groups[group_name]
                    processed_df = apply_actions(df, actions, st.session_state.processed_groups)
                    results[group_name] = processed_df
                    st.session_state.processed_groups[group_name] = processed_df  # Store for merge references
                
                # Display results
                st.success("✅ Processing completed!")
                st.markdown("---")
                
                for group_name, result_df in results.items():
                    st.subheader(f"📊 Results for '{group_name}'")
                    
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
                        actions_count = len(grouped_actions[group_name])
                        st.metric("Actions Applied", actions_count)
                    
                    # Show first 10 rows preview
                    st.subheader("📋 First 10 Rows Preview")
                    if len(result_df) > 0:
                        preview_df = result_df.head(10)
                        st.dataframe(preview_df, use_container_width=True)
                        
                        # Show data info
                        st.info(f"Showing {len(preview_df)} of {len(result_df)} total rows")
                        
                        # Column info
                        with st.expander("📝 Column Information"):
                            col_info = pd.DataFrame({
                                'Column': result_df.columns,
                                'Data Type': result_df.dtypes.astype(str),
                                'Non-Null Count': result_df.count(),
                                'Null Count': result_df.isnull().sum()
                            })
                            st.dataframe(col_info, use_container_width=True)
                    else:
                        st.warning("⚠️ No data remaining after processing")
                    
                    # Download section
                    st.subheader("💾 Download Results")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Excel download
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            result_df.to_excel(writer, sheet_name='Processed_Data', index=False)
                        
                        st.download_button(
                            label=f"📥 Download {group_name} (Excel)",
                            data=buffer.getvalue(),
                            file_name=f"{group_name}_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    with col2:
                        # CSV download
                        csv = result_df.to_csv(index=False)
                        st.download_button(
                            label=f"📥 Download {group_name} (CSV)",
                            data=csv,
                            file_name=f"{group_name}_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    st.markdown("---")
        
        # Show sample of original data for comparison
        if st.session_state.groups:
            st.subheader("📂 Original Data Preview")
            for group_name, df in st.session_state.groups.items():
                with st.expander(f"Original: {group_name} ({len(df)} rows)"):
                    st.dataframe(df.head(5), use_container_width=True)
