"""
API Testing Script for PPT Generator
Tests different presentation types with realistic content
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

# ==================== TEST CONTENT FOR DIFFERENT PRESENTATION TYPES ====================

# Business Report Content
REPORT_CONTENT = """
Q4 2024 Business Performance Report

Executive Summary:
Our company has achieved significant growth in Q4 2024, with revenue increasing by 23% year-over-year to reach $4.2 million. This growth was primarily driven by strong performance in our enterprise segment and successful launch of three new products.

Key Performance Metrics:
Total Revenue: $4.2M (23% increase from Q4 2023)
Customer Acquisition: 450 new customers (15% above target)
Customer Retention Rate: 92% (industry average: 85%)
Average Deal Size: $28,000 (increased from $22,000 in Q3)
Operating Margin: 18% (improved from 14% last quarter)

Market Analysis:
The market conditions remained favorable with increased demand for digital transformation solutions. Our competitive positioning has strengthened due to our AI-powered features that differentiate us from competitors. Market research indicates a 35% growth potential in the SMB segment for next year.

Product Performance:
Product A: Generated $2.1M in revenue, 50% of total revenue
Product B: $1.3M revenue with 89% customer satisfaction score  
Product C: New launch exceeded targets by 40% with $800K in first quarter

Challenges Identified:
Supply chain delays impacted delivery times by average of 5 days. Technical support ticket resolution time increased to 48 hours from 36 hours. Need to scale infrastructure to support growing customer base.

Recommendations:
1. Invest additional $500K in infrastructure upgrades
2. Hire 10 additional support staff to improve response times
3. Establish secondary supplier relationships to mitigate supply chain risks
4. Develop automated onboarding to improve customer experience

Next Steps:
Finalize Q1 2025 budget allocation by January 15th. Launch customer success program by February 1st. Complete infrastructure upgrade by end of Q1.
"""

# Pitch Deck Content  
PITCH_CONTENT = """
TechVenture AI - Investment Opportunity

The Problem:
Small businesses lose $75 billion annually due to inefficient inventory management. Current solutions are either too expensive (SAP, Oracle) costing over $100K annually, or too basic (spreadsheets) leading to human errors. 60% of SMBs still use manual processes for inventory tracking resulting in 23% average overstock and 18% stockouts.

Our Solution - SmartInventory AI:
We've developed an AI-powered inventory management platform that predicts demand with 94% accuracy. Our solution integrates with existing POS systems in under 2 hours. Machine learning algorithms analyze 50+ data points including weather, local events, and social trends. Automated reordering reduces stockouts by 75% while cutting overstock by 60%.

Market Opportunity:
Total Addressable Market (TAM): $12 billion globally
Serviceable Addressable Market (SAM): $3.2 billion in North America
Serviceable Obtainable Market (SOM): $320 million in next 5 years
Growing at 18% CAGR with acceleration due to post-pandemic digitalization

Business Model:
SaaS subscription model with three tiers:
Starter: $299/month for businesses with <1000 SKUs
Professional: $799/month for 1000-5000 SKUs  
Enterprise: $2,499/month for 5000+ SKUs
Average Customer Lifetime Value: $45,000
Customer Acquisition Cost: $3,000
Gross Margins: 78%

Traction and Validation:
150 paying customers with $2.1M ARR
Month-over-month growth: 22%
Net Revenue Retention: 125%
Customer testimonials from Fortune 500 suppliers
Partnership with Shopify and Square

The Team:
CEO: Jane Smith - 15 years experience, former VP at Amazon Supply Chain
CTO: John Doe - Stanford PhD in AI, 8 patents in predictive analytics
VP Sales: Mike Johnson - Built sales teams at 3 unicorns
Advisory Board includes former Walmart CIO and MIT Professor

Funding Ask:
Raising $10M Series A to accelerate growth
Use of funds:
- 40% Sales and Marketing expansion
- 30% Product development and AI enhancement  
- 20% Operations and infrastructure
- 10% Working capital

