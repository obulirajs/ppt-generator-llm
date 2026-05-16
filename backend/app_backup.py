"""
Flask Application - PPT Generator API
Main backend service for converting text/documents to PowerPoint presentations
Uses local Ollama LLM for content structuring
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import time
import logging
from datetime import datetime

# Import utility modules
from utils import document_parser, llm_service, ppt_generator


# ==================== CONFIGURATION ====================

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Flask Configuration
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'temp')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

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
        
        response = {
            "application_name": "PPT Penerator (Backend)",
            'status': 'healthy' if is_connected else 'degraded',
            'api_version': '1.0.0',
            'ollama_connected': is_connected,
            'ollama_url': OLLAMA_BASE_URL,
            'available_models': available_models,
            'default_model': DEFAULT_MODEL,
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
    Main endpoint to generate PowerPoint presentation
    Accepts either file upload or direct text input
    
    Returns:
        JSON response with file information or error
    """
    start_time = time.time()
    temp_file_path = None
    
    try:
        # Validate request
        is_valid, error_msg, input_type = validate_request()
        if not is_valid:
            return create_error_response(error_msg, 'validation', 400)
        
        logger.info(f"Received request - Input type: {input_type}")
        
        # Get model name
        model_name = get_model_from_request()
        logger.info(f"Using model: {model_name}")
        
        # Extract text based on input type
        extracted_text = None
        
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
                logger.info(f"Processed {len(extracted_text)} characters of direct text")
            except Exception as e:
                return create_error_response(f"Invalid text input: {str(e)}", 'validation', 400)
        
        elif input_type == 'json':
            # Handle JSON body
            data = request.get_json()
            text_input = data['text']
            try:
                extracted_text = document_parser.process_direct_text(text_input)
                logger.info(f"Processed {len(extracted_text)} characters from JSON")
            except Exception as e:
                return create_error_response(f"Invalid text input: {str(e)}", 'validation', 400)
        
        # Validate extracted content
        is_valid, warning, processed_text = document_parser.validate_content(extracted_text)
        if not is_valid:
            return create_error_response(warning, 'validation', 400)
        
        if warning:
            logger.warning(warning)
        
        # Generate presentation structure using LLM
        try:
            logger.info("Generating presentation structure with LLM...")
            structure = llm_service.generate_presentation_structure(processed_text, model_name)
            logger.info(f"Generated structure with {len(structure.get('slides', []))} slides")
        except Exception as e:
            return create_error_response(f"Failed to generate structure: {str(e)}", 'llm', 500)
        
        # Validate structure
        is_valid, error_msg = ppt_generator.validate_structure(structure)
        if not is_valid:
            return create_error_response(f"Invalid presentation structure: {error_msg}", 'structure', 500)
        
        # Generate PowerPoint file
        try:
            logger.info("Creating PowerPoint presentation...")
            ppt_file_path = ppt_generator.create_presentation(
                structure, 
                app.config['UPLOAD_FOLDER']
            )
            logger.info(f"PowerPoint created: {os.path.basename(ppt_file_path)}")
        except Exception as e:
            return create_error_response(f"Failed to create presentation: {str(e)}", 'generation', 500)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Return success response
        return create_success_response(ppt_file_path, processing_time)
    
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


# ==================== MAIN ENTRY POINT ====================

if __name__ == '__main__':
    # Print startup information
    print("\n" + "="*60)
    print("🚀 PPT Generator API Server Starting...")
    print("="*60)
    print(f"📍 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🤖 Default Ollama model: {DEFAULT_MODEL}")
    print(f"🌐 Ollama URL: {OLLAMA_BASE_URL}")
    print(f"📦 Max file size: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f}MB")
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