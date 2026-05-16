"""
LLM Service Module
Integrates with local Ollama to generate structured presentation content
Supports: llama3.2, deepseek-r1, and other Ollama models
"""

import json
import re
import requests
from typing import Dict, List, Tuple, Optional
from config import PRESENTATION_TYPES


# Configuration Constants
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
REQUEST_TIMEOUT = 120  # seconds (longer for deepseek-r1)
MAX_RETRIES = 2
MIN_SLIDES = 3
MAX_SLIDES = 15
MAX_BULLETS_PER_SLIDE = 6


def check_ollama_connection():
    """
    Check if Ollama is running and accessible
    
    Returns:
        tuple: (is_running: bool, error_message: str or None)
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            return True, None
        return False, f"Ollama returned status code: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Ollama. Make sure Ollama is running (ollama serve)"
    except Exception as e:
        return False, f"Ollama connection error: {str(e)}"


def check_model_availability(model_name):
    """
    Check if specified model is available in Ollama
    
    Args:
        model_name (str): Name of the model to check
        
    Returns:
        tuple: (is_available: bool, error_message: str or None)
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            available_models = [model['name'] for model in data.get('models', [])]
            
            # Check if model exists (exact match or with tag)
            model_exists = any(
                model_name in model or model.startswith(model_name) 
                for model in available_models
            )
            
            if model_exists:
                return True, None
            else:
                return False, f"Model '{model_name}' not found. Available models: {', '.join(available_models)}"
        return False, "Could not retrieve model list from Ollama"
    except Exception as e:
        return False, f"Error checking model availability: {str(e)}"


def create_structured_prompt(content):
    """
    Create a detailed prompt for LLM to generate presentation structure
    
    Args:
        content (str): The text content to convert into presentation
        
    Returns:
        str: Formatted prompt with instructions
    """
    prompt = f"""You are a professional presentation designer. Analyze the following content and create a well-structured PowerPoint presentation outline.

CONTENT TO ANALYZE:
{content}

INSTRUCTIONS:
1. Create a presentation with 5-10 slides (adjust based on content length)
2. First slide should be a title slide with main title and subtitle
3. Subsequent slides should cover key topics with clear titles and bullet points
4. Each content slide should have 3-5 bullet points maximum
5. Bullet points should be concise (1-2 lines each)
6. Organize information logically with clear flow
7. Use professional and clear language

OUTPUT FORMAT:
Return ONLY a valid JSON object with this exact structure (no additional text or markdown):

{{
  "title": "Main Presentation Title",
  "slides": [
    {{
      "type": "title",
      "title": "Main Title",
      "subtitle": "Brief subtitle or tagline"
    }},
    {{
      "type": "content",
      "title": "First Topic Title",
      "bullets": [
        "First key point about this topic",
        "Second key point with relevant details",
        "Third important point"
      ]
    }},
    {{
      "type": "content",
      "title": "Second Topic Title",
      "bullets": [
        "Point one",
        "Point two",
        "Point three"
      ]
    }}
  ]
}}

Return ONLY the JSON object, nothing else."""

    return prompt


def call_ollama_api(prompt, model_name=DEFAULT_MODEL):
    """
    Make API call to local Ollama instance
    
    Args:
        prompt (str): The prompt to send to the model
        model_name (str): Name of the Ollama model to use
        
    Returns:
        str: Response text from the model
        
    Raises:
        Exception: If API call fails
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('response', '')
        else:
            raise Exception(f"Ollama API returned status code {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception(f"Request timed out after {REQUEST_TIMEOUT} seconds. Try using a faster model like llama3.2")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to Ollama. Make sure Ollama is running with 'ollama serve'")
    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


def parse_llm_response(response_text):
    """
    Parse and extract JSON from LLM response
    Handles markdown code blocks and extra text
    
    Args:
        response_text (str): Raw response from LLM
        
    Returns:
        dict: Parsed JSON structure
        
    Raises:
        Exception: If JSON cannot be parsed
    """
    try:
        # First, try to parse as-is
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_pattern, response_text, re.DOTALL)
    
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in the text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, response_text, re.DOTALL)
    
    for match in matches:
        try:
            data = json.loads(match)
            if 'title' in data and 'slides' in data:
                return data
        except json.JSONDecodeError:
            continue
    
    raise Exception("Could not extract valid JSON from LLM response")


def validate_presentation_structure(data):
    """
    Validate that the presentation structure has required fields
    
    Args:
        data (dict): Parsed JSON structure
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    # Check top-level fields
    if not isinstance(data, dict):
        return False, "Response is not a valid JSON object"
    
    if 'title' not in data:
        return False, "Missing 'title' field"
    
    if 'slides' not in data:
        return False, "Missing 'slides' field"
    
    if not isinstance(data['slides'], list):
        return False, "'slides' must be an array"
    
    if len(data['slides']) < MIN_SLIDES:
        return False, f"Need at least {MIN_SLIDES} slides"
    
    if len(data['slides']) > MAX_SLIDES:
        return False, f"Too many slides (max {MAX_SLIDES})"
    
    # Validate each slide
    for i, slide in enumerate(data['slides']):
        if not isinstance(slide, dict):
            return False, f"Slide {i+1} is not a valid object"
        
        if 'type' not in slide:
            return False, f"Slide {i+1} missing 'type' field"
        
        if slide['type'] not in ['title', 'content']:
            return False, f"Slide {i+1} has invalid type: {slide['type']}"
        
        if 'title' not in slide:
            return False, f"Slide {i+1} missing 'title' field"
        
        if slide['type'] == 'content':
            if 'bullets' not in slide:
                return False, f"Content slide {i+1} missing 'bullets' field"
            
            if not isinstance(slide['bullets'], list):
                return False, f"Slide {i+1} bullets must be an array"
            
            if len(slide['bullets']) == 0:
                return False, f"Slide {i+1} has no bullet points"
    
    return True, None