Expected ROI:
Projected to reach $50M ARR in 3 years
Path to $100M valuation by Year 5
Potential exit opportunities to major ERP players
"""

# Business Review Content
BUSINESS_REVIEW_CONTENT = """
Q4 2024 Quarterly Business Review

Performance Overview:
This quarter marked our strongest performance in company history. We exceeded revenue targets by 12% and expanded into 3 new markets. Employee satisfaction scores reached all-time high of 87%.

Revenue Performance:
Q4 Target: $3.5M
Q4 Actual: $3.92M  
YoY Growth: 28%
Recurring Revenue: 72% of total
New Business: $1.1M

Key Performance Indicators:
Sales Pipeline: $12M (3.5x coverage ratio)
Win Rate: 34% (up from 28% in Q3)
Sales Cycle: 45 days (reduced from 52 days)
CSAT Score: 4.6/5.0
Employee NPS: +42

Major Achievements:
Closed largest deal in company history worth $450K
Launched new product line generating $200K in first month
Achieved ISO 27001 certification
Won 'Best Innovation' award at industry conference
Expanded team by 25 new hires

Challenges and Mitigation:
Challenge: Higher than expected customer churn in SMB segment (15%)
Mitigation: Launching customer success program with dedicated CSMs

Challenge: Product delays due to technical debt
Mitigation: Allocated 30% of engineering capacity to refactoring

Market Opportunities:
Enterprise segment showing 45% quarter-over-quarter growth
International expansion potential in APAC region worth $5M
New partnership opportunities with system integrators

Q1 2025 Priorities:
1. Launch enterprise tier product by end of January
2. Expand sales team by 8 additional AEs
3. Implement new CRM system
4. Begin APAC market entry planning
"""

# Case Study Content
CASE_STUDY_CONTENT = """
Digital Transformation Success Story: GlobalRetail Corp

Client Background:
GlobalRetail Corp is a Fortune 500 retailer with 2,000+ stores across North America. Annual revenue of $45 billion with 150,000 employees. They were struggling with legacy systems causing $50M annual losses due to inefficiencies.

The Challenge:
Inventory data scattered across 15 different systems with no real-time visibility. Manual processes taking 200+ hours per week across teams. Customer complaints about out-of-stock items increased by 40%. Inability to compete with Amazon and other digital-first retailers. IT infrastructure costs growing 20% annually with declining performance.

Our Approach:
Conducted 3-week assessment of current state across all systems. Developed cloud-first architecture leveraging microservices. Implemented agile transformation with 2-week sprints. Created unified data lake consolidating all inventory sources. Built real-time analytics dashboard for executive visibility.

Solution Implementation:
Phase 1: Migrated core inventory system to cloud (3 months)
Phase 2: Integrated POS and e-commerce platforms (2 months)  
Phase 3: Deployed AI-powered demand forecasting (2 months)
Phase 4: Launched mobile app for store managers (1 month)
Phase 5: Training and change management (ongoing)

Technical Architecture:
Frontend: React Native mobile apps, Angular web dashboard
Backend: Node.js microservices on Kubernetes
Database: MongoDB for transactions, Snowflake for analytics
AI/ML: TensorFlow for demand prediction
Infrastructure: AWS with multi-region deployment

Results Achieved:
Reduced inventory holding costs by 35% ($125M annual savings)
Improved stock availability from 87% to 96%
Decreased time-to-insight from 3 days to real-time
IT operational costs reduced by 40%
Customer satisfaction increased from 3.2 to 4.5 stars

Success Metrics:
ROI achieved in 8 months (expected was 18 months)
99.95% system uptime vs 94% with legacy system
Processing time for inventory updates: 2 seconds vs 2 hours
Mobile app adoption: 95% of store managers within 30 days

Key Learnings:
Executive sponsorship critical for enterprise-wide transformation
Phased approach reduces risk and allows quick wins
Change management as important as technical implementation
Cloud-native architecture provides scalability and cost efficiency
"""

# Proposal Content
PROPOSAL_CONTENT = """
Digital Marketing Transformation Proposal for ABC Corporation

