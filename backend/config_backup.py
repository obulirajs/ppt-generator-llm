"""
Configuration settings for PPT Generator Application
"""
import os
from datetime import timedelta

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database configuration
DATABASE_CONFIG = {
    'path': os.path.join(BASE_DIR, 'database', 'ppt_generator.db'),
    'echo': False,  # Set to True for SQL query logging during development
    'pool_size': 5,
    'max_overflow': 10
}

# Template configuration
TEMPLATE_CONFIG = {
    'system_templates_dir': os.path.join(BASE_DIR, 'templates', 'system'),
    'user_templates_dir': os.path.join(BASE_DIR, 'user_templates'),
    'allowed_extensions': ['.pptx'],
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'thumbnail_size': (300, 225)  # Width x Height
}

# LLM Configuration (Ollama)
LLM_CONFIG = {
    'base_url': 'http://localhost:11434',
    'default_model': 'llama3.2',
    'timeout': 120,
    'temperature': 0.7,
    'max_tokens': 4000
}

# Presentation Types Configuration
PRESENTATION_TYPES = {
    'report': {
        'name': 'Business Report',
        'description': 'Comprehensive business reports with data analysis',
        'default_sections': [
            {'name': 'Executive Summary', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Key Findings', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Detailed Analysis', 'min_slides': 3, 'max_slides': 5, 'bullets_per_slide': 5},
            {'name': 'Recommendations', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Next Steps', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 4}
        ]
    },
    'pitch': {
        'name': 'Pitch Deck',
        'description': 'Investor pitch presentations',
        'default_sections': [
            {'name': 'Title & Vision', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 0},
            {'name': 'Problem Statement', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 3},
            {'name': 'Our Solution', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 4},
            {'name': 'Market Opportunity', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 5},
            {'name': 'Business Model', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Go-to-Market Strategy', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Team', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 6},
            {'name': 'Ask & Use of Funds', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 4}
        ]
    },
    'business_review': {
        'name': 'Business Review',
        'description': 'Periodic business performance reviews',
        'default_sections': [
            {'name': 'Overview', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 4},
            {'name': 'Performance Metrics', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Achievements', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Challenges', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Opportunities', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Action Items', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 5}
        ]
    },
    'client_success': {
        'name': 'Client Success Plan',
        'description': 'Client success stories and implementation plans',
        'default_sections': [
            {'name': 'Client Overview', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 4},
            {'name': 'Success Metrics', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 5},
            {'name': 'Implementation Journey', 'min_slides': 2, 'max_slides': 4, 'bullets_per_slide': 4},
            {'name': 'Results Achieved', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Future Roadmap', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4}
        ]
    },
    'case_study': {
        'name': 'Case Study',
        'description': 'Detailed case study presentations',
        'default_sections': [
            {'name': 'Background', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Challenge', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Approach', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Solution Implementation', 'min_slides': 2, 'max_slides': 4, 'bullets_per_slide': 5},
            {'name': 'Results & Impact', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Key Learnings', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 4}
        ]
    },
    'presales': {
        'name': 'Pre-Sales Deck',
        'description': 'Pre-sales and solution presentations',
        'default_sections': [
            {'name': 'Agenda', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 5},
            {'name': 'Understanding Your Needs', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Our Solution', 'min_slides': 3, 'max_slides': 5, 'bullets_per_slide': 5},
            {'name': 'Technical Architecture', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 4},
            {'name': 'Implementation Plan', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Pricing & Timeline', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Why Us', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 5}
        ]
    },
    'proposal': {
        'name': 'Client Proposal',
        'description': 'Formal client proposals',
        'default_sections': [
            {'name': 'Executive Summary', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Project Understanding', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 4},
            {'name': 'Proposed Solution', 'min_slides': 3, 'max_slides': 5, 'bullets_per_slide': 5},
            {'name': 'Methodology', 'min_slides': 2, 'max_slides': 3, 'bullets_per_slide': 5},
            {'name': 'Timeline & Milestones', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 5},
            {'name': 'Investment', 'min_slides': 1, 'max_slides': 2, 'bullets_per_slide': 4},
            {'name': 'Terms & Conditions', 'min_slides': 1, 'max_slides': 1, 'bullets_per_slide': 5}
        ]
    }
}

# Session Configuration
SESSION_CONFIG = {
    'secret_key': 'your-secret-key-change-in-production',
    'permanent_session_lifetime': timedelta(days=30),
    'cookie_name': 'ppt_session',
    'cookie_httponly': True,
    'cookie_secure': False  # Set to True in production with HTTPS
}

# File Upload Configuration
UPLOAD_CONFIG = {
    'max_content_length': 16 * 1024 * 1024,  # 16MB max file size
    'allowed_document_types': ['.txt', '.docx', '.pdf'],
    'temp_folder': os.path.join(BASE_DIR, 'temp')
}

# Generation Settings
GENERATION_CONFIG = {
    'default_template': 'corporate_default',
    'auto_detect_type': True,
    'max_slides_per_presentation': 50,
    'min_content_length': 100,  # Minimum characters for generation
    'enable_caching': True,
    'cache_ttl': 3600  # 1 hour in seconds
}

# LangChain Configuration (for future use)
LANGCHAIN_CONFIG = {
    'enable_structured_output': True,
    'enable_prompt_templates': True,
    'enable_output_validation': True,
    'verbose': False,  # Set to True for debugging
    'max_retries': 3,
    'retry_delay': 1  # seconds
}