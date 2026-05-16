"""
Database Package for PPT Generator
"""

from database.models import (
    Base,
    User,
    Template,
    StructureConfig,
    SectionTemplate,
    GenerationHistory,
    UserPreference,
    ContentAnalysis,
    PromptTemplate
)

from database.db_manager import DatabaseManager, init_database

__all__ = [
    'Base',
    'User',
    'Template',
    'StructureConfig',
    'SectionTemplate',
    'GenerationHistory',
    'UserPreference',
    'ContentAnalysis',
    'PromptTemplate',
    'DatabaseManager',
    'init_database'
]

# Package version
__version__ = '1.0.0'