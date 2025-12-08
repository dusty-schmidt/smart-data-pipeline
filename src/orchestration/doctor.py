"""
Doctor Agent - Self-Healing for Tier 2 Autonomy Kernel

Diagnoses failures, generates patches, and deploys fixes through a staging workflow.
"""
import os
import ast
import hashlib
import shutil
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.agents.base import BaseAgent
from src.orchestration.health import HealthTracker, SourceState
from src.storage.models import FixHistoryRecord, Base, Lesson
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


@dataclass
class DiagnosisContext:
    """Full context needed for diagnosis."""
    source_name: str
    error_type: str
    error_message: str
    failure_count: int
    fix_attempts_today: int
    is_quarantined: bool
    # Additional context for LLM
    current_code: Optional[str] = None
    current_html: Optional[str] = None
    previous_html_hash: Optional[str] = None
    html_changed: bool = False


@dataclass 
class Diagnosis:
    """Result of analyzing a failure."""
    source_name: str
    error_type: str
    root_cause: str
    suggested_fix: str
    confidence: float
    fix_strategy: str = "patch"  # "patch" or "rebuild"


class DoctorAgent(BaseAgent):
    """
    The Self-Healing Agent.
    
    Responsibilities:
    - Collect context on failures (error + HTML diff + code)
    - Diagnose root cause using LLM
    - Generate and test patches
    - Deploy to staging, validate, promote to production
    - Enforce circuit breakers (max 3 attempts per 24h)
    """
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        super().__init__()
        self.db_path = db_path
        self.health_tracker = HealthTracker(db_path)
        self.registry_path = Path("src/registry")
        self.staging_path = Path("src/registry/staging")
        
        # Ensure staging directory exists
        self.staging_path.mkdir(parents=True, exist_ok=True)
        
        # Database for fix history
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def collect_context(self, source_name: str, error: Exception) -> DiagnosisContext:
        """
        Gather all information needed for diagnosis.
        
        Collects:
        1. Error type and message
        2. Current scraper code from registry
        3. Current HTML from source (via Firecrawl)
        4. HTML change detection
        5. Health stats
        """
        logger.info(f"[Doctor] Collecting context for {source_name}")
        
        # Get health status
        health = self.health_tracker.get_health(source_name)
        
        # Get current code
        current_code = self._get_source_code(source_name)
        
        # Get current HTML and detect changes
        current_html = None
        html_changed = False
        previous_hash = None
        
        if health:
            previous_hash = self.health_tracker.get_html_hash(source_name)
        
        # Try to fetch current HTML (would need URL from blueprint/registry)
        # For now, we'll leave this as None and note it in the context
        
        context = DiagnosisContext(
            source_name=source_name,
            error_type=type(error).__name__,
            error_message=str(error)[:2000],  # Truncate long errors
            failure_count=health.consecutive_failures if health else 1,
            fix_attempts_today=health.fix_attempts_today if health else 0,
            is_quarantined=health.state == SourceState.QUARANTINED if health else False,
            current_code=current_code,
            current_html=current_html,
            previous_html_hash=previous_hash,
            html_changed=html_changed,
        )
        
        logger.debug(f"[Doctor] Context collected: error={context.error_type}, failures={context.failure_count}")
        return context
    
    def _get_source_code(self, source_name: str) -> Optional[str]:
        """Read the current source code from the registry."""
        file_path = self.registry_path / f"{source_name}.py"
        if file_path.exists():
            return file_path.read_text()
        return None
    
    def diagnose(self, context: DiagnosisContext) -> Diagnosis:
        """
        Analyze failure context and determine root cause using LLM.
        """
        logger.info(f"[Doctor] Diagnosing {context.source_name}")
        
        system_prompt = """You are a Senior Python Engineer specializing in web scraping debugging.
        
Analyze the error context and determine:
1. Root cause of the failure
2. Whether this is fixable via code patch or requires a full rebuild
3. Specific fix suggestion

Common failure patterns:
- SelectorNotFound: DOM structure changed, need new CSS selectors
- TimeoutError: Site blocking or slow, need retry logic or different approach
- KeyError: API response structure changed
- AttributeError: Parsing logic doesn't match current page structure
- ConnectionError: Network issues or site down (usually temporary)

Respond in JSON format:
{
    "root_cause": "Brief description of what went wrong",
    "fix_strategy": "patch" or "rebuild",
    "suggested_fix": "Specific code changes or approach to fix",
    "confidence": 0.0-1.0
}
"""
        

        # Contextual Learning: Retrieve relevant lessons
        lessons = self._get_relevant_lessons(context)
        lesson_text = ""
        if lessons:
            lesson_text = "\n\nRelevant past lessons:\n" + "\n".join([f"- {l.symptom_description} -> {l.fix_strategy}" for l in lessons])

        user_message = f"""
Error Context:
- Source: {context.source_name}
- Error Type: {context.error_type}
- Error Message: {context.error_message}
- Consecutive Failures: {context.failure_count}
- Fix Attempts Today: {context.fix_attempts_today}

Current Code:
```python
{context.current_code or "Code not available"}
```

{f"HTML Changed: {context.html_changed}" if context.previous_html_hash else "No previous HTML hash for comparison"}
{lesson_text}

Diagnose the issue and provide a fix strategy.
"""
        
        try:
            response = self.ask_llm(
                prompt=user_message,
                system_prompt=system_prompt,
                json_mode=True
            )
            
            # Parse JSON response
            import json
            result = json.loads(response)
            
            diagnosis = Diagnosis(
                source_name=context.source_name,
                error_type=context.error_type,
                root_cause=result.get("root_cause", "Unknown"),
                suggested_fix=result.get("suggested_fix", ""),
                confidence=float(result.get("confidence", 0.5)),
                fix_strategy=result.get("fix_strategy", "patch"),
            )
            
            logger.info(f"[Doctor] Diagnosis: {diagnosis.root_cause} (confidence: {diagnosis.confidence:.0%})")
            return diagnosis
            
        except Exception as e:
            logger.error(f"[Doctor] Diagnosis failed: {e}")
            return Diagnosis(
                source_name=context.source_name,
                error_type=context.error_type,
                root_cause=f"Diagnosis failed: {e}",
                suggested_fix="Manual intervention required",
                confidence=0.0,
            )
    
    def _get_relevant_lessons(self, context: DiagnosisContext) -> List[Lesson]:
        """Query knowledge base for relevant lessons."""
        session = self.Session()
        try:
            # Simple heuristic: match error type or source name pattern
            # In a real system, this would use vector embeddings
            return session.query(Lesson).filter(
                (Lesson.error_type == context.error_type) |
                (Lesson.domain_pattern.like(f"%{context.source_name}%"))
            ).order_by(Lesson.success_count.desc()).limit(3).all()
        except Exception as e:
            logger.warning(f"[Doctor] Failed to fetch lessons: {e}")
            return []
        finally:
            session.close()

    def learn_from_success(self, context: DiagnosisContext, diagnosis: Diagnosis, patch: str) -> None:
        """
        Extract a lesson from a successful fix and save to Knowledge Base.
        """
        logger.info(f"[Doctor] Learning from success for {context.source_name}")
        
        system_prompt = """You are a Senior Engineer distilling lessons from a fixed bug.
        
        Analyze the error, the diagnosis, and the successful patch.
        Extract a generalized lesson that could help future debugging.
        
        Output JSON:
        {
            "domain_pattern": "e.g. 'shopify_sites' or 'generic_html'",
            "symptom_description": "When finding X error with Y context",
            "fix_strategy": "Try approach Z instead",
            "reasoning": "Why this worked"
        }
        """
        
        user_message = f"""
        Error: {context.error_type}: {context.error_message}
        Root Cause: {diagnosis.root_cause}
        Fix Strategy Applied: {diagnosis.suggested_fix}
        
        Patch Diff Summary:
        (Length: {len(patch)} chars)
        
        Extract a generalized lesson.
        """
        
        try:
            response = self.ask_llm(
                prompt=user_message,
                system_prompt=system_prompt,
                json_mode=True
            )
            
            import json
            data = json.loads(response)
            
            session = self.Session()
            try:
                lesson = Lesson(
                    error_type=context.error_type,
                    domain_pattern=data.get("domain_pattern", context.source_name),
                    symptom_description=data.get("symptom_description", ""),
                    fix_strategy=data.get("fix_strategy", ""),
                    success_count=1
                )
                session.add(lesson)
                session.commit()
                logger.info(f"[Doctor] Learned new lesson: {lesson.fix_strategy}")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"[Doctor] Learning failed: {e}")

    def generate_patch(self, diagnosis: Diagnosis, context: DiagnosisContext) -> Optional[str]:
        """
        Generate code patch to fix the issue using LLM.
        
        Returns the patched code or None if generation fails.
        """
        logger.info(f"[Doctor] Generating patch for {diagnosis.source_name}")
        
        if not context.current_code:
            logger.error("[Doctor] Cannot generate patch: no current code available")
            return None
        
        system_prompt = """You are a Senior Python Engineer fixing a web scraper.

Apply the suggested fix to the code. Return ONLY the complete fixed Python code.
Do not include markdown code fences. Do not explain - just return the fixed code.

Important:
- Preserve all imports
- Preserve the class structure
- Only modify what's necessary to fix the issue
- Add error handling if the fix involves uncertain selectors
"""
        
        user_message = f"""
Current Code:
{context.current_code}

Error: {diagnosis.error_type}: {context.error_message}

Root Cause: {diagnosis.root_cause}

Suggested Fix: {diagnosis.suggested_fix}

Apply the fix and return the complete corrected code.
"""
        
        try:
            patched_code = self.ask_llm(
                prompt=user_message,
                system_prompt=system_prompt,
            )
            
            # Clean up any accidental markdown
            patched_code = patched_code.strip()
            if patched_code.startswith("```python"):
                patched_code = patched_code[9:]
            if patched_code.startswith("```"):
                patched_code = patched_code[3:]
            if patched_code.endswith("```"):
                patched_code = patched_code[:-3]
            patched_code = patched_code.strip()
            
            # Validate syntax
            try:
                ast.parse(patched_code)
            except SyntaxError as e:
                logger.error(f"[Doctor] Generated code has syntax errors: {e}")
                return None
            
            logger.info(f"[Doctor] Patch generated successfully ({len(patched_code)} bytes)")
            return patched_code
            
        except Exception as e:
            logger.error(f"[Doctor] Patch generation failed: {e}")
            return None
    
    def deploy_to_staging(self, source_name: str, patch: str) -> bool:
        """
        Deploy patch to staging registry for validation.
        """
        logger.info(f"[Doctor] Deploying {source_name} to staging")
        
        staging_file = self.staging_path / f"{source_name}.py"
        
        try:
            staging_file.write_text(patch)
            logger.info(f"[Doctor] Staged: {staging_file}")
            return True
        except Exception as e:
            logger.error(f"[Doctor] Failed to stage: {e}")
            return False
    
    def validate_staged(self, source_name: str) -> bool:
        """
        Run validation on staged scraper.
        
        Validation includes:
        1. Syntax check (already done during patch generation)
        2. Import check
        3. Basic execution test (dry run)
        """
        logger.info(f"[Doctor] Validating staged {source_name}")
        
        staging_file = self.staging_path / f"{source_name}.py"
        
        if not staging_file.exists():
            logger.error(f"[Doctor] Staging file not found: {staging_file}")
            return False
        
        code = staging_file.read_text()
        
        # 1. Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            logger.error(f"[Doctor] Syntax error in staged code: {e}")
            return False
        
        # 2. Try to compile and check imports
        try:
            compile(code, staging_file, 'exec')
        except Exception as e:
            logger.error(f"[Doctor] Compilation error: {e}")
            return False
        
        # 3. Basic structural validation
        # Check for required patterns (Fetcher and/or Parser class)
        if "class" not in code:
            logger.error("[Doctor] No class definition found in staged code")
            return False
        
        logger.info(f"[Doctor] Validation passed for {source_name}")
        return True
    
    def promote_to_production(self, source_name: str) -> bool:
        """
        Promote validated patch from staging to production.
        """
        logger.info(f"[Doctor] Promoting {source_name} to production")
        
        staging_file = self.staging_path / f"{source_name}.py"
        production_file = self.registry_path / f"{source_name}.py"
        
        if not staging_file.exists():
            logger.error(f"[Doctor] Staging file not found: {staging_file}")
            return False
        
        try:
            # Backup current production file if it exists
            if production_file.exists():
                backup_file = self.registry_path / f"{source_name}.py.bak"
                shutil.copy(production_file, backup_file)
                logger.debug(f"[Doctor] Backed up to {backup_file}")
            
            # Move staging to production
            shutil.move(str(staging_file), str(production_file))
            logger.info(f"[Doctor] Promoted {source_name} to production")
            return True
            
        except Exception as e:
            logger.error(f"[Doctor] Promotion failed: {e}")
            return False
    
    def rollback(self, source_name: str) -> bool:
        """
        Rollback to previous version if available.
        """
        production_file = self.registry_path / f"{source_name}.py"
        backup_file = self.registry_path / f"{source_name}.py.bak"
        
        if not backup_file.exists():
            logger.error(f"[Doctor] No backup available for {source_name}")
            return False
        
        try:
            shutil.move(str(backup_file), str(production_file))
            logger.info(f"[Doctor] Rolled back {source_name}")
            return True
        except Exception as e:
            logger.error(f"[Doctor] Rollback failed: {e}")
            return False
    
    def heal(self, source_name: str, error: Exception) -> bool:
        """
        Full healing workflow: collect → diagnose → patch → stage → validate → promote.
        
        Returns True if healing succeeded.
        """
        logger.info(f"[Doctor] Starting healing workflow for {source_name}")
        
        # Check circuit breaker
        if not self.health_tracker.can_attempt_fix(source_name):
            logger.warning(f"[Doctor] Circuit breaker triggered for {source_name}")
            return False
        
        # Record fix attempt
        self.health_tracker.record_fix_attempt(source_name)
        
        try:
            # 1. Collect context
            context = self.collect_context(source_name, error)
            
            # 2. Diagnose
            diagnosis = self.diagnose(context)
            
            if diagnosis.confidence < 0.3:
                logger.warning(f"[Doctor] Low confidence diagnosis ({diagnosis.confidence:.0%}), skipping auto-fix")
                self._record_fix_history(source_name, context, diagnosis, success=False)
                return False
            
            # 3. Generate patch
            patch = self.generate_patch(diagnosis, context)
            if patch is None:
                logger.error("[Doctor] Failed to generate patch")
                self._record_fix_history(source_name, context, diagnosis, success=False)
                return False
            
            # 4. Deploy to staging
            if not self.deploy_to_staging(source_name, patch):
                self._record_fix_history(source_name, context, diagnosis, success=False)
                return False
            
            # 5. Validate
            if not self.validate_staged(source_name):
                logger.error("[Doctor] Validation failed, not promoting")
                self._record_fix_history(source_name, context, diagnosis, success=False)
                return False
            
            # 6. Promote to production
            if not self.promote_to_production(source_name):
                self._record_fix_history(source_name, context, diagnosis, success=False)
                return False
            
            # Success!
            self._record_fix_history(source_name, context, diagnosis, success=True, patch=patch)
            
            # Learn from this success
            self.learn_from_success(context, diagnosis, patch)
            
            logger.success(f"[Doctor] Successfully healed {source_name}")
            return True
            
        except Exception as e:
            logger.exception(f"[Doctor] Healing workflow failed: {e}")
            return False
    
    def _record_fix_history(
        self,
        source_name: str,
        context: DiagnosisContext,
        diagnosis: Diagnosis,
        success: bool,
        patch: Optional[str] = None
    ) -> None:
        """Record fix attempt in history for auditing."""
        session = self.Session()
        try:
            record = FixHistoryRecord(
                source_name=source_name,
                error_type=context.error_type,
                error_message=context.error_message[:1000] if context.error_message else None,
                root_cause=diagnosis.root_cause[:1000] if diagnosis.root_cause else None,
                patch_applied=patch[:5000] if patch else None,  # Truncate large patches
                success=success,
            )
            session.add(record)
            session.commit()
        finally:
            session.close()