Executive Summary:
We propose a comprehensive digital marketing transformation program for ABC Corporation to increase online revenue by 200% within 18 months. Our solution combines cutting-edge technology with proven marketing strategies to establish ABC as a digital leader in your industry.

Understanding Your Requirements:
ABC Corporation needs to modernize its digital presence to capture growing online market. Current website converts at 0.5% versus industry average of 2.5%. Social media presence is fragmented across platforms with no unified strategy. Marketing data is siloed preventing comprehensive customer view. Need to compete with digital-native competitors entering your market.

Proposed Solution:
Complete website redesign using conversion-optimized architecture. Implementation of marketing automation platform (HubSpot/Marketo). Social media management across 6 major platforms. Content strategy including blog, video, and podcast production. SEO optimization targeting 500+ high-value keywords. Paid advertising management across Google, Facebook, and LinkedIn.

Methodology and Approach:
Discovery Phase (Month 1): Audit current state, competitor analysis, customer research
Strategy Phase (Month 2): Develop comprehensive digital strategy and roadmap  
Implementation Phase (Months 3-8): Execute website, campaigns, and content
Optimization Phase (Months 9-18): Continuous testing and improvement

Deliverables:
New responsive website with e-commerce capabilities
Marketing automation with 50+ workflow templates
Content calendar with 200+ pieces of content
Monthly analytics reports and quarterly business reviews
Training for internal team on all platforms

Timeline:
Month 1-2: Discovery and Strategy
Month 3-4: Website Development
Month 5-6: Marketing Automation Setup
Month 7-8: Content Production Launch
Month 9-12: Campaign Optimization
Month 13-18: Scale and Expand

Investment:
Total Project Investment: $450,000
Phase 1 (Months 1-6): $250,000
Phase 2 (Months 7-12): $150,000
Phase 3 (Months 13-18): $50,000

Payment Terms:
25% upon contract signature
25% at Phase 1 completion
25% at Phase 2 completion  
25% at project completion

