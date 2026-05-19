"""
Database Manager for PPT Generator
Handles all database operations and initialization
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from database.models import (
    Base, User, Template, StructureConfig, SectionTemplate,
    GenerationHistory, UserPreference, ContentAnalysis, PromptTemplate,
    PresentationVersion
)
from config import DATABASE_CONFIG, PRESENTATION_TYPES, TEMPLATE_CONFIG, VERSIONING_CONFIG

class DatabaseManager:
    """Manages all database operations for the PPT Generator"""
    
    def __init__(self):
        """Initialize database connection and create tables"""
        # Create database directory if it doesn't exist
        db_dir = os.path.dirname(DATABASE_CONFIG['path'])
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Initialize database engine
        self.engine = create_engine(
            f"sqlite:///{DATABASE_CONFIG['path']}",
            echo=DATABASE_CONFIG['echo'],
            pool_size=DATABASE_CONFIG['pool_size'],
            max_overflow=DATABASE_CONFIG['max_overflow']
        )
        
        # Create session factory
        self.SessionFactory = scoped_session(sessionmaker(bind=self.engine))
        
        # Create tables if they don't exist
        self._create_tables()

        # Initialize default data
        self._initialize_defaults()

        # Backfill v1 stub rows for any pre-existing presentations (idempotent)
        self._backfill_v1_for_existing_presentations()

    def _create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(self.engine)
        print("✅ Database tables created successfully")
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ============== User Management ==============
    
    def get_or_create_user(self, session_id: str) -> Dict:
        """Get existing user or create new one with session ID"""
        with self.get_session() as session:
            user = session.query(User).filter_by(session_id=session_id).first()
            if not user:
                user = User(session_id=session_id)
                session.add(user)
                session.commit()
                session.refresh(user)  # Refresh to get the ID
                
                # Create default preferences for new user
                self._create_user_preferences(session, user)
            
            # Return dictionary representation to avoid detached instance error
            return user.to_dict()
    
    def _create_user_preferences(self, session, user: User):
        """Create default preferences for a new user"""
        preferences = UserPreference(
            session_id=user.session_id,
            user_id=user.id,
            auto_detect_enabled=True,
            ui_preferences={'theme': 'light', 'show_tips': True},
            generation_preferences={'max_slides': 30, 'bullets_per_slide': 5}
        )
        session.add(preferences)
        session.commit()
    
    # ============== Template Management ==============
    
    def get_all_templates(self, session_id: Optional[str] = None) -> List[Dict]:
        """Get all available templates for a user"""
        with self.get_session() as session:
            query = session.query(Template)
            
            # Get system templates and public templates
            query = query.filter(
                (Template.type == 'system') | 
                (Template.is_public == True) |
                (Template.owner_session_id == session_id)
            )
            
            templates = query.all()
            return [template.to_dict() for template in templates]
    
    def get_template_by_id(self, template_id: int) -> Optional[Dict]:
        """Get a specific template by ID"""
        with self.get_session() as session:
            template = session.query(Template).filter_by(id=template_id).first()
            return template.to_dict() if template else None
    
    def get_default_template(self) -> Optional[Dict]:
        """Get the default template"""
        with self.get_session() as session:
            template = session.query(Template).filter_by(is_default=True).first()
            return template.to_dict() if template else None
    
    def save_user_template(self, session_id: str, template_data: Dict) -> Dict:
        """Save a user-uploaded template"""
        with self.get_session() as session:
            # Get user ID from session
            user = session.query(User).filter_by(session_id=session_id).first()
            if not user:
                user = User(session_id=session_id)
                session.add(user)
                session.commit()
                session.refresh(user)
            
            template = Template(
                name=template_data['name'],
                description=template_data.get('description'),
                category=template_data.get('category', 'custom'),
                type='user_uploaded',
                file_path=template_data['file_path'],
                thumbnail_path=template_data.get('thumbnail_path'),
                is_public=template_data.get('is_public', False),
                brand_colors=template_data.get('brand_colors'),
                font_settings=template_data.get('font_settings'),
                owner_session_id=session_id,
                owner_id=user.id
            )
            
            session.add(template)
            session.commit()
            session.refresh(template)
            return template.to_dict()
    
    def update_template_usage(self, template_id: int):
        """Increment template usage count"""
        with self.get_session() as session:
            template = session.query(Template).filter_by(id=template_id).first()
            if template:
                template.usage_count += 1
                session.commit()
    
    # ============== Structure Configuration Management ==============
    
    def get_all_structure_configs(self, session_id: Optional[str] = None) -> List[Dict]:
        """Get all available structure configurations"""
        with self.get_session() as session:
            query = session.query(StructureConfig)
            
            # Get default and public configs, plus user's own configs
            query = query.filter(
                (StructureConfig.is_default == True) |
                (StructureConfig.is_public == True) |
                (StructureConfig.owner_session_id == session_id)
            )
            
            configs = query.all()
            return [config.to_dict() for config in configs]
    
    def get_structure_config_by_id(self, config_id: int) -> Optional[Dict]:
        """Get a specific structure configuration"""
        with self.get_session() as session:
            config = session.query(StructureConfig).filter_by(id=config_id).first()
            return config.to_dict() if config else None
    
    def get_structure_config_by_type(self, presentation_type: str) -> Optional[Dict]:
        """Get default structure configuration for a presentation type"""
        with self.get_session() as session:
            config = session.query(StructureConfig).filter_by(
                presentation_type=presentation_type,
                is_default=True
            ).first()
            return config.to_dict() if config else None
    
    def save_custom_structure(self, session_id: str, structure_data: Dict) -> Dict:
        """Save a custom structure configuration"""
        with self.get_session() as session:
            # Get user ID from session
            user = session.query(User).filter_by(session_id=session_id).first()
            if not user:
                user = User(session_id=session_id)
                session.add(user)
                session.commit()
                session.refresh(user)
            
            # Create main structure config
            structure_config = StructureConfig(
                name=structure_data['name'],
                description=structure_data.get('description'),
                presentation_type=structure_data.get('presentation_type'),
                sections=structure_data.get('sections', []),
                global_settings=structure_data.get('global_settings', {}),
                is_public=structure_data.get('is_public', False),
                owner_session_id=session_id,
                owner_id=user.id
            )
            
            session.add(structure_config)
            session.flush()  # Get the ID before adding section templates
            
            # Create section templates
            for idx, section in enumerate(structure_data.get('sections', [])):
                section_template = SectionTemplate(
                    structure_config_id=structure_config.id,
                    section_order=idx + 1,
                    section_name=section['name'],
                    slide_count_min=section.get('min_slides', 1),
                    slide_count_max=section.get('max_slides', 3),
                    bullets_per_slide=section.get('bullets_per_slide', 5),
                    include_chart=section.get('include_chart', False),
                    include_image=section.get('include_image', False),
                    layout_preference=section.get('layout_preference', 'text_only'),
                    custom_prompt=section.get('custom_prompt')
                )
                session.add(section_template)
            
            session.commit()
            session.refresh(structure_config)
            return structure_config.to_dict()
    
    # ============== User Preferences Management ==============
    
    def get_user_preferences(self, session_id: str) -> Optional[Dict]:
        """Get user preferences"""
        with self.get_session() as session:
            preferences = session.query(UserPreference).filter_by(session_id=session_id).first()
            return preferences.to_dict() if preferences else None
    
    def update_user_preferences(self, session_id: str, preferences_data: Dict):
        """Update user preferences"""
        with self.get_session() as session:
            preferences = session.query(UserPreference).filter_by(session_id=session_id).first()
            
            if not preferences:
                user = self.get_or_create_user(session_id)
                preferences = UserPreference(session_id=session_id, user_id=user.id)
                session.add(preferences)
            
            # Update preferences
            for key, value in preferences_data.items():
                if hasattr(preferences, key):
                    setattr(preferences, key, value)
            
            session.commit()
    
    # ============== Generation History Management ==============
    
    def save_generation_history(self, generation_data: Dict) -> Dict:
        """Save generation history record"""
        with self.get_session() as session:
            history = GenerationHistory(**generation_data)
            session.add(history)
            session.commit()
            session.refresh(history)
            return history.to_dict()
    
    def get_generation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get generation history for a session"""
        with self.get_session() as session:
            histories = session.query(GenerationHistory)\
                .filter_by(session_id=session_id)\
                .order_by(GenerationHistory.created_at.desc())\
                .limit(limit)\
                .all()
            return [history.to_dict() for history in histories]
    
    def save_content_analysis(self, generation_id: int, analysis_data: Dict) -> Dict:
        """Save content analysis results (for LangChain integration)"""
        with self.get_session() as session:
            analysis = ContentAnalysis(
                generation_history_id=generation_id,
                **analysis_data
            )
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            return analysis.to_dict()

    # ============== Presentation Versioning Management ==============

    def save_presentation_version(self, version_data: Dict) -> Dict:
        """Save a presentation version row.

        v1 is written by the generation flow on every successful generation.
        v2+ will be written by the future refinement flow. Caller must supply
        all fields explicitly (lineage_id, version_number, label, session_id,
        etc.). No defaulting is done here — bad input is a programmer error.
        """
        with self.get_session() as session:
            version = PresentationVersion(**version_data)
            session.add(version)
            session.commit()
            session.refresh(version)
            return version.to_dict()

    def get_lineages_for_session(self, session_id: str, limit: int = 20) -> List[Dict]:
        """List lineages owned by a session, newest-first.

        Aggregates over presentation_versions to produce one entry per
        lineage with the latest version's number, label, and created_at,
        plus the total version count. Ordering is by MAX(created_at) DESC
        to match /api/history's convention.
        """
        max_limit = VERSIONING_CONFIG.get('max_lineage_list_limit', 100)
        safe_limit = max(1, min(int(limit), max_limit))

        with self.get_session() as s:
            agg = (
                s.query(
                    PresentationVersion.lineage_id.label('lineage_id'),
                    func.max(PresentationVersion.version_number).label('max_version'),
                    func.count(PresentationVersion.id).label('total_versions'),
                    func.max(PresentationVersion.created_at).label('latest_created_at'),
                )
                .filter(PresentationVersion.session_id == session_id)
                .group_by(PresentationVersion.lineage_id)
                .subquery()
            )

            rows = (
                s.query(
                    agg.c.lineage_id,
                    agg.c.max_version,
                    agg.c.total_versions,
                    agg.c.latest_created_at,
                    PresentationVersion.label,
                )
                .join(
                    PresentationVersion,
                    (PresentationVersion.lineage_id == agg.c.lineage_id)
                    & (PresentationVersion.version_number == agg.c.max_version)
                    & (PresentationVersion.session_id == session_id),
                )
                .order_by(agg.c.latest_created_at.desc())
                .limit(safe_limit)
                .all()
            )

            return [
                {
                    'lineage_id': r.lineage_id,
                    'latest_version_number': r.max_version,
                    'latest_version_label': r.label,
                    'latest_version_created_at': r.latest_created_at.isoformat() if r.latest_created_at else None,
                    'total_versions': r.total_versions,
                }
                for r in rows
            ]

    def get_versions_for_lineage(self, lineage_id: int, session_id: str) -> Optional[List[Dict]]:
        """Return all versions in a lineage, chronological (oldest first).

        Returns None when no rows match (lineage_id, session_id) — covers
        both "lineage does not exist" and "lineage exists but owned by a
        different session". The route translates this into the spec's
        `not_found` error_type to avoid leaking lineage existence across
        sessions.
        """
        with self.get_session() as s:
            versions = (
                s.query(PresentationVersion)
                .filter_by(lineage_id=lineage_id, session_id=session_id)
                .order_by(PresentationVersion.version_number.asc())
                .all()
            )
            if not versions:
                return None
            return [v.to_dict() for v in versions]

    def get_version(self, lineage_id: int, version_number: int, session_id: str) -> Optional[Dict]:
        """Return a single version row, scoped to ownership.

        Returns None when the row is missing or owned by a different
        session (same existence-leak guard as get_versions_for_lineage).
        """
        with self.get_session() as s:
            version = (
                s.query(PresentationVersion)
                .filter_by(
                    lineage_id=lineage_id,
                    version_number=version_number,
                    session_id=session_id,
                )
                .first()
            )
            return version.to_dict() if version else None

    def lineage_exists_for_session(self, lineage_id: int, session_id: str) -> bool:
        """Cheap ownership probe used by the download route before send_file."""
        with self.get_session() as s:
            return (
                s.query(PresentationVersion.id)
                .filter_by(lineage_id=lineage_id, session_id=session_id)
                .first()
                is not None
            )

    def _backfill_v1_for_existing_presentations(self):
        """Idempotent backfill: insert a stub v1 row for every
        generation_history row that doesn't yet have a corresponding
        presentation_versions entry.

        Stub rows carry over file_path/filename/session_id/created_at from
        generation_history so the download endpoint can still serve old
        decks, but leave slide_structure NULL and set is_stub=True to
        mark that the original generation pipeline didn't snapshot them.

        Errors are caught and logged — backfill failure must not block
        app startup (matches the existing leniency in initialize_database).
        """
        try:
            with self.get_session() as s:
                orphans = (
                    s.query(GenerationHistory)
                    .outerjoin(
                        PresentationVersion,
                        PresentationVersion.lineage_id == GenerationHistory.id,
                    )
                    .filter(PresentationVersion.id.is_(None))
                    .all()
                )

                if not orphans:
                    print("Versioning backfill: 0 rows to insert")
                    return

                v1_label = VERSIONING_CONFIG.get('v1_label', 'Initial generation')
                inserted = 0
                for gh in orphans:
                    stub = PresentationVersion(
                        lineage_id=gh.id,
                        version_number=1,
                        label=v1_label,
                        note=None,
                        slide_structure=None,
                        file_path=gh.file_path,
                        filename=gh.filename,
                        is_stub=True,
                        session_id=gh.session_id,
                        created_at=gh.created_at,
                    )
                    s.add(stub)
                    inserted += 1
                s.commit()
                print(f"Versioning backfill: inserted {inserted} stub v1 rows")
        except Exception as e:
            print(f"⚠️ Versioning backfill failed: {e}")

    # ============== Prompt Template Management (for LangChain) ==============
    
    def get_prompt_template(self, name: str) -> Optional[Dict]:
        """Get a prompt template by name"""
        with self.get_session() as session:
            template = session.query(PromptTemplate).filter_by(
                name=name,
                is_active=True
            ).first()
            return template.to_dict() if template else None
    
    def save_prompt_template(self, template_data: Dict) -> Dict:
        """Save or update a prompt template"""
        with self.get_session() as session:
            existing = session.query(PromptTemplate).filter_by(
                name=template_data['name']
            ).first()
            
            if existing:
                # Deactivate old version
                existing.is_active = False
                
                # Create new version
                template = PromptTemplate(
                    **template_data,
                    version=existing.version + 1
                )
            else:
                template = PromptTemplate(**template_data)
            
            session.add(template)
            session.commit()
            session.refresh(template)
            return template.to_dict()
    
    # ============== Initialization Methods ==============
    
    def _initialize_defaults(self):
        """Initialize default data in the database"""
        with self.get_session() as session:
            # Check if defaults already exist
            if session.query(Template).filter_by(type='system').count() > 0:
                return  # Defaults already initialized
            
            print("🔧 Initializing default data...")
            
            # Create default templates
            self._create_default_templates(session)
            
            # Create default structure configurations
            self._create_default_structures(session)
            
            # Create default prompt templates (for LangChain)
            self._create_default_prompts(session)
            
            print("✅ Default data initialized successfully")
    
    def _create_default_templates(self, session):
        """Create default system templates"""
        default_templates = [
            {
                'name': 'Corporate Default',
                'description': 'Standard corporate template with company branding',
                'category': 'corporate',
                'type': 'system',
                'file_path': os.path.join(TEMPLATE_CONFIG['system_templates_dir'], 'corporate_default.pptx'),
                'is_default': True,
                'brand_colors': {'primary': '#003366', 'secondary': '#0066CC', 'accent': '#FF6600'},
                'font_settings': {'title': 'Arial Bold', 'body': 'Calibri', 'size_title': 32, 'size_body': 18}
            },
            {
                'name': 'Modern Pitch',
                'description': 'Modern template for pitch presentations',
                'category': 'pitch',
                'type': 'system',
                'file_path': os.path.join(TEMPLATE_CONFIG['system_templates_dir'], 'modern_pitch.pptx'),
                'brand_colors': {'primary': '#1A1A2E', 'secondary': '#16213E', 'accent': '#E94560'},
                'font_settings': {'title': 'Montserrat', 'body': 'Open Sans', 'size_title': 36, 'size_body': 20}
            },
            {
                'name': 'Professional Report',
                'description': 'Professional template for business reports',
                'category': 'report',
                'type': 'system',
                'file_path': os.path.join(TEMPLATE_CONFIG['system_templates_dir'], 'professional_report.pptx'),
                'brand_colors': {'primary': '#2C3E50', 'secondary': '#34495E', 'accent': '#3498DB'},
                'font_settings': {'title': 'Georgia', 'body': 'Times New Roman', 'size_title': 30, 'size_body': 16}
            }
        ]
        
        for template_data in default_templates:
            # Check if file exists, if not create placeholder
            if not os.path.exists(template_data['file_path']):
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(template_data['file_path']), exist_ok=True)
                # You'll need to place actual PPTX files here or create them
                template_data['file_path'] = 'placeholder.pptx'  # Temporary placeholder
            
            template = Template(**template_data)
            session.add(template)
        
        session.commit()
    
    def _create_default_structures(self, session):
        """Create default structure configurations"""
        for pres_type, config in PRESENTATION_TYPES.items():
            structure_config = StructureConfig(
                name=config['name'],
                description=config['description'],
                presentation_type=pres_type,
                sections=config['default_sections'],
                global_settings={
                    'include_agenda': True,
                    'include_summary': True,
                    'max_slides': 30
                },
                is_default=True,
                is_public=True
            )
            session.add(structure_config)
            session.flush()
            
            # Create section templates
            for idx, section in enumerate(config['default_sections']):
                section_template = SectionTemplate(
                    structure_config_id=structure_config.id,
                    section_order=idx + 1,
                    section_name=section['name'],
                    slide_count_min=section.get('min_slides', 1),
                    slide_count_max=section.get('max_slides', 3),
                    bullets_per_slide=section.get('bullets_per_slide', 5)
                )
                session.add(section_template)
        
        session.commit()
    
    def _create_default_prompts(self, session):
        """Create default prompt templates for LangChain"""
        default_prompts = [
            {
                'name': 'presentation_type_detection',
                'template_type': 'detection',
                'prompt_text': """Analyze the following content and determine what type of presentation it should be.
                
Content: {content}

Possible presentation types: {presentation_types}

Provide your analysis in the following JSON format:
{{
    "type": "detected_presentation_type",
    "confidence": 0.95,
    "reasoning": "Brief explanation",
    "suggested_sections": ["Section 1", "Section 2", ...]
}}""",
                'input_variables': ['content', 'presentation_types'],
                'output_parser': 'json',
                'description': 'Detects the type of presentation from content'
            },
            {
                'name': 'content_structuring',
                'template_type': 'structuring',
                'prompt_text': """Structure the following content for a {presentation_type} presentation.

Content: {content}
Target sections: {sections}
Max slides per section: {max_slides}

Organize the content into the specified sections and provide structured output.""",
                'input_variables': ['content', 'presentation_type', 'sections', 'max_slides'],
                'output_parser': 'pydantic',
                'description': 'Structures content into presentation sections'
            },
            {
                'name': 'slide_generation',
                'template_type': 'generation',
                'prompt_text': """Generate slide content for the following section:

Section: {section_name}
Content: {section_content}
Bullets per slide: {bullets_per_slide}
Style: {style}

Generate clear, concise bullet points for the slides.""",
                'input_variables': ['section_name', 'section_content', 'bullets_per_slide', 'style'],
                'output_parser': 'pydantic',
                'description': 'Generates slide content for a section'
            }
        ]
        
        for prompt_data in default_prompts:
            prompt = PromptTemplate(**prompt_data)
            session.add(prompt)
        
        session.commit()
    
    # ============== Utility Methods ==============
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return str(uuid.uuid4())
    
    def cleanup_old_sessions(self, days: int = 30):
        """Clean up old sessions and their data"""
        with self.get_session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Delete old sessions without registered users
            old_sessions = session.query(User).filter(
                User.email.is_(None),
                User.created_at < cutoff_date
            ).all()
            
            for user in old_sessions:
                session.delete(user)  # Cascading delete will handle related records
            
            session.commit()
            print(f"✅ Cleaned up {len(old_sessions)} old sessions")
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        with self.get_session() as session:
            stats = {
                'total_users': session.query(User).count(),
                'total_templates': session.query(Template).count(),
                'user_templates': session.query(Template).filter_by(type='user_uploaded').count(),
                'total_generations': session.query(GenerationHistory).count(),
                'total_structure_configs': session.query(StructureConfig).count()
            }
            
            # Get most used template
            most_used = session.query(Template).order_by(Template.usage_count.desc()).first()
            if most_used:
                stats['most_used_template'] = most_used.name
            
            return stats

# ============== Database initialization function ==============
def init_database():
    """Initialize the database (called from app.py)"""
    db_manager = DatabaseManager()
    return db_manager

if __name__ == "__main__":
    # Test database initialization
    print("🚀 Initializing PPT Generator Database...")
    db_manager = init_database()
    
    # Print statistics
    stats = db_manager.get_statistics()
    print("\n📊 Database Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Database setup completed successfully!")