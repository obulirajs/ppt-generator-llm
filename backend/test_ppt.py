from utils.ppt_generator import create_presentation, validate_structure

# Test structure
test_structure = {
    "title": "Test Presentation",
    "slides": [
        {
            "type": "title",
            "title": "AI in Modern Business",
            "subtitle": "Transforming Organizations Through Technology"
        },
        {
            "type": "content",
            "title": "Key Benefits",
            "bullets": [
                "Automation of repetitive tasks",
                "Enhanced decision-making capabilities",
                "Improved customer experience",
                "Cost reduction and efficiency"
            ]
        },
        {
            "type": "content",
            "title": "Implementation Strategies",
            "bullets": [
                "Start with pilot projects",
                "Invest in training and development",
                "Monitor and measure results"
            ]
        }
    ]
}

# Validate
is_valid, error = validate_structure(test_structure)
print(f"Valid structure: {is_valid}")
if error:
    print(f"Error: {error}")

# Generate
try:
    file_path = create_presentation(test_structure)
    print(f"\n✓ Success! File created at: {file_path}")
except Exception as e:
    print(f"Error: {e}")