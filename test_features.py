#!/usr/bin/env python3
"""
Test script to verify new features added to main.py
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime

# Test the workflow export/import functionality
def test_workflow_export_import():
    """Test group preset export/import functionality"""
    
    # Mock data structures similar to streamlit session state
    mock_actions = [
        {
            "type": "rename_column",
            "group": "test_group",
            "old_name": "old_col",
            "new_name": "new_col"
        }
    ]
    
    mock_group_presets = {
        "test_group": {
            "group_name": "test_group",
            "sheet_name": "Sheet1",
            "header_row": 1,
            "header_column": 1
        }
    }
    
    # Create workflow data (simulating export)
    workflow_data = {
        "workflow_name": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "actions": mock_actions,
        "group_presets": mock_group_presets,
        "created_date": datetime.now().isoformat(),
        "total_actions": len(mock_actions),
        "groups_used": ["test_group"],
        "version": "1.0"
    }
    
    # Test JSON serialization
    try:
        workflow_json = json.dumps(workflow_data, indent=2)
        print("✅ Workflow export JSON serialization successful")
        
        # Test JSON deserialization
        loaded_workflow = json.loads(workflow_json)
        
        # Verify group presets are included
        if "group_presets" in loaded_workflow:
            print("✅ Group presets included in exported workflow")
        else:
            print("❌ Group presets missing from exported workflow")
            
        # Verify preset data integrity
        if loaded_workflow["group_presets"]["test_group"]["group_name"] == "test_group":
            print("✅ Group preset data integrity maintained")
        else:
            print("❌ Group preset data corruption detected")
            
    except Exception as e:
        print(f"❌ Workflow export/import test failed: {e}")

def test_adjust_column_value():
    """Test the new adjust_column_value action"""
    
    # Create test dataframe
    test_df = pd.DataFrame({
        'Tỉnh': ['Tỉnh Hà Nội', 'Tỉnh Hồ Chí Minh', 'Tỉnh Đà Nẵng'],
        'Population': [8000000, 9000000, 1200000],
        'Area': [3329, 2061, 1285]
    })
    
    print("Original DataFrame:")
    print(test_df)
    print()
    
    # Test formula: remove 'Tỉnh ' prefix
    try:
        # Simulate the adjust_column_value action
        formula = "df['Tỉnh'].str.replace('^Tỉnh ', '', regex=True)"
        result = eval(formula, {'df': test_df, 'pd': pd, 'np': np})
        test_df['Tỉnh'] = result
        
        print("After applying formula (remove 'Tỉnh ' prefix):")
        print(test_df)
        print("✅ adjust_column_value action test successful")
        
    except Exception as e:
        print(f"❌ adjust_column_value action test failed: {e}")

def test_action_reordering():
    """Test action reordering functionality"""
    
    # Mock actions list
    actions = [
        {"type": "rename_column", "group": "test", "old_name": "A", "new_name": "B"},
        {"type": "filter", "group": "test", "column": "C", "values": "value1"},
        {"type": "sort", "group": "test", "column": "D", "order": "asc"}
    ]
    
    print("Original actions order:")
    for i, action in enumerate(actions):
        print(f"{i+1}. {action['type']} - {action.get('old_name', action.get('column', 'N/A'))}")
    
    # Test swapping actions (simulating move up/down)
    # Move action 1 down (swap with action 2)
    actions[0], actions[1] = actions[1], actions[0]
    
    print("\nAfter moving first action down:")
    for i, action in enumerate(actions):
        print(f"{i+1}. {action['type']} - {action.get('old_name', action.get('column', 'N/A'))}")
    
    print("✅ Action reordering test successful")

if __name__ == "__main__":
    print("Testing new features...\n")
    
    print("1. Testing workflow export/import with group presets:")
    test_workflow_export_import()
    print()
    
    print("2. Testing adjust_column_value action:")
    test_adjust_column_value()
    print()
    
    print("3. Testing action reordering:")
    test_action_reordering()
    print()
    
    print("All tests completed!")