def sanitize_presentation_structure(data):
    """
    Clean and sanitize the presentation structure
    
    Args:
        data (dict): Presentation structure
        
    Returns:
        dict: Sanitized structure
    """
    # Ensure title is a string
    data['title'] = str(data['title']).strip()
    
    # Limit and sanitize slides
    data['slides'] = data['slides'][:MAX_SLIDES]
    
    for slide in data['slides']:
        slide['title'] = str(slide['title']).strip()
        
        if slide['type'] == 'title' and 'subtitle' in slide:
            slide['subtitle'] = str(slide['subtitle']).strip()
        
        if slide['type'] == 'content' and 'bullets' in slide:
            # Limit bullets per slide
            slide['bullets'] = slide['bullets'][:MAX_BULLETS_PER_SLIDE]
            # Sanitize each bullet
            slide['bullets'] = [str(bullet).strip() for bullet in slide['bullets']]
            # Remove empty bullets
            slide['bullets'] = [b for b in slide['bullets'] if b]
    
    return data


def create_fallback_structure(content):
    """
    Create a basic presentation structure if LLM fails
    
    Args:
        content (str): Original content
        
    Returns:
        dict: Basic presentation structure
    """
    # Split content into paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    # Create title from first line or paragraph
    first_line = content.split('\n')[0].strip()
    title = first_line[:100] if first_line else "Presentation"
    
    slides = [
        {
            "type": "title",
            "title": title,
            "subtitle": "Generated Presentation"
        }
    ]
    
    # Create content slides from paragraphs
    for i, para in enumerate(paragraphs[:8], 1):  # Max 8 content slides
        # Split paragraph into sentences for bullets
        sentences = [s.strip() + '.' for s in para.split('.') if s.strip()]
        bullets = sentences[:5]  # Max 5 bullets
        
        if bullets:
            slides.append({
                "type": "content",
                "title": f"Topic {i}",
                "bullets": bullets
            })
    
    return {
        "title": title,
        "slides": slides
    }


def generate_presentation_structure(content, model_name=None):
    """
    Main function to generate presentation structure from content
    
    Args:
        content (str): Text content to convert
        model_name (str, optional): Ollama model to use
        
    Returns:
        dict: Structured presentation data
        
    Raises:
        Exception: If generation fails completely
    """
    # Use default model if not specified
    if not model_name:
        model_name = DEFAULT_MODEL
    
    # Check Ollama connection
    is_running, error = check_ollama_connection()
    if not is_running:
        raise Exception(error)
    
    # Check model availability
    is_available, error = check_model_availability(model_name)
    if not is_available:
        raise Exception(error)
    
    # Create prompt
    prompt = create_structured_prompt(content)
    
    # Try to generate with retries
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Generating presentation structure (attempt {attempt + 1}/{MAX_RETRIES})...")
            
            # Call Ollama API
            response_text = call_ollama_api(prompt, model_name)
            
            # Parse response
            data = parse_llm_response(response_text)
            
            # Validate structure
            is_valid, error = validate_presentation_structure(data)
            if not is_valid:
                raise Exception(f"Invalid structure: {error}")
            
            # Sanitize and return
            data = sanitize_presentation_structure(data)
            print("✓ Presentation structure generated successfully")
            return data
            
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print("Retrying...")
    
    # If all retries failed, use fallback
    print(f"All attempts failed. Using fallback structure. Error: {last_error}")
    return create_fallback_structure(content)


