#!/usr/bin/env python3
"""Test database initialization and operations"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_database

def test_database():
    """Test all database operations"""
    print("🚀 Testing database initialization...")
    
    # Initialize database
    db_manager = init_database()
    print("✅ Database initialized successfully")
    
    # Test session creation
    session_id = db_manager.generate_session_id()
    print(f"✅ Generated session ID: {session_id}")
    
    # Test user creation
    user = db_manager.get_or_create_user(session_id)
    print(f"✅ Created user with ID: {user['id']}")
    print(f"   Session ID: {user['session_id']}")
    
    # Get templates
    templates = db_manager.get_all_templates(session_id)
    print(f"\n✅ Found {len(templates)} templates:")
    for template in templates:
        print(f"   - {template['name']} ({template['category']}) - Type: {template['type']}")
        if template['is_default']:
            print(f"     ⭐ Default Template")
    
    # Get structure configs
    configs = db_manager.get_all_structure_configs(session_id)
    print(f"\n✅ Found {len(configs)} structure configurations:")
    for config in configs:
        print(f"   - {config['name']} ({config['presentation_type']})")
        if config.get('sections'):
            print(f"     Sections: {len(config['sections'])} sections defined")
    
    # Test getting default template
    default_template = db_manager.get_default_template()
    if default_template:
        print(f"\n✅ Default template: {default_template['name']}")
    
    # Test getting structure by type
    report_structure = db_manager.get_structure_config_by_type('report')
    if report_structure:
        print(f"\n✅ Report structure found: {report_structure['name']}")
        print(f"   Sections in report structure:")
        for section in report_structure.get('sections', []):
            print(f"     - {section['name']} ({section.get('min_slides', 1)}-{section.get('max_slides', 3)} slides)")
    
    # Test user preferences
    preferences = db_manager.get_user_preferences(session_id)
    if preferences:
        print(f"\n✅ User preferences found:")
        print(f"   Auto-detect enabled: {preferences['auto_detect_enabled']}")
    else:
        print("\n✅ No user preferences yet (will be created on first use)")
        # Create preferences
        db_manager.update_user_preferences(session_id, {
            'preferred_presentation_type': 'report',
            'auto_detect_enabled': True
        })
        print("   Created default preferences")
    
    # Test saving generation history
    generation_data = {
        'session_id': session_id,
        'filename': 'test_presentation.pptx',
        'detected_type': 'report',
        'final_type': 'report',
        'total_slides': 15,
        'generation_time_seconds': 3.5,
        'input_type': 'text',
        'input_size': 1500,
        'model_used': 'llama3.2'
    }
    
    history = db_manager.save_generation_history(generation_data)
    print(f"\n✅ Saved generation history:")
    print(f"   ID: {history['id']}")
    print(f"   Filename: {history['filename']}")
    print(f"   Slides: {history['total_slides']}")
    
    # Test retrieving generation history
    histories = db_manager.get_generation_history(session_id)
    print(f"\n✅ Retrieved {len(histories)} generation history records")
    
    # Test custom template upload
    custom_template_data = {
        'name': 'My Custom Template',
        'description': 'A test custom template',
        'category': 'custom',
        'file_path': '/path/to/custom_template.pptx',
        'is_public': False,
        'brand_colors': {'primary': '#FF0000', 'secondary': '#00FF00'}
    }
    
    custom_template = db_manager.save_user_template(session_id, custom_template_data)
    print(f"\n✅ Saved custom template:")
    print(f"   ID: {custom_template['id']}")
    print(f"   Name: {custom_template['name']}")
    print(f"   Type: {custom_template['type']}")
    
    # Test custom structure configuration
    custom_structure_data = {
        'name': 'My Custom Structure',
        'description': 'A test custom structure',
        'presentation_type': 'custom_report',
        'sections': [
            {'name': 'Introduction', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Main Content', 'min_slides': 3, 'max_slides': 5, 'bullets_per_slide': 5},
            {'name': 'Conclusion', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 3}
        ],
        'global_settings': {'include_agenda': True},
        'is_public': False
    }
    
    custom_structure = db_manager.save_custom_structure(session_id, custom_structure_data)
    print(f"\n✅ Saved custom structure:")
    print(f"   ID: {custom_structure['id']}")
    print(f"   Name: {custom_structure['name']}")
    print(f"   Sections: {len(custom_structure.get('section_templates', []))} sections")
    
    # Test prompt templates (for LangChain)
    prompt_template = db_manager.get_prompt_template('presentation_type_detection')
    if prompt_template:
        print(f"\n✅ Found prompt template: {prompt_template['name']}")
        print(f"   Type: {prompt_template['template_type']}")
        print(f"   Parser: {prompt_template['output_parser']}")
    
    # Get statistics
    stats = db_manager.get_statistics()
    print("\n📊 Database Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ All database tests completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = test_database()
        if success:
            print("\n🎉 Database is ready for use!")
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)