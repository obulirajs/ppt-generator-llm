"""
Flask Application - PPT Generator API
Main backend service for converting text/documents to PowerPoint presentations
Uses local Ollama LLM for content structuring
Enhanced with database integration for templates and structures
"""

from flask import Flask, request, jsonify, send_file, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import time
import logging
from datetime import datetime
import uuid

# Import utility modules
from utils import document_parser, llm_service, ppt_generator

# Import database components
from database import init_database
from config import (
    SESSION_CONFIG,
    TEMPLATE_CONFIG,
    PRESENTATION_TYPES,
    GENERATION_CONFIG,
    VERSIONING_CONFIG
)


# ==================== CONFIGURATION ====================

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Flask Configuration
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'temp')
app.config['SECRET_KEY'] = SESSION_CONFIG['secret_key']
app.config['PERMANENT_SESSION_LIFETIME'] = SESSION_CONFIG['permanent_session_lifetime']

# Ollama Configuration
DEFAULT_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# CORS Configuration - Allow React frontend
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5173"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db_manager = None

def initialize_database():
    """Initialize database on application startup"""
    global db_manager
    try:
        logger.info("Initializing database...")
        db_manager = init_database()
        logger.info("✅ Database initialized successfully")
        
        # Get statistics
        stats = db_manager.get_statistics()
        logger.info(f"Database stats: {stats}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False


# ==================== HELPER FUNCTIONS ====================

def validate_request():
    """
    Validate incoming request has either file or text
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None, input_type: str)
    """
    # Check if file is present
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '':
            return True, None, 'file'
    
    # Check if text is present
    if 'text' in request.form:
        text = request.form['text']
        if text and text.strip():
            return True, None, 'text'
    
    # Check JSON body
    if request.is_json:
        data = request.get_json()
        if data and 'text' in data and data['text'].strip():
            return True, None, 'json'
    
    return False, "No file or text content provided", None


def get_model_from_request():
    """
    Extract model name from request or use default
    
    Returns:
        str: Model name
    """
    # Check form data
    if 'model' in request.form:
        return request.form['model']
    
    # Check JSON body
    if request.is_json:
        data = request.get_json()
        if data and 'model' in data:
            return data['model']
    
    return DEFAULT_MODEL


def create_error_response(error_message, error_type='processing', status_code=400):
    """
    Create standardized error response
    
    Args:
        error_message (str): Error description
        error_type (str): Type of error
        status_code (int): HTTP status code
        
    Returns:
        tuple: (response, status_code)
    """
    logger.error(f"{error_type} error: {error_message}")
    return jsonify({
        'success': False,
        'error': error_message,
        'error_type': error_type,
        'timestamp': datetime.utcnow().isoformat()
    }), status_code


def create_success_response(file_path, processing_time):
    """
    Create standardized success response
    
    Args:
        file_path (str): Path to generated file
        processing_time (float): Time taken to process
        
    Returns:
        tuple: (response, status_code)
    """
    filename = os.path.basename(file_path)
    file_size_kb = os.path.getsize(file_path) / 1024
    
    # Get presentation info
    ppt_info = ppt_generator.get_presentation_info(file_path)
    
    response_data = {
        'success': True,
        'message': 'Presentation generated successfully',
        'filename': filename,
        'download_url': f'/api/download/{filename}',
        'file_size_kb': round(file_size_kb, 2),
        'processing_time_seconds': round(processing_time, 2),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if ppt_info and 'slide_count' in ppt_info:
        response_data['slide_count'] = ppt_info['slide_count']
    
    logger.info(f"Successfully generated: {filename} ({file_size_kb:.1f} KB in {processing_time:.1f}s)")
    
    return jsonify(response_data), 200


def safe_filename_for_download(filename):
    """
    Validate filename for download to prevent path traversal
    
    Args:
        filename (str): Requested filename
        
    Returns:
        str or None: Safe filename or None if invalid
    """
    # Remove any path components
    filename = os.path.basename(filename)
    
    # Check if it's a .pptx file
    if not filename.endswith('.pptx'):
        return None
    
    # Check if file exists in upload folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return None
    
    return filename


def get_or_create_session_id():
    """
    Get existing session ID from Flask session or create a new one

    Returns:
        str: Session ID
    """
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True

        # Create user in database if database is available
        if db_manager:
            try:
                db_manager.get_or_create_user(session['session_id'])
                logger.info(f"Created new session: {session['session_id']}")
            except Exception as e:
                logger.error(f"Failed to create user in database: {str(e)}")

    return session['session_id']


def _lineage_owned_by_session(lineage_id, session_id):
    """
    Cheap ownership probe used by version-detail routes.

    Returns True only when the lineage exists AND has at least one row
    matching the calling session. False covers both "missing" and
    "exists but owned by another session" — the existence-leak guard.
    """
    if not db_manager:
        return False
    return db_manager.lineage_exists_for_session(lineage_id, session_id)


# ==================== API ROUTES ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify API and Ollama status
    
    Returns:
        JSON response with health status
    """
    try:
        # Check Ollama connection
        is_connected, error = llm_service.check_ollama_connection()
        
        # Get available models
        available_models = llm_service.get_available_models() if is_connected else []
        
        # Get database statistics if available
        db_stats = {}
        if db_manager:
            try:
                db_stats = db_manager.get_statistics()
            except Exception as e:
                logger.warning(f"Could not get database stats: {str(e)}")
        
        response = {
            "application_name": "PPT Generator (Backend)",
            'status': 'healthy' if is_connected else 'degraded',
            'api_version': '1.0.0',
            'ollama_connected': is_connected,
            'ollama_url': OLLAMA_BASE_URL,
            'available_models': available_models,
            'default_model': DEFAULT_MODEL,
            'database_connected': db_manager is not None,
            'database_stats': db_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if error:
            response['ollama_error'] = error
        
        status_code = 200 if is_connected else 503
        return jsonify(response), status_code
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_error_response(str(e), 'health_check', 500)


@app.route('/api/models', methods=['GET'])
def list_models():
    """
    List available Ollama models
    
    Returns:
        JSON response with model list
    """
    try:
        models = llm_service.get_available_models()
        
        return jsonify({
            'success': True,
            'models': models,
            'default_model': DEFAULT_MODEL,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to list models: {str(e)}")
        return create_error_response(str(e), 'models', 500)


@app.route('/api/generate-ppt', methods=['POST'])
def generate_ppt():
    """
    Enhanced endpoint to generate PowerPoint presentation
    Now supports templates and structure configurations from database
    
    Accepts:
        - file or text content (required)
        - model (optional, defaults to llama3.2)
        - template_id (optional, uses default if not specified)
        - structure_config_id (optional, auto-detects if not specified)
        - auto_detect_type (optional, defaults to true)
    
    Returns:
        JSON response with file information or error
    """
    start_time = time.time()
    temp_file_path = None
    session_id = None
    
    try:
        # Get session ID for tracking
        session_id = get_or_create_session_id()
        logger.info(f"Processing request for session: {session_id[:8]}...")
        
        # Validate request has content
        is_valid, error_msg, input_type = validate_request()
        if not is_valid:
            return create_error_response(error_msg, 'validation', 400)
        
        logger.info(f"Received request - Input type: {input_type}")
        
        # Get parameters from request
        model_name = get_model_from_request()
        template_id = request.form.get('template_id', type=int)
        structure_config_id = request.form.get('structure_config_id', type=int)
        auto_detect_type = request.form.get('auto_detect_type', 'true').lower() == 'true'
        
        logger.info(f"Parameters - Model: {model_name}, Template: {template_id}, Structure: {structure_config_id}")
        
        # Extract text based on input type
        extracted_text = None
        original_filename = None
        input_size = 0
        
        if input_type == 'file':
            # Handle file upload
            file = request.files['file']
            
            # Validate file
            is_valid, error_msg = document_parser.validate_file(file)
            if not is_valid:
                return create_error_response(error_msg, 'validation', 400)
            
            # Save uploaded file
            try:
                temp_file_path, original_filename = document_parser.save_uploaded_file(
                    file, 
                    app.config['UPLOAD_FOLDER']
                )
                logger.info(f"File uploaded: {original_filename}")
                input_size = os.path.getsize(temp_file_path)
            except Exception as e:
                return create_error_response(f"Failed to save file: {str(e)}", 'file_upload', 500)
            
            # Extract text from file
            try:
                file_extension = document_parser.get_file_extension(original_filename)
                extracted_text = document_parser.extract_text_from_file(temp_file_path, file_extension)
                logger.info(f"Extracted {len(extracted_text)} characters from file")
            except Exception as e:
                return create_error_response(f"Failed to extract text: {str(e)}", 'extraction', 500)
        
        elif input_type == 'text':
            # Handle direct text input
            text_input = request.form['text']
            try:
                extracted_text = document_parser.process_direct_text(text_input)
                input_size = len(extracted_text)
                logger.info(f"Processed {input_size} characters of direct text")
            except Exception as e:
                return create_error_response(f"Invalid text input: {str(e)}", 'validation', 400)
        
        elif input_type == 'json':
            # Handle JSON body
            data = request.get_json()
            text_input = data['text']
            try:
                extracted_text = document_parser.process_direct_text(text_input)
                input_size = len(extracted_text)
                logger.info(f"Processed {input_size} characters from JSON")
            except Exception as e:
                return create_error_response(f"Invalid text input: {str(e)}", 'validation', 400)
        
        # Validate extracted content
        is_valid, warning, processed_text = document_parser.validate_content(extracted_text)
        if not is_valid:
            return create_error_response(warning, 'validation', 400)
        
        if warning:
            logger.warning(warning)
        
        # Get template from database if available
        template = None
        template_path = None
        if db_manager:
            if template_id:
                # Use specified template
                template = db_manager.get_template_by_id(template_id)
                if not template:
                    logger.warning(f"Template {template_id} not found, using default")
            
            if not template:
                # Use default template
                template = db_manager.get_default_template()
            
            if template:
                template_path = template.get('file_path')
                if template_path and os.path.exists(template_path):
                    logger.info(f"Using template: {template['name']} (ID: {template['id']})")
                    template_id = template['id']
                else:
                    logger.warning(f"Template file not found: {template_path}")
                    template_path = None
        
        # Get or detect structure configuration if database is available
        structure_config = None
        detected_type = None
        confidence_score = None
        
        if db_manager:
            if structure_config_id:
                # Use specified structure
                structure_config = db_manager.get_structure_config_by_id(structure_config_id)
                if structure_config:
                    logger.info(f"Using structure: {structure_config['name']} (ID: {structure_config_id})")
            
            elif auto_detect_type:
                # Auto-detect presentation type
                logger.info("Auto-detecting presentation type...")
                try:
                    # Use first 3000 characters for detection
                    detection_result = llm_service.detect_presentation_type(processed_text[:3000])
                    detected_type = detection_result.get('type', 'report')
                    confidence_score = detection_result.get('confidence', 0.5)
                    
                    logger.info(f"Detected type: {detected_type} (confidence: {confidence_score:.2f})")
                    
                    # Get structure config for detected type
                    structure_config = db_manager.get_structure_config_by_type(detected_type)
                    if structure_config:
                        structure_config_id = structure_config['id']
                        logger.info(f"Using detected structure: {structure_config['name']}")
                    
                except Exception as e:
                    logger.warning(f"Auto-detection failed: {str(e)}, using default")
            
            # Fall back to default report structure if nothing else
            if not structure_config:
                structure_config = db_manager.get_structure_config_by_type('report')
                if structure_config:
                    structure_config_id = structure_config['id']
                    logger.info("Using default report structure")
        # Prepare structure for generation
        generation_structure = None
        
        # Always use LLM to generate the actual presentation structure
        # The structure_config is just for guidance on sections, not the actual slides
        logger.info("Generating presentation structure with LLM...")
        try:
            # Generate the structure using existing LLM service method
            # This creates the proper format with title and bullets
            generation_structure = llm_service.generate_presentation_structure(
                processed_text, 
                model_name
            )
            logger.info(f"Generated structure with {len(generation_structure.get('slides', []))} slides")
            
            # If we detected a type and have config, log it for reference
            if structure_config:
                logger.info(f"Structure config '{structure_config.get('name')}' available for reference")
                # Note: The structure_config provides guidance on expected sections
                # but we let the LLM generate the actual slides
            
        except Exception as e:
            return create_error_response(f"Failed to generate structure: {str(e)}", 'llm', 500)
        
        # # Prepare structure for generation
        # generation_structure = None
        # if structure_config and structure_config.get('sections'):
        #     generation_structure = {
        #         'title': original_filename or 'Presentation',
        #         'slides': []
        #     }
            
        #     # Convert structure config to generation format
        #     for section in structure_config['sections']:
        #         # Add section slides based on configuration
        #         section_data = {
        #             'type': 'section',
        #             'name': section.get('name', 'Section'),
        #             'min_slides': section.get('min_slides', 1),
        #             'max_slides': section.get('max_slides', 3),
        #             'bullets_per_slide': section.get('bullets_per_slide', 5)
        #         }
        #         generation_structure['slides'].append(section_data)
        # else:
        #     # Use existing logic to generate structure from LLM
        #     logger.info("Generating presentation structure with LLM...")
        #     try:
        #         generation_structure = llm_service.generate_presentation_structure(
        #             processed_text, 
        #             model_name
        #         )
        #         logger.info(f"Generated structure with {len(generation_structure.get('slides', []))} slides")
        #     except Exception as e:
        #         return create_error_response(f"Failed to generate structure: {str(e)}", 'llm', 500)
        
        # Validate structure
        is_valid, error_msg = ppt_generator.validate_structure(generation_structure)
        if not is_valid:
            return create_error_response(f"Invalid presentation structure: {error_msg}", 'structure', 500)
        
        # Generate PowerPoint file with template if available
        try:
            logger.info("Creating PowerPoint presentation...")
            
            # Check if we need to use template-aware generation
            if template_path and os.path.exists(template_path):
                # Generate with template (this needs to be implemented in ppt_generator)
                ppt_file_path = ppt_generator.create_presentation_with_template(
                    generation_structure,
                    template_path,
                    app.config['UPLOAD_FOLDER']
                )
                logger.info(f"PowerPoint created with template: {os.path.basename(ppt_file_path)}")
            else:
                # Use existing generation method
                ppt_file_path = ppt_generator.create_presentation(
                    generation_structure, 
                    app.config['UPLOAD_FOLDER']
                )
                logger.info(f"PowerPoint created: {os.path.basename(ppt_file_path)}")
                
        except Exception as e:
            return create_error_response(f"Failed to create presentation: {str(e)}", 'generation', 500)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Get slide count
        slide_count = ppt_generator.get_presentation_info(ppt_file_path).get('slide_count', 0)
        
        # Save generation history to database if available
        generation_id = None
        if db_manager:
            try:
                history_data = {
                    'session_id': session_id,
                    'filename': os.path.basename(ppt_file_path),
                    'file_path': ppt_file_path,
                    'template_id': template_id,
                    'structure_config_id': structure_config_id,
                    'detected_type': detected_type,
                    'final_type': structure_config.get('presentation_type') if structure_config else detected_type,
                    'confidence_score': confidence_score,
                    'total_slides': slide_count,
                    'generation_time_seconds': processing_time,
                    'input_type': input_type,
                    'input_size': input_size,
                    'model_used': model_name,
                    'generation_metadata': {
                        'original_filename': original_filename,
                        'auto_detect': auto_detect_type
                    }
                }
                
                history = db_manager.save_generation_history(history_data)
                generation_id = history.get('id')
                logger.info(f"Generation history saved with ID: {generation_id}")

                # Feature 001 — presentation versioning foundation:
                # persist v1 of this lineage. Nested try/except so a version-save
                # failure does not skip the template-usage / preferences updates
                # below, and never breaks the user-facing response (plan §6 risk #1).
                try:
                    db_manager.save_presentation_version({
                        'lineage_id': generation_id,
                        'version_number': 1,
                        'label': VERSIONING_CONFIG['v1_label'],
                        'note': None,
                        'slide_structure': generation_structure,
                        'file_path': ppt_file_path,
                        'filename': os.path.basename(ppt_file_path),
                        'is_stub': False,
                        'session_id': session_id,
                    })
                    logger.info(f"Presentation version v1 saved for lineage {generation_id}")
                except Exception as version_error:
                    logger.error(f"Failed to save presentation version v1: {str(version_error)}")

                # Update template usage count
                if template_id:
                    db_manager.update_template_usage(template_id)
                
                # Update user preferences
                db_manager.update_user_preferences(session_id, {
                    'last_template_id': template_id,
                    'last_structure_config_id': structure_config_id,
                    'preferred_presentation_type': detected_type or 'report'
                })
                
            except Exception as e:
                logger.error(f"Failed to save generation history: {str(e)}")
                # Continue even if history saving fails
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'Presentation generated successfully',
            'filename': os.path.basename(ppt_file_path),
            'download_url': f'/api/download/{os.path.basename(ppt_file_path)}',
            'file_size_kb': round(os.path.getsize(ppt_file_path) / 1024, 2),
            'processing_time_seconds': round(processing_time, 2),
            'slide_count': slide_count,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add database-related information if available
        if db_manager:
            response_data['generation_id'] = generation_id
            response_data['template_used'] = template['name'] if template else 'Default'
            response_data['structure_used'] = structure_config['name'] if structure_config else 'Default'
            
            if detected_type:
                response_data['detected_type'] = detected_type
                response_data['confidence_score'] = round(confidence_score, 2) if confidence_score else None
        
        logger.info(f"Successfully generated: {os.path.basename(ppt_file_path)} ({slide_count} slides in {processing_time:.1f}s)")
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(f"Internal server error: {str(e)}", 'internal', 500)
    
    finally:
        # Cleanup temporary uploaded file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                document_parser.cleanup_temp_file(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {str(e)}")


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    Download generated PowerPoint file
    
    Args:
        filename (str): Name of the file to download
        
    Returns:
        File download or error response
    """
    try:
        # Validate and sanitize filename
        safe_filename = safe_filename_for_download(filename)
        
        if not safe_filename:
            return create_error_response("File not found or invalid filename", 'not_found', 404)
        
        # Send file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        logger.info(f"Downloading file: {safe_filename}")
        
        return send_file(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            as_attachment=True,
            download_name=safe_filename
        )
    
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return create_error_response(f"Failed to download file: {str(e)}", 'download', 500)


@app.route('/api/cleanup', methods=['DELETE'])
def cleanup():
    """
    Cleanup old presentation files (older than 24 hours)
    
    Returns:
        JSON response with cleanup status
    """
    try:
        logger.info("Running cleanup of old files...")
        ppt_generator.cleanup_old_presentations(app.config['UPLOAD_FOLDER'], max_age_hours=24)
        
        return jsonify({
            'success': True,
            'message': 'Cleanup completed successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return create_error_response(f"Cleanup failed: {str(e)}", 'cleanup', 500)

@app.route('/api/files', methods=['GET'])
def list_files():
    """
    List all generated presentation files
    """
    try:
        files_list = []
        upload_folder = app.config['UPLOAD_FOLDER']
        
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename.endswith('.pptx'):
                    file_path = os.path.join(upload_folder, filename)
                    
                    # Get file info
                    file_stat = os.stat(file_path)
                    file_size_kb = file_stat.st_size / 1024
                    modified_time = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    # Get presentation info
                    ppt_info = ppt_generator.get_presentation_info(file_path)
                    
                    files_list.append({
                        'filename': filename,
                        'file_size_kb': round(file_size_kb, 2),
                        'created_at': modified_time.isoformat(),
                        'slide_count': ppt_info.get('slide_count') if ppt_info else None,
                        'download_url': f'/api/download/{filename}'
                    })
        
        # Sort by creation time (newest first)
        files_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files_list,
            'total': len(files_list),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        return create_error_response(f"Failed to list files: {str(e)}", 'files', 500)


@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """
    Delete a specific presentation file
    """
    try:
        # Validate and sanitize filename
        safe_filename = safe_filename_for_download(filename)
        
        if not safe_filename:
            return create_error_response("File not found or invalid filename", 'not_found', 404)
        
        # Delete file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        os.remove(file_path)
        
        logger.info(f"Deleted file: {safe_filename}")
        
        return jsonify({
            'success': True,
            'message': f'File {safe_filename} deleted successfully',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to delete file: {str(e)}")
        return create_error_response(f"Failed to delete file: {str(e)}", 'delete', 500)


# ==================== TEMPLATE MANAGEMENT ENDPOINTS ====================

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """
    Get all available templates for the current session
    
    Returns:
        JSON response with list of templates
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        # Get session ID
        session_id = get_or_create_session_id()
        logger.info(f"Fetching templates for session: {session_id[:8]}...")
        
        # Get templates from database
        templates = db_manager.get_all_templates(session_id)
        
        # Add additional metadata
        for template in templates:
            # Add thumbnail URL if thumbnail exists
            if template.get('thumbnail_path'):
                template['thumbnail_url'] = f"/api/templates/{template['id']}/thumbnail"
            
            # Mark if this is the user's template
            template['is_mine'] = template.get('owner_session_id') == session_id
        
        # Find default template ID
        default_template_id = next(
            (t['id'] for t in templates if t.get('is_default')), 
            None
        )
        
        logger.info(f"Found {len(templates)} templates")
        
        return jsonify({
            'success': True,
            'templates': templates,
            'default_template_id': default_template_id,
            'total': len(templates),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get templates: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to get templates: {str(e)}", 'templates', 500)


@app.route('/api/templates/<int:template_id>', methods=['GET'])
def get_template_details(template_id):
    """
    Get detailed information about a specific template
    
    Args:
        template_id (int): Template ID
        
    Returns:
        JSON response with template details
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        logger.info(f"Fetching template details for ID: {template_id}")
        
        # Get template from database
        template = db_manager.get_template_by_id(template_id)
        
        if not template:
            return create_error_response(f"Template with ID {template_id} not found", 'not_found', 404)
        
        # Add additional information
        if template.get('file_path') and os.path.exists(template['file_path']):
            template['file_size_kb'] = os.path.getsize(template['file_path']) / 1024
        
        logger.info(f"Retrieved template: {template.get('name')}")
        
        return jsonify({
            'success': True,
            'template': template,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get template details: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to get template: {str(e)}", 'template', 500)


@app.route('/api/templates/upload', methods=['POST'])
def upload_template():
    """
    Upload a custom PowerPoint template
    
    Returns:
        JSON response with uploaded template information
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        # Get session ID
        session_id = get_or_create_session_id()
        
        # Check if file is present
        if 'file' not in request.files:
            return create_error_response("No file provided", 'validation', 400)
        
        file = request.files['file']
        
        # Validate file
        if file.filename == '':
            return create_error_response("No file selected", 'validation', 400)
        
        if not file.filename.endswith('.pptx'):
            return create_error_response(
                "Invalid file format. Only .pptx files are allowed", 
                'validation', 
                400
            )
        
        # Get template metadata from form
        template_name = request.form.get('name', '').strip()
        if not template_name:
            # Generate name from filename
            template_name = os.path.splitext(file.filename)[0].replace('_', ' ').title()
        
        description = request.form.get('description', '')
        category = request.form.get('category', 'custom')
        is_public = request.form.get('is_public', 'false').lower() == 'true'
        
        # Validate file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = TEMPLATE_CONFIG.get('max_file_size', 10 * 1024 * 1024)
        if file_size > max_size:
            return create_error_response(
                f"File too large. Maximum size: {max_size / (1024*1024):.1f}MB", 
                'file_size', 
                413
            )
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_original = secure_filename(file.filename)
        unique_filename = f"{session_id[:8]}_{timestamp}_{safe_original}"
        
        # Ensure user templates directory exists
        user_templates_dir = TEMPLATE_CONFIG.get('user_templates_dir', 'user_templates')
        os.makedirs(user_templates_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(user_templates_dir, unique_filename)
        file.save(file_path)
        logger.info(f"Template file saved: {unique_filename}")
        
        # TODO: Generate thumbnail (will be implemented later)
        thumbnail_path = None
        
        # Prepare template data for database
        template_data = {
            'name': template_name,
            'description': description,
            'category': category,
            'file_path': file_path,
            'thumbnail_path': thumbnail_path,
            'is_public': is_public
        }
        
        # Save to database
        try:
            template = db_manager.save_user_template(session_id, template_data)
            logger.info(f"Template saved to database: {template_name} (ID: {template.get('id')})")
            
            return jsonify({
                'success': True,
                'message': 'Template uploaded successfully',
                'template': template,
                'timestamp': datetime.utcnow().isoformat()
            }), 201
            
        except Exception as db_error:
            # Clean up uploaded file if database save fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise db_error
        
    except Exception as e:
        logger.error(f"Failed to upload template: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to upload template: {str(e)}", 'upload', 500)


# ==================== STRUCTURE CONFIGURATION ENDPOINTS ====================

@app.route('/api/structure-configs', methods=['GET'])
def get_structure_configs():
    """
    Get all available structure configurations
    
    Returns:
        JSON response with list of structure configurations
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        # Get session ID
        session_id = get_or_create_session_id()
        logger.info(f"Fetching structure configs for session: {session_id[:8]}...")
        
        # Get configurations from database
        configs = db_manager.get_all_structure_configs(session_id)
        
        # Add metadata
        for config in configs:
            # Mark if this is the user's configuration
            config['is_mine'] = config.get('owner_session_id') == session_id
            
            # Count total slides range
            if config.get('sections'):
                min_slides = sum(s.get('min_slides', 1) for s in config['sections'])
                max_slides = sum(s.get('max_slides', 3) for s in config['sections'])
                config['slide_range'] = f"{min_slides}-{max_slides}"
        
        # Get available presentation types
        presentation_types = list(PRESENTATION_TYPES.keys())
        
        logger.info(f"Found {len(configs)} structure configurations")
        
        return jsonify({
            'success': True,
            'configurations': configs,
            'presentation_types': presentation_types,
            'total': len(configs),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get structure configs: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to get configurations: {str(e)}", 'structure', 500)


@app.route('/api/structure-configs/<string:presentation_type>', methods=['GET'])
def get_structure_by_type(presentation_type):
    """
    Get structure configuration for a specific presentation type
    
    Args:
        presentation_type (str): Type of presentation (report, pitch, etc.)
        
    Returns:
        JSON response with structure configuration
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        logger.info(f"Fetching structure config for type: {presentation_type}")
        
        # Validate presentation type
        if presentation_type not in PRESENTATION_TYPES:
            return create_error_response(
                f"Invalid presentation type: {presentation_type}", 
                'validation', 
                400
            )
        
        # Get configuration from database
        config = db_manager.get_structure_config_by_type(presentation_type)
        
        if not config:
            return create_error_response(
                f"No configuration found for type: {presentation_type}", 
                'not_found', 
                404
            )
        
        logger.info(f"Retrieved config: {config.get('name')}")
        
        return jsonify({
            'success': True,
            'configuration': config,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get structure by type: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to get configuration: {str(e)}", 'structure', 500)


@app.route('/api/structure-configs', methods=['POST'])
def create_structure_config():
    """
    Create a custom structure configuration
    
    Returns:
        JSON response with created configuration
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        # Get session ID
        session_id = get_or_create_session_id()
        
        # Get JSON data
        if not request.is_json:
            return create_error_response("Request must be JSON", 'validation', 400)
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return create_error_response("Configuration name is required", 'validation', 400)
        
        if not data.get('sections') or not isinstance(data['sections'], list):
            return create_error_response("Sections array is required", 'validation', 400)
        
        if len(data['sections']) == 0:
            return create_error_response("At least one section is required", 'validation', 400)
        
        # Validate each section
        for i, section in enumerate(data['sections']):
            if not section.get('name'):
                return create_error_response(
                    f"Section {i+1} must have a name", 
                    'validation', 
                    400
                )
            
            # Set defaults for optional fields
            section['min_slides'] = section.get('min_slides', 1)
            section['max_slides'] = section.get('max_slides', 3)
            section['bullets_per_slide'] = section.get('bullets_per_slide', 5)
            
            # Validate slide counts
            if section['min_slides'] > section['max_slides']:
                return create_error_response(
                    f"Section '{section['name']}': min_slides cannot be greater than max_slides", 
                    'validation', 
                    400
                )
        
        # Prepare configuration data
        config_data = {
            'name': data['name'].strip(),
            'description': data.get('description', ''),
            'presentation_type': data.get('presentation_type', 'custom'),
            'sections': data['sections'],
            'global_settings': data.get('global_settings', {}),
            'is_public': data.get('is_public', False)
        }
        
        logger.info(f"Creating structure config: {config_data['name']}")
        
        # Save to database
        config = db_manager.save_custom_structure(session_id, config_data)
        
        logger.info(f"Structure config saved: {config.get('name')} (ID: {config.get('id')})")
        
        return jsonify({
            'success': True,
            'message': 'Structure configuration created successfully',
            'configuration': config,
            'timestamp': datetime.utcnow().isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create structure config: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to create configuration: {str(e)}", 'structure', 500)


# ==================== SESSION MANAGEMENT ENDPOINTS ====================

@app.route('/api/session', methods=['GET'])
def get_session_info():
    """
    Get current session information and preferences
    
    Returns:
        JSON response with session details
    """
    try:
        # Get session ID
        session_id = get_or_create_session_id()
        
        # Get user preferences if database is available
        preferences = None
        generation_count = 0
        
        if db_manager:
            try:
                preferences = db_manager.get_user_preferences(session_id)
                
                # Get generation history count
                history = db_manager.get_generation_history(session_id, limit=100)
                generation_count = len(history)
                
            except Exception as db_error:
                logger.warning(f"Could not get session data from database: {str(db_error)}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'preferences': preferences,
            'statistics': {
                'total_generations': generation_count
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get session info: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to get session info: {str(e)}", 'session', 500)


@app.route('/api/session/preferences', methods=['POST'])
def update_preferences():
    """
    Update user preferences for the current session
    
    Returns:
        JSON response with update status
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        # Get session ID
        session_id = get_or_create_session_id()
        
        # Get JSON data
        if not request.is_json:
            return create_error_response("Request must be JSON", 'validation', 400)
        
        data = request.get_json()
        
        # Validate preference keys
        valid_keys = [
            'last_template_id', 
            'last_structure_config_id',
            'preferred_presentation_type',
            'auto_detect_enabled',
            'ui_preferences',
            'generation_preferences'
        ]
        
        # Filter only valid keys
        preferences_data = {
            key: value for key, value in data.items() 
            if key in valid_keys
        }
        
        if not preferences_data:
            return create_error_response("No valid preferences provided", 'validation', 400)
        
        logger.info(f"Updating preferences for session: {session_id[:8]}...")
        
        # Update in database
        db_manager.update_user_preferences(session_id, preferences_data)
        
        logger.info("Preferences updated successfully")
        
        return jsonify({
            'success': True,
            'message': 'Preferences updated successfully',
            'updated_fields': list(preferences_data.keys()),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update preferences: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to update preferences: {str(e)}", 'preferences', 500)


@app.route('/api/history', methods=['GET'])
def get_generation_history():
    """
    Get generation history for the current session
    
    Returns:
        JSON response with generation history
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)
        
        # Get session ID
        session_id = get_or_create_session_id()
        
        # Get query parameters
        limit = request.args.get('limit', 20, type=int)
        limit = min(max(limit, 1), 100)  # Clamp between 1 and 100
        
        logger.info(f"Fetching generation history for session: {session_id[:8]}...")
        
        # Get history from database
        history = db_manager.get_generation_history(session_id, limit=limit)
        
        # Add download URLs
        for item in history:
            if item.get('filename'):
                item['download_url'] = f"/api/download/{item['filename']}"
        
        logger.info(f"Found {len(history)} history items")
        
        return jsonify({
            'success': True,
            'history': history,
            'total': len(history),
            'limit': limit,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get generation history: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to get history: {str(e)}", 'history', 500)
    
    
# ==================== PRESENTATION VERSIONING ENDPOINTS ====================

@app.route('/api/lineages', methods=['GET'])
def list_lineages():
    """
    List all presentation lineages owned by the current session.

    Query params:
        limit (int, optional): max entries; clamped to
            [1, VERSIONING_CONFIG['max_lineage_list_limit']].
            Defaults to VERSIONING_CONFIG['default_lineage_list_limit'].

    Returns:
        JSON with `lineages` list (newest-first by latest version's
        created_at), `total`, `limit`, and `timestamp`. Flat shape
        matching /api/history.
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)

        session_id = get_or_create_session_id()

        default_limit = VERSIONING_CONFIG.get('default_lineage_list_limit', 20)
        max_limit = VERSIONING_CONFIG.get('max_lineage_list_limit', 100)
        limit = request.args.get('limit', default_limit, type=int)
        limit = max(1, min(limit, max_limit))

        logger.info(f"Fetching lineages for session: {session_id[:8]}... (limit={limit})")

        lineages = db_manager.get_lineages_for_session(session_id, limit=limit)

        return jsonify({
            'success': True,
            'lineages': lineages,
            'total': len(lineages),
            'limit': limit,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Failed to list lineages: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to list lineages: {str(e)}", 'lineages', 500)


@app.route('/api/lineages/<int:lineage_id>/versions', methods=['GET'])
def list_versions_in_lineage(lineage_id):
    """
    List versions in a lineage owned by the current session.

    Versions are returned oldest-first (v1 → vN). Each entry exposes
    metadata only — slide_structure is intentionally omitted here
    (potentially large); callers fetch a specific snapshot via the
    single-version endpoint below.

    Returns 404 `not_found` when the lineage doesn't exist OR exists
    but is owned by a different session — the two cases are
    indistinguishable to the caller (existence-leak guard).
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)

        session_id = get_or_create_session_id()
        logger.info(
            f"Fetching versions for lineage {lineage_id}, session: {session_id[:8]}..."
        )

        versions = db_manager.get_versions_for_lineage(lineage_id, session_id)
        if versions is None:
            return create_error_response("Not found", 'not_found', 404)

        projected = [
            {
                'version_number': v['version_number'],
                'label': v['label'],
                'note': v['note'],
                'created_at': v['created_at'],
                'has_snapshot': v.get('slide_structure') is not None,
            }
            for v in versions
        ]

        return jsonify({
            'success': True,
            'lineage_id': lineage_id,
            'versions': projected,
            'total': len(projected),
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Failed to list versions: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to list versions: {str(e)}", 'versions', 500)


@app.route('/api/lineages/<int:lineage_id>/versions/<int:version_number>', methods=['GET'])
def get_version_detail(lineage_id, version_number):
    """
    Fetch a single version's full content, including slide_structure.

    Returns 404 `not_found` when the version doesn't exist OR exists
    but is owned by a different session — same existence-leak guard
    as the list endpoint above.
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)

        session_id = get_or_create_session_id()
        logger.info(
            f"Fetching version {version_number} of lineage {lineage_id}, "
            f"session: {session_id[:8]}..."
        )

        version = db_manager.get_version(lineage_id, version_number, session_id)
        if version is None:
            return create_error_response("Not found", 'not_found', 404)

        return jsonify({
            'success': True,
            'lineage_id': lineage_id,
            'version_number': version['version_number'],
            'label': version['label'],
            'note': version['note'],
            'created_at': version['created_at'],
            'filename': version['filename'],
            'slide_structure': version['slide_structure'],
            'is_stub': version['is_stub'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Failed to get version: {str(e)}", exc_info=True)
        return create_error_response(f"Failed to get version: {str(e)}", 'version', 500)


@app.route('/api/lineages/<int:lineage_id>/versions/<int:version_number>/download', methods=['GET'])
def download_version(lineage_id, version_number):
    """
    Stream a specific version's .pptx file as an attachment.

    Returns 404 `not_found` for all of:
      - row doesn't exist
      - row exists but is owned by a different session
      - row has NULL file_path (stub backfill row)
      - file_path is set but the file is gone from disk (cleanup sweeper
        or manual delete)
    All four collapse to the same response to preserve the existence-
    leak guard (spec §Behavior / Resolved Decisions).
    """
    try:
        if not db_manager:
            return create_error_response("Database not available", 'database', 503)

        session_id = get_or_create_session_id()
        logger.info(
            f"Downloading version {version_number} of lineage {lineage_id}, "
            f"session: {session_id[:8]}..."
        )

        version = db_manager.get_version(lineage_id, version_number, session_id)
        if version is None:
            return create_error_response("Not found", 'not_found', 404)

        file_path = version.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return create_error_response("Not found", 'not_found', 404)

        download_name = version.get('filename') or os.path.basename(file_path)
        return send_file(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            as_attachment=True,
            download_name=download_name,
        )

    except Exception as e:
        logger.error(f"Failed to download version: {str(e)}", exc_info=True)
        return create_error_response(
            f"Failed to download version: {str(e)}",
            'version_download',
            500,
        )


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return create_error_response("Endpoint not found", 'not_found', 404)


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    max_size_mb = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    return create_error_response(
        f"File too large. Maximum size: {max_size_mb}MB", 
        'file_size', 
        413
    )


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}", exc_info=True)
    return create_error_response("Internal server error", 'internal', 500)


# ==================== DATABASE INITIALIZATION ====================

# Initialize database on module load
if not initialize_database():
    logger.warning("⚠️ Running without database - some features will be limited")


# ==================== MAIN ENTRY POINT ====================

if __name__ == '__main__':
    # Print startup information
    print("\n" + "="*60)
    print("🚀 PPT Generator API Server Starting...")
    print("="*60)
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🤖 Default Ollama model: {DEFAULT_MODEL}")
    print(f"🌐 Ollama URL: {OLLAMA_BASE_URL}")
    print(f"📦 Max file size: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f}MB")
    
    # Database status
    if db_manager:
        print(f"🗄️ Database: Connected")
        stats = db_manager.get_statistics()
        print(f"   - Templates: {stats.get('total_templates', 0)}")
        print(f"   - Structure configs: {stats.get('total_structure_configs', 0)}")
    else:
        print(f"🗄️ Database: Not available")
    
    print("="*60)
    print("📡 API Endpoints:")
    print("   POST   /api/generate-ppt  - Generate presentation")
    print("   GET    /api/download/<filename> - Download file")
    print("   GET    /api/health        - Health check")
    print("   GET    /api/models        - List models")
    print("   DELETE /api/cleanup       - Cleanup old files")
    print("="*60)
    print("🎯 Server running at: http://localhost:5000")
    print("🔧 React frontend should connect to: http://localhost:5000/api")
    print("="*60 + "\n")
    
    # Run Flask app
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,
        threaded=True
    )