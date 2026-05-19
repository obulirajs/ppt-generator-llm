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


def test_presentation_versioning():
    """Feature 001 — Presentation Versioning Foundation: DB-layer tests.

    Runs against an isolated tmp SQLite DB so the dev DB stays clean.
    Covers the six scenarios from specs/001-…/tasks.md Task 10.
    """
    import tempfile
    import shutil
    from config import DATABASE_CONFIG, VERSIONING_CONFIG
    from database.db_manager import DatabaseManager
    from database.models import PresentationVersion

    print("\n🚀 Testing presentation versioning (feature 001) on isolated tmp DB...")

    tmp_dir = tempfile.mkdtemp(prefix='ppt_versioning_test_')
    tmp_db_path = os.path.join(tmp_dir, 'test.db')
    original_path = DATABASE_CONFIG['path']
    DATABASE_CONFIG['path'] = tmp_db_path
    db = None

    try:
        db = DatabaseManager()
        print(f"✅ Isolated test DB at {tmp_db_path}")

        SID_A = 'test-sid-A'
        SID_B = 'test-sid-B'

        # Seed parent generation_history rows so lineage_id values are realistic
        gh_a = db.save_generation_history({
            'session_id': SID_A, 'filename': 'a.pptx', 'file_path': '/tmp/a.pptx',
            'input_type': 'text', 'input_size': 100, 'model_used': 'llama3.2',
        })
        gh_b = db.save_generation_history({
            'session_id': SID_B, 'filename': 'b.pptx', 'file_path': '/tmp/b.pptx',
            'input_type': 'text', 'input_size': 200, 'model_used': 'llama3.2',
        })
        lid_a, lid_b = gh_a['id'], gh_b['id']

        # ---- 1. save_presentation_version roundtrips via get_version ----
        row = db.save_presentation_version({
            'lineage_id': lid_a, 'version_number': 1, 'label': 'Initial generation',
            'note': None, 'slide_structure': {'slides': [{'title': 'Hello'}]},
            'file_path': '/tmp/a.pptx', 'filename': 'a.pptx',
            'is_stub': False, 'session_id': SID_A,
        })
        assert row['id']
        fetched = db.get_version(lid_a, 1, SID_A)
        assert fetched is not None
        for key in ('id', 'lineage_id', 'version_number', 'label', 'note',
                    'slide_structure', 'file_path', 'filename', 'is_stub',
                    'session_id', 'created_at'):
            assert key in fetched, f"missing key {key} in get_version result"
        assert fetched['slide_structure'] == {'slides': [{'title': 'Hello'}]}
        assert fetched['is_stub'] is False
        print("✅ Test 1: save_presentation_version + roundtrip via get_version")

        # ---- 2. Unique (lineage_id, version_number) constraint ----
        raised = False
        try:
            db.save_presentation_version({
                'lineage_id': lid_a, 'version_number': 1, 'label': 'duplicate',
                'note': None, 'slide_structure': None,
                'file_path': None, 'filename': None,
                'is_stub': False, 'session_id': SID_A,
            })
        except Exception as e:
            raised = True
            msg = str(e).upper()
            assert 'UNIQUE' in msg or 'INTEGRITY' in msg, f"unexpected error: {e}"
        assert raised, "expected IntegrityError on duplicate (lineage_id, version_number)"
        print("✅ Test 2: unique (lineage_id, version_number) constraint enforced")

        # ---- 3. get_lineages_for_session aggregation ----
        # Seed v2 of lineage A to exercise aggregation; seed v1 of lineage B for cross-session
        db.save_presentation_version({
            'lineage_id': lid_a, 'version_number': 2, 'label': 'tighten slide 1',
            'note': None, 'slide_structure': {'slides': [{'title': 'Hello v2'}]},
            'file_path': '/tmp/a2.pptx', 'filename': 'a2.pptx',
            'is_stub': False, 'session_id': SID_A,
        })
        db.save_presentation_version({
            'lineage_id': lid_b, 'version_number': 1, 'label': 'Initial generation',
            'note': None, 'slide_structure': {'slides': [{'title': 'B'}]},
            'file_path': '/tmp/b.pptx', 'filename': 'b.pptx',
            'is_stub': False, 'session_id': SID_B,
        })
        lineages_a = db.get_lineages_for_session(SID_A)
        assert len(lineages_a) == 1
        la = lineages_a[0]
        assert la['lineage_id'] == lid_a
        assert la['latest_version_number'] == 2
        assert la['latest_version_label'] == 'tighten slide 1'
        assert la['total_versions'] == 2
        lineages_b = db.get_lineages_for_session(SID_B)
        assert len(lineages_b) == 1 and lineages_b[0]['total_versions'] == 1
        print("✅ Test 3: get_lineages_for_session aggregates correctly per session")

        # ---- 4. get_versions_for_lineage chronological + existence-leak guard ----
        versions = db.get_versions_for_lineage(lid_a, SID_A)
        assert versions is not None
        assert [v['version_number'] for v in versions] == [1, 2], "oldest-first required"
        assert db.get_versions_for_lineage(999999, SID_A) is None
        assert db.get_versions_for_lineage(lid_a, SID_B) is None
        print("✅ Test 4: get_versions_for_lineage chronological + existence-leak guard")

        # ---- 5. get_version + lineage_exists_for_session existence-leak guard ----
        assert db.get_version(lid_a, 1, SID_A) is not None
        assert db.get_version(lid_a, 1, SID_B) is None
        assert db.get_version(lid_a, 999, SID_A) is None
        assert db.lineage_exists_for_session(lid_a, SID_A) is True
        assert db.lineage_exists_for_session(lid_a, SID_B) is False
        assert db.lineage_exists_for_session(999999, SID_A) is False
        print("✅ Test 5: get_version + lineage_exists_for_session existence-leak guard")

        # ---- 6. Backfill idempotency ----
        gh_extra_ids = []
        for i in range(3):
            gh = db.save_generation_history({
                'session_id': f'backfill-sid-{i}', 'filename': f'extra{i}.pptx',
                'file_path': f'/tmp/extra{i}.pptx', 'input_type': 'text',
                'input_size': 50, 'model_used': 'llama3.2',
            })
            gh_extra_ids.append(gh['id'])

        with db.get_session() as s:
            pre_count = s.query(PresentationVersion).count()
        db._backfill_v1_for_existing_presentations()
        with db.get_session() as s:
            post_count = s.query(PresentationVersion).count()
            # Materialize to dicts inside the session — avoids detached-instance
            # errors after the `with` block closes (matches CLAUDE.md convention).
            stubs_for_extras = [
                v.to_dict() for v in
                s.query(PresentationVersion)
                .filter(PresentationVersion.lineage_id.in_(gh_extra_ids))
                .all()
            ]
        assert post_count - pre_count == 3, f"expected 3 new stubs, got {post_count - pre_count}"
        assert len(stubs_for_extras) == 3
        for stub in stubs_for_extras:
            assert stub['is_stub'] is True
            assert stub['slide_structure'] is None
            assert stub['label'] == VERSIONING_CONFIG['v1_label']
            assert stub['version_number'] == 1
        # Second run must be a strict no-op
        db._backfill_v1_for_existing_presentations()
        with db.get_session() as s:
            post_count_2 = s.query(PresentationVersion).count()
        assert post_count_2 == post_count, "backfill not idempotent on second run"
        print("✅ Test 6: backfill inserts stubs once and is idempotent on rerun")

        print("\n✅ All presentation versioning DB tests passed!")
        return True

    finally:
        DATABASE_CONFIG['path'] = original_path
        if db is not None:
            try:
                db.engine.dispose()
            except Exception:
                pass
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        ok1 = test_database()
        ok2 = test_presentation_versioning()
        if ok1 and ok2:
            print("\n🎉 Database is ready for use!")
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)