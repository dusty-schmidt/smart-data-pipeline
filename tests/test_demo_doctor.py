
import sys
import time
from unittest.mock import MagicMock, patch
import json
from loguru import logger
from src.utils.logger import logger as custom_logger # Test our logger
from src.agents.doctor import DoctorAgent, DiagnosisContext, Diagnosis
from src.orchestration.health import HealthTracker, SourceState

# Setup reliable demo environment
def test_demo_doctor_is_in():
    print("\n🩺 THE DOCTOR IS IN: System Capabilities Demo 🩺\n")
    print("="*60)
    
    # 1. Demonstate Structured Logging
    print("\n[1] DEMO: Structured Logging & Error Recovery")
    print("-" * 40)
    
    custom_logger.info("System initializing...")
    custom_logger.info("Checking vital signs...")
    
    # Simulate a transient failure to show retries (using a mock for visual simplicity)
    print("   > Simulating unstable connection to Knowledge Base...")
    
    retry_counter = 0
    def unstable_operation():
        nonlocal retry_counter
        retry_counter += 1
        if retry_counter < 3:
            custom_logger.warning(f"Connection attempt {retry_counter} failed. Retrying...")
            raise ConnectionError("Network blip")
        custom_logger.success("Connection established!")
        
    try:
        # DIY retry loop to mimic tenacity visual for demo
        for i in range(3):
            try:
                unstable_operation()
                break
            except ConnectionError:
                time.sleep(0.5)
    except Exception as e:
        pass

    # 2. Demonstrate Doctor Logic
    print("\n[2] DEMO: The Doctor (Self-Healing)")
    print("-" * 40)
    
    # Initialize Doctor with in-memory DB
    doctor = DoctorAgent(db_path=":memory:")
    
    # Create a synthetic "sick" source
    source_name = "broken_scraper_v1"
    error = ValueError("SelectorNotFound: div.price_box")
    
    custom_logger.info(f"Patient arrived: {source_name}")
    custom_logger.error(f"Symptoms: {error}")
    
    # Mock LLM for deterministic demo
    mock_responses = {
        # Diagnosis
        "Diagnose": json.dumps({
            "root_cause": "The website changed its layout. 'div.price_box' is now 'span.new-price'.",
            "fix_strategy": "patch",
            "suggested_fix": "Update selector to 'span.new-price'",
            "confidence": 0.95
        }),
        # Patch
        "Apply the fix": """
class BrokenScraperV1:
    def parse(self, html):
        # PATCHED: Updated selector
        return html.find("span", class_="new-price").text
""",
        # Learning
        "Extract a generalized lesson": json.dumps({
            "domain_pattern": "ecommerce_sites",
            "symptom_description": "Price selector not found",
            "fix_strategy": "Look for semantic class names like 'new-price'",
            "reasoning": "Modern frameworks often use functional class names"
        })
    }
    
    def mock_ask_llm(prompt, **kwargs):
        for key, response in mock_responses.items():
            if key in prompt:
                return response
        return "{}"

    # We need to mock _get_source_code and deploy_to_staging since files don't exist
    with patch.object(doctor, 'ask_llm', side_effect=mock_ask_llm), \
         patch.object(doctor, '_get_source_code', return_value="Original Code"), \
         patch.object(doctor, 'deploy_to_staging', return_value=True), \
         patch.object(doctor, 'validate_staged', return_value=True), \
         patch.object(doctor, 'promote_to_production', return_value=True):
        
        # Run the healing workflow
        success = doctor.heal(source_name, error)
        
    if success:
        print("\n[3] DEMO: The Learner (Knowledge Base)")
        print("-" * 40)
        
        # Verify the lesson was learned
        session = doctor.Session()
        from src.storage.models import Lesson
        lessons = session.query(Lesson).all()
        
        if lessons:
            l = lessons[0]
            custom_logger.info(f"New Lesson Learned!")
            print(f"   - Error: {l.error_type}")
            print(f"   - Strategy: {l.fix_strategy}")
            print(f"   - Domain: {l.domain_pattern}")
        else:
            custom_logger.error("No lesson learned.")
        session.close()

    print("\n" + "="*60)
    print("🏁 DEMO COMPLETE")

if __name__ == "__main__":
    test_demo_doctor_is_in()