def get_available_models():
    """
    Get list of available Ollama models
    
    Returns:
        list: List of model names
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        return []
    except Exception:
        return []
    
def detect_presentation_type(content, model_name=DEFAULT_MODEL):
    """
    Detect the type of presentation based on content analysis
    Uses LLM to analyze content and determine the most appropriate presentation type
    Configuration-driven approach using PRESENTATION_TYPES from config.py
    
    Args:
        content (str): The text content to analyze
        model_name (str): Name of the Ollama model to use
        
    Returns:
        dict: Detection result with type, confidence, and reasoning
    """
    try:
        print(f"Analyzing content to detect presentation type...")
        
        # Get presentation types from configuration
        presentation_types = {}
        for pres_type, config in PRESENTATION_TYPES.items():
            presentation_types[pres_type] = config.get('description', config.get('name', pres_type))
        
        # Create type descriptions for the prompt
        type_descriptions = '\n'.join([f"- {k}: {v}" for k, v in presentation_types.items()])
        
        # Create the detection prompt
        prompt = f"""Analyze the following content and determine what type of presentation it should be.

Available presentation types:
{type_descriptions}

Content to analyze (first 3000 characters):
{content[:3000]}

Based on this content, determine:
1. The most appropriate presentation type from the list above
2. Your confidence level (0.0 to 1.0)
3. Key indicators that led to this classification

Respond in JSON format:
{{
    "type": "detected_type",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this type was chosen",
    "key_indicators": ["indicator1", "indicator2", "indicator3"]
}}

IMPORTANT: The "type" field must be exactly one of: {', '.join(presentation_types.keys())}"""
        
        # Check Ollama connection first
        is_connected, error = check_ollama_connection()
        if not is_connected:
            print(f"Ollama not connected, using keyword-based detection")
            return detect_presentation_type_fallback(content)
        
        # Call Ollama API
        url = f"{OLLAMA_BASE_URL}/api/generate"
        
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent detection
                "top_p": 0.9
            }
        }
        
        response = requests.post(
            url,
            json=payload,
            timeout=30  # Shorter timeout for detection
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', '')
            
            # Parse JSON response
            try:
                detection_result = json.loads(response_text)
                
                # Validate the detected type
                detected_type = detection_result.get('type', 'report')
                if detected_type not in presentation_types:
                    print(f"Invalid type detected: {detected_type}, defaulting to 'report'")
                    detected_type = 'report'
                
                # Ensure confidence is between 0 and 1
                confidence = detection_result.get('confidence', 0.5)
                confidence = max(0.0, min(1.0, float(confidence)))
                
                result = {
                    'type': detected_type,
                    'confidence': confidence,
                    'reasoning': detection_result.get('reasoning', 'Analysis completed'),
                    'key_indicators': detection_result.get('key_indicators', [])
                }
                
                print(f"✓ Detected presentation type: {detected_type} (confidence: {confidence:.2f})")
                return result
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {str(e)}")
                return detect_presentation_type_fallback(content)
        else:
            print(f"Ollama API returned status code {response.status_code}")
            return detect_presentation_type_fallback(content)
            
    except requests.exceptions.Timeout:
        print("Detection request timed out, using fallback")
        return detect_presentation_type_fallback(content)
    except Exception as e:
        print(f"Error in presentation type detection: {str(e)}")
        return detect_presentation_type_fallback(content)


def detect_presentation_type_fallback(content):
    """
    Fallback keyword-based detection when LLM is unavailable
    Uses keywords from configuration for flexible detection
    
    Args:
        content (str): The text content to analyze
        
    Returns:
        dict: Detection result based on keyword analysis
    """
    content_lower = content.lower()
    
    # Calculate scores for each type using configuration
    scores = {}
    for pres_type, config in PRESENTATION_TYPES.items():
        keywords = config.get('keywords', [])
        weight = config.get('keyword_weight', 1.0)
        
        score = 0
        matched_keywords = []
        
        for keyword in keywords:
            if keyword in content_lower:
                score += weight
                matched_keywords.append(keyword)
        
        scores[pres_type] = {
            'score': score,
            'matched': matched_keywords
        }
    
    # Find the type with highest score
    best_type = 'report'  # Default
    best_score = 0
    best_matched = []
    
    for pres_type, result in scores.items():
        if result['score'] > best_score:
            best_score = result['score']
            best_type = pres_type
            best_matched = result['matched']
    
    # Calculate confidence based on score and matched keywords
    if best_score > 5:
        confidence = 0.8
    elif best_score > 3:
        confidence = 0.6
    elif best_score > 1:
        confidence = 0.4
    else:
        confidence = 0.3
    
    print(f"✓ Fallback detection: {best_type} (confidence: {confidence:.2f})")
    
    return {
        'type': best_type,
        'confidence': confidence,
        'reasoning': f"Detected based on keyword analysis. Found {len(best_matched)} relevant keywords.",
        'key_indicators': best_matched[:5]  # Return top 5 matched keywords
    }