Expected ROI:
Conservative estimate: 300% ROI within 24 months
Break-even point: Month 10
Projected revenue increase: $2.5M in Year 1, $5M in Year 2
"""


# ==================== TEST FUNCTIONS ====================

def test_health_check():
    """Test the health check endpoint"""
    print("\n" + "="*60)
    print("Testing Health Check...")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def test_get_templates():
    """Test getting available templates"""
    print("\n" + "="*60)
    print("Testing Get Templates...")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/templates")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    
    if data.get('success'):
        print(f"Found {len(data.get('templates', []))} templates")
        for template in data.get('templates', []):
            print(f"  - {template['name']} (ID: {template['id']})")
    
    return data

# Test template upload
def test_template_upload():
    url = "http://localhost:5000/api/templates/upload"
    files = {'file': open('Corporate_Template.pptx', 'rb')}
    data = {
        'name': 'Corporate-2025',
        'category': 'corporate'
    }
    response = requests.post(url, files=files, data=data)
    print(response.json())

def test_generation(content_type="report", content=None, template_id=None):
    """
    Test PPT generation with different content types
    
    Args:
        content_type: Type of presentation to generate
        content: Custom content or use default based on type
        template_id: Optional template ID to use
    """
    print("\n" + "="*60)
    print(f"Testing PPT Generation - Type: {content_type}")
    print("="*60)
    
    # Select content based on type
    if content is None:
        content_map = {
            "report": REPORT_CONTENT,
            "pitch": PITCH_CONTENT,
            "business_review": BUSINESS_REVIEW_CONTENT,
            "case_study": CASE_STUDY_CONTENT,
            "proposal": PROPOSAL_CONTENT
        }
        content = content_map.get(content_type, REPORT_CONTENT)
    
    # Prepare request data
    data = {
        'text': content,
        'auto_detect_type': 'true',
        'model': 'llama3.2'
    }
    
    if template_id:
        data['template_id'] = template_id
    
    print(f"Content Length: {len(content)} characters")
    print(f"Auto-detect: True")
    print(f"Template ID: {template_id if template_id else 'Default'}")
    
    # Make request
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/generate-ppt", data=data)
    elapsed_time = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {elapsed_time:.2f} seconds")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Generation Successful!")
        print(f"Filename: {result.get('filename')}")
        print(f"Slides: {result.get('slide_count')}")
        print(f"Template Used: {result.get('template_used', 'Default')}")
        print(f"Detected Type: {result.get('detected_type', 'Unknown')}")
        print(f"Confidence: {result.get('confidence_score', 0)}")
        print(f"Download URL: {result.get('download_url')}")
        print(f"Processing Time: {result.get('processing_time_seconds')} seconds")
    else:
        print("\n❌ Generation Failed!")
        print(f"Error: {response.json()}")
    
    return response.json()


def test_all_presentation_types():
    """Test generation for all presentation types"""
    print("\n" + "="*60)
    print("TESTING ALL PRESENTATION TYPES")
    print("="*60)
    
    types = ["report", "pitch", "business_review", "case_study", "proposal"]
    results = {}
    
    for pres_type in types:
        print(f"\n📊 Testing {pres_type.upper()}...")
        try:
            result = test_generation(content_type=pres_type)
            results[pres_type] = {
                'success': result.get('success', False),
                'detected_type': result.get('detected_type'),
                'confidence': result.get('confidence_score'),
                'slides': result.get('slide_count')
            }
            time.sleep(2)  # Pause between requests
        except Exception as e:
            print(f"Error testing {pres_type}: {str(e)}")
            results[pres_type] = {'success': False, 'error': str(e)}
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for pres_type, result in results.items():
        status = "✅" if result['success'] else "❌"
        print(f"{status} {pres_type.upper()}: ", end="")
        if result['success']:
            print(f"Detected: {result['detected_type']}, "
                  f"Confidence: {result['confidence']}, "
                  f"Slides: {result['slides']}")
        else:
            print(f"Failed - {result.get('error', 'Unknown error')}")
    
    return results


def test_custom_content():
    """Test with your own custom content"""
    custom_content = """
    Add your own content here for testing.
    This will be converted into a presentation.
    The system will auto-detect the type and generate appropriate slides.
    """
    
    print("\n" + "="*60)
    print("Testing with Custom Content")
    print("="*60)
    
    return test_generation(content_type="custom", content=custom_content)


def main():
    """Main test execution"""
    print("\n🚀 PPT Generator API Test Suite")
    print("================================\n")
    
    # Choose what to test
    print("Select test to run:")
    print("1. Health Check")
    print("2. List Templates")
    print("3. Generate Report")
    print("4. Generate Pitch Deck")
    print("5. Generate Business Review")
    print("6. Generate Case Study")
    print("7. Generate Proposal")
    print("8. Test All Types")
    print("9. Custom Content")
    print("10. Template Upload")
    
    
    choice = input("\nEnter choice (1-9) or press Enter to test all: ").strip()
    
    if choice == "1":
        test_health_check()
    elif choice == "2":
        test_get_templates()
    elif choice == "3":
        test_generation("report")
    elif choice == "4":
        test_generation("pitch")
    elif choice == "5":
        test_generation("business_review")
    elif choice == "6":
        test_generation("case_study")
    elif choice == "7":
        test_generation("proposal")
    elif choice == "8" or choice == "":
        test_all_presentation_types()
    elif choice == "9":
        test_custom_content()
    elif choice == "10":
        test_template_upload()
    else:
        print("Invalid choice")


# ==================== FEATURE 001: PRESENTATION VERSIONING API TESTS ====================

def _cleanup_versioning_rows(session_ids):
    """Delete every users/generation_history/presentation_versions row
    whose session_id is in the given list. Idempotent; safe to call even
    when nothing was seeded."""
    import os, sqlite3
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'database', 'ppt_generator.db')
    conn = sqlite3.connect(db_path)
    deleted = {'pv': 0, 'gh': 0, 'user': 0}
    for sid in session_ids:
        if not sid:
            continue
        deleted['pv'] += conn.execute(
            "DELETE FROM presentation_versions WHERE session_id = ?", (sid,)
        ).rowcount
        deleted['gh'] += conn.execute(
            "DELETE FROM generation_history WHERE session_id = ?", (sid,)
        ).rowcount
        deleted['user'] += conn.execute(
            "DELETE FROM users WHERE session_id = ?", (sid,)
        ).rowcount
    conn.commit()
    conn.close()
    return deleted


def test_presentation_versioning_api():
    """Feature 001 — Presentation Versioning API tests.

    Hits the running Flask server. Seeds generation_history +
    presentation_versions rows directly via DatabaseManager to skip the
    slow Ollama POST (per tasks.md Task 11 notes). The seeded v1 row has
    the same shape the live POST pipeline writes. Test rows are keyed by
    the seeded session_id so cleanup is reliable.
    """
    import os, sys, hashlib
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from database.db_manager import init_database

    print("\n🚀 Testing /api/lineages* routes (feature 001)...")

    # --- Case 1: fresh session, no lineages ---
    fresh = requests.Session()
    r = fresh.get(f"{BASE_URL}/lineages", timeout=10)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body['success'] is True
    assert body['lineages'] == []
    assert body['total'] == 0
    print("✅ Case 1: fresh session GET /api/lineages → 200, empty list")

    # Discover the server-assigned session_id so seeded rows are owned by `fresh`
    sid = fresh.get(f"{BASE_URL}/session", timeout=10).json()['session_id']
    print(f"   Using primary session_id={sid[:8]}…")

    # Pick an existing .pptx in temp/ so the download bytes-equality test works
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
    real_pptx = None
    if os.path.isdir(upload_dir):
        candidates = sorted(
            [f for f in os.listdir(upload_dir) if f.endswith('.pptx')],
            reverse=True,
        )
        if candidates:
            real_pptx = os.path.join(upload_dir, candidates[0])
    placeholder_created = False
    if not real_pptx:
        os.makedirs(upload_dir, exist_ok=True)
        real_pptx = os.path.join(upload_dir, 'test_api_versioning_placeholder.pptx')
        with open(real_pptx, 'wb') as f:
            f.write(b'PK\x05\x06' + b'\x00' * 18)  # minimal empty-zip bytes
        placeholder_created = True
    real_filename = os.path.basename(real_pptx)

    other_sid = None  # captured later for cleanup
    try:
        db = init_database()

        # Seed a generation_history + v1 row owned by `fresh`
        gh = db.save_generation_history({
            'session_id': sid, 'filename': real_filename, 'file_path': real_pptx,
            'input_type': 'text', 'input_size': 100, 'model_used': 'llama3.2',
        })
        lid = gh['id']
        db.save_presentation_version({
            'lineage_id': lid, 'version_number': 1,
            'label': 'Initial generation', 'note': None,
            'slide_structure': {'slides': [{'title': 'Hello'}], 'title': 'T'},
            'file_path': real_pptx, 'filename': real_filename,
            'is_stub': False, 'session_id': sid,
        })
        print(f"   Seeded lineage_id={lid} (v1, session={sid[:8]}…, file={real_filename})")

        # --- Case 2: lineage shows up in list ---
        r = fresh.get(f"{BASE_URL}/lineages", timeout=10)
        assert r.status_code == 200
        body = r.json()
        ours = [x for x in body['lineages'] if x['lineage_id'] == lid]
        assert len(ours) == 1, f"lineage {lid} not in {body}"
        e = ours[0]
        assert e['latest_version_number'] == 1
        assert e['latest_version_label'] == 'Initial generation'
        assert e['total_versions'] == 1
        print("✅ Case 2: lineage in list with latest_version_number=1 + 'Initial generation' label")

        # --- Case 3: versions list ---
        r = fresh.get(f"{BASE_URL}/lineages/{lid}/versions", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body['lineage_id'] == lid and body['total'] == 1
        v = body['versions'][0]
        assert v['version_number'] == 1
        assert v['has_snapshot'] is True
        assert 'slide_structure' not in v  # not projected in list responses
        print("✅ Case 3: versions list returns one version, has_snapshot=true")

        # --- Case 4: version detail ---
        r = fresh.get(f"{BASE_URL}/lineages/{lid}/versions/1", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body['slide_structure'] is not None
        assert body['is_stub'] is False
        for key in ('lineage_id', 'version_number', 'label', 'note',
                    'created_at', 'filename', 'slide_structure', 'is_stub'):
            assert key in body, f"missing key {key}"
        print("✅ Case 4: version detail returns non-null slide_structure, is_stub=false")

        # --- Case 5: download, bytes equal legacy /api/download/<filename> ---
        r = fresh.get(f"{BASE_URL}/lineages/{lid}/versions/1/download", timeout=10)
        assert r.status_code == 200, r.text[:300]
        ctype = r.headers.get('Content-Type', '')
        assert ctype.startswith('application/vnd.openxmlformats'), f"got {ctype}"
        assert len(r.content) > 0
        legacy = fresh.get(f"{BASE_URL}/download/{real_filename}", timeout=10)
        assert legacy.status_code == 200
        assert hashlib.sha256(r.content).hexdigest() \
            == hashlib.sha256(legacy.content).hexdigest(), \
            "bytes diverge from legacy /api/download"
        print(f"✅ Case 5: download 200, correct mimetype, {len(r.content)} bytes, SHA-256 matches legacy")

        # --- Case 6: missing lineage → 404 not_found ---
        r = fresh.get(f"{BASE_URL}/lineages/9999999/versions", timeout=10)
        assert r.status_code == 404 and r.json().get('error_type') == 'not_found'
        print("✅ Case 6: missing lineage → 404 not_found")

        # --- Case 7: cross-session via second fresh session ---
        other = requests.Session()
        other_sid = other.get(f"{BASE_URL}/session", timeout=10).json()['session_id']
        r = other.get(f"{BASE_URL}/lineages/{lid}/versions", timeout=10)
        assert r.status_code == 404 and r.json().get('error_type') == 'not_found'
        r = other.get(f"{BASE_URL}/lineages/{lid}/versions/1", timeout=10)
        assert r.status_code == 404 and r.json().get('error_type') == 'not_found'
        r = other.get(f"{BASE_URL}/lineages/{lid}/versions/1/download", timeout=10)
        assert r.status_code == 404 and r.json().get('error_type') == 'not_found'
        print("✅ Case 7: cross-session → 404 not_found on all three read routes")

        # --- Case 8: stub row with file_path=NULL → 404 not_found ---
        stub_lid = lid + 1_000_000  # synthetic id; FK isn't enforced in SQLite
        db.save_presentation_version({
            'lineage_id': stub_lid, 'version_number': 1,
            'label': 'Initial generation', 'note': None,
            'slide_structure': None, 'file_path': None, 'filename': None,
            'is_stub': True, 'session_id': sid,
        })
        r = fresh.get(f"{BASE_URL}/lineages/{stub_lid}/versions/1/download", timeout=10)
        assert r.status_code == 404 and r.json().get('error_type') == 'not_found'
        print("✅ Case 8: stub row (file_path=NULL) download → 404 not_found")

        print("\n✅ All presentation versioning API tests passed!")
        return True

    finally:
        # Clean up everything keyed by our test session_ids
        deleted = _cleanup_versioning_rows([sid, other_sid])
        print(f"Cleanup: deleted pv={deleted['pv']}, gh={deleted['gh']}, "
              f"users={deleted['user']}")
        if placeholder_created and os.path.exists(real_pptx):
            try:
                os.remove(real_pptx)
                print(f"Cleanup: removed placeholder pptx {real_filename}")
            except Exception:
                pass


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == 'menu':
        # Interactive menu preserved — `python test_api.py menu`
        main()
    else:
        # Default: run the feature-001 API smoke tests and exit non-zero on failure
        try:
            ok = test_presentation_versioning_api()
            if ok:
                print("\n🎉 API tests passed!")
        except Exception as e:
            print(f"\n❌ {e}")
            import traceback
            traceback.print_exc()
            _sys.exit(1)