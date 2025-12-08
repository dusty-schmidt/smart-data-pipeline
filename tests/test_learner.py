
import unittest
from unittest.mock import MagicMock, patch
import json
from src.agents.doctor import DoctorAgent, DiagnosisContext, Diagnosis, Lesson

class TestLearner(unittest.TestCase):
    def setUp(self):
        # Use in-memory DB for tests
        self.doctor = DoctorAgent(db_path=":memory:")
    
    def test_learn_from_success(self):
        """Verify that learn_from_success creates a Lesson record."""
        context = DiagnosisContext(
            source_name="test_source",
            error_type="SelectorNotFound",
            error_message="Cannot find div.price",
            failure_count=1,
            fix_attempts_today=0,
            is_quarantined=False
        )
        diagnosis = Diagnosis(
            source_name="test_source",
            error_type="SelectorNotFound",
            root_cause="DOM changed",
            suggested_fix="use xpath",
            confidence=0.9
        )
        
        # Mock LLM response
        mock_llm_response = json.dumps({
            "domain_pattern": "test_sites",
            "symptom_description": "When selector fails",
            "fix_strategy": "Try generic xpath",
            "reasoning": "It works"
        })
        
        with patch.object(self.doctor, 'ask_llm', return_value=mock_llm_response):
            self.doctor.learn_from_success(context, diagnosis, "patch_code")
            
        # Verify db
        session = self.doctor.Session()
        lessons = session.query(Lesson).all()
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0].fix_strategy, "Try generic xpath")
        session.close()

    def test_diagnose_uses_lessons(self):
        """Verify that diagnose retrieves lessons."""
        # Seed a lesson
        session = self.doctor.Session()
        lesson = Lesson(
            error_type="SelectorNotFound",
            domain_pattern="test_source",
            symptom_description="Symptom X",
            fix_strategy="Fix Y"
        )
        session.add(lesson)
        session.commit()
        session.close()
        
        context = DiagnosisContext(
            source_name="test_source",
            error_type="SelectorNotFound",
            error_message="msg",
            failure_count=1,
            fix_attempts_today=0,
            is_quarantined=False
        )
        
        # Mock LLM to avoid real call, just return empty valid json
        with patch.object(self.doctor, 'ask_llm', return_value='{}') as mock_ask:
            self.doctor.diagnose(context)
            
            # Check arguments passed to ask_llm
            args, kwargs = mock_ask.call_args
            prompt = kwargs.get('prompt', args[0] if args else "")
            
            # Verify lesson text is in prompt
            self.assertIn("Symptom X -> Fix Y", prompt)

if __name__ == '__main__':
    unittest.main()
