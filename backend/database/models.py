"""
SQLAlchemy Database Models for PPT Generator
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
import json

Base = declarative_base()

# ============== User Model (for future authentication) ==============
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)  # For future auth
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    templates = relationship('Template', back_populates='owner', cascade='all, delete-orphan')
    structure_configs = relationship('StructureConfig', back_populates='owner', cascade='all, delete-orphan')
    generation_history = relationship('GenerationHistory', back_populates='user', cascade='all, delete-orphan')
    preferences = relationship('UserPreference', back_populates='user', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ============== Template Model ==============
class Template(Base):
    __tablename__ = 'templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # 'corporate', 'sales', 'technical', etc.
    type = Column(String(20), nullable=False, default='system')  # 'system' or 'user_uploaded'
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500))
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    
    # Branding settings
    brand_colors = Column(JSON)  # {"primary": "#003366", "secondary": "#0066CC"}
    font_settings = Column(JSON)  # {"title": "Arial", "body": "Calibri"}
    logo_settings = Column(JSON)  # {"path": "logo.png", "position": "top-right"}
    
    # Metadata
    owner_session_id = Column(String(100))
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship('User', back_populates='templates')
    generation_history = relationship('GenerationHistory', back_populates='template')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'type': self.type,
            'file_path': self.file_path,
            'thumbnail_path': self.thumbnail_path,
            'is_default': self.is_default,
            'is_public': self.is_public,
            'brand_colors': self.brand_colors,
            'font_settings': self.font_settings,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ============== Structure Configuration Model ==============
class StructureConfig(Base):
    __tablename__ = 'structure_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    presentation_type = Column(String(50))  # 'report', 'pitch', 'business_review', etc.
    
    # Configuration settings
    sections = Column(JSON, nullable=False)  # Detailed section configuration
    global_settings = Column(JSON)  # Overall presentation settings
    
    # Metadata
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    owner_session_id = Column(String(100))
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship('User', back_populates='structure_configs')
    section_templates = relationship('SectionTemplate', back_populates='structure_config', 
                                    cascade='all, delete-orphan', order_by='SectionTemplate.section_order')
    generation_history = relationship('GenerationHistory', back_populates='structure_config')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'presentation_type': self.presentation_type,
            'sections': self.sections,
            'global_settings': self.global_settings,
            'is_default': self.is_default,
            'section_templates': [st.to_dict() for st in self.section_templates],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ============== Section Template Model ==============
class SectionTemplate(Base):
    __tablename__ = 'section_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    structure_config_id = Column(Integer, ForeignKey('structure_configs.id', ondelete='CASCADE'), nullable=False)
    section_order = Column(Integer, nullable=False)
    section_name = Column(String(200), nullable=False)
    
    # Section configuration
    slide_count_min = Column(Integer, default=1)
    slide_count_max = Column(Integer, default=3)
    bullets_per_slide = Column(Integer, default=5)
    include_chart = Column(Boolean, default=False)
    include_image = Column(Boolean, default=False)
    layout_preference = Column(String(50), default='text_only')  # 'text_only', 'text_image', 'chart_focus'
    
    # Additional settings
    custom_prompt = Column(Text)  # Custom prompt for this section
    style_overrides = Column(JSON)  # Section-specific style overrides
    
    # Relationships
    structure_config = relationship('StructureConfig', back_populates='section_templates')
    
    def to_dict(self):
        return {
            'id': self.id,
            'section_order': self.section_order,
            'section_name': self.section_name,
            'slide_count_min': self.slide_count_min,
            'slide_count_max': self.slide_count_max,
            'bullets_per_slide': self.bullets_per_slide,
            'include_chart': self.include_chart,
            'include_image': self.include_image,
            'layout_preference': self.layout_preference,
            'custom_prompt': self.custom_prompt
        }

# ============== Generation History Model ==============
class GenerationHistory(Base):
    __tablename__ = 'generation_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    
    # File information
    filename = Column(String(500), nullable=False)
    file_path = Column(String(500))
    
    # Generation details
    template_id = Column(Integer, ForeignKey('templates.id', ondelete='SET NULL'))
    structure_config_id = Column(Integer, ForeignKey('structure_configs.id', ondelete='SET NULL'))
    
    # Type detection
    detected_type = Column(String(50))  # Auto-detected presentation type
    final_type = Column(String(50))  # Final type after user modification
    confidence_score = Column(Float)  # Confidence in type detection
    
    # Metrics
    total_slides = Column(Integer)
    generation_time_seconds = Column(Float)
    input_type = Column(String(20))  # 'file' or 'text'
    input_size = Column(Integer)  # Characters or file size in bytes
    model_used = Column(String(50))
    
    # Metadata
    generation_metadata = Column(JSON)  # Additional generation details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship('User', back_populates='generation_history')
    template = relationship('Template', back_populates='generation_history')
    structure_config = relationship('StructureConfig', back_populates='generation_history')
    content_analysis = relationship('ContentAnalysis', back_populates='generation_history', uselist=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'filename': self.filename,
            'template_name': self.template.name if self.template else 'Default',
            'structure_config_name': self.structure_config.name if self.structure_config else 'Auto',
            'detected_type': self.detected_type,
            'final_type': self.final_type,
            'total_slides': self.total_slides,
            'generation_time_seconds': self.generation_time_seconds,
            'model_used': self.model_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ============== User Preference Model ==============
class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    
    # Preferences
    last_template_id = Column(Integer, ForeignKey('templates.id', ondelete='SET NULL'))
    last_structure_config_id = Column(Integer, ForeignKey('structure_configs.id', ondelete='SET NULL'))
    preferred_presentation_type = Column(String(50))
    auto_detect_enabled = Column(Boolean, default=True)
    
    # UI preferences
    ui_preferences = Column(JSON)  # {"theme": "light", "show_tips": true}
    
    # Generation preferences
    generation_preferences = Column(JSON)  # {"max_slides": 30, "bullets_per_slide": 5}
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    user = relationship('User', back_populates='preferences')
    
    def to_dict(self):
        return {
            'session_id': self.session_id,
            'last_template_id': self.last_template_id,
            'last_structure_config_id': self.last_structure_config_id,
            'preferred_presentation_type': self.preferred_presentation_type,
            'auto_detect_enabled': self.auto_detect_enabled,
            'ui_preferences': self.ui_preferences,
            'generation_preferences': self.generation_preferences
        }

# ============== Content Analysis Model (for LangChain integration) ==============
class ContentAnalysis(Base):
    __tablename__ = 'content_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    generation_history_id = Column(Integer, ForeignKey('generation_history.id', ondelete='CASCADE'), nullable=False)
    
    # Analysis results
    detected_type = Column(String(50))
    confidence_score = Column(Float)
    suggested_structure = Column(JSON)  # Suggested sections and organization
    key_topics = Column(JSON)  # Extracted key topics
    content_summary = Column(Text)
    
    # LangChain metadata
    langchain_metadata = Column(JSON)  # Chain execution details
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    generation_history = relationship('GenerationHistory', back_populates='content_analysis')
    
    def to_dict(self):
        return {
            'id': self.id,
            'detected_type': self.detected_type,
            'confidence_score': self.confidence_score,
            'suggested_structure': self.suggested_structure,
            'key_topics': self.key_topics,
            'content_summary': self.content_summary
        }

# ============== Prompt Template Model (for LangChain) ==============
class PromptTemplate(Base):
    __tablename__ = 'prompt_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)
    template_type = Column(String(50))  # 'detection', 'structuring', 'generation'
    prompt_text = Column(Text, nullable=False)
    input_variables = Column(JSON)  # List of required variables
    output_parser = Column(String(50))  # 'pydantic' or 'json'
    
    # Versioning
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'template_type': self.template_type,
            'prompt_text': self.prompt_text,
            'input_variables': self.input_variables,
            'output_parser': self.output_parser,
            'version': self.version,
            'is_active': self.is_active
        }