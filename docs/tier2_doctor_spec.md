# Doctor Agent: Diagnosis Logic Specification

## Overview
The Doctor Agent is the **highest-risk component** in Tier 2. Poor implementation leads to infinite cost loops. This document specifies the diagnosis logic with proper safeguards.

## Core Principle: Quarantine Before Promotion

```
Error Detected → Diagnosis → Patch → Staging → Validation → Production
                                         ↓ (fail)
                                    Quarantine (max 3 attempts)
```

## The Context Package

### What the Doctor Needs Before Asking LLM

The Doctor must collect a **complete context package** before generating a fix:

```python
@dataclass
class DiagnosisContext:
    # Source Identity
    source_name: str
    blueprint: DataBlueprint
    current_code: str  # The failing fetcher/parser
    
    # Error Information
    error_type: str  # "HTTP_ERROR", "PARSE_ERROR", "SCHEMA_MISMATCH"
    error_message: str
    error_traceback: str
    failure_count: int  # How many times has this failed?
    last_success_at: Optional[datetime]  # When did it last work?
    
    # The Critical Diff
    original_html: str  # HTML from when blueprint was created
    current_html: str   # HTML from failed attempt
    html_diff: str      # Computed diff (structural changes)
    
    # Data Quality
    expected_schema: Dict[str, str]  # From blueprint
    actual_output: Optional[Dict]    # What the scraper returned (if any)
    
    # Circuit Breaker State
    fix_attempts_today: int  # How many times have we tried to fix this?
    is_quarantined: bool
```

### Context Collection Flow

```python
class DoctorAgent:
    def collect_context(self, source_name: str, error: Exception) -> DiagnosisContext:
        """
        Gather all information needed for diagnosis.
        This is the MOST IMPORTANT method - garbage in, garbage out.
        """
        # 1. Load source metadata
        blueprint = self._load_blueprint(source_name)
        current_code = self._load_current_code(source_name)
        
        # 2. Fetch current page state
        current_html = self._fetch_current_page(blueprint.base_url)
        
        # 3. Load historical HTML (from blueprint creation)
        original_html = self._load_original_html(source_name)
        
        # 4. Compute structural diff
        html_diff = self._compute_html_diff(original_html, current_html)
        
        # 5. Check circuit breaker state
        fix_attempts = self._count_fix_attempts(source_name, hours=24)
        
        # 6. Load expected schema
        expected_schema = blueprint.fields
        
        # 7. Try to get actual output (if parse error, might be None)
        actual_output = self._safe_execute_scraper(source_name)
        
        return DiagnosisContext(
            source_name=source_name,
            blueprint=blueprint,
            current_code=current_code,
            error_type=self._classify_error(error),
            error_message=str(error),
            error_traceback=traceback.format_exc(),
            failure_count=self._get_failure_count(source_name),
            last_success_at=self._get_last_success(source_name),
            original_html=original_html,
            current_html=current_html,
            html_diff=html_diff,
            expected_schema=expected_schema,
            actual_output=actual_output,
            fix_attempts_today=fix_attempts,
            is_quarantined=fix_attempts >= 3
        )
```

## Error Classification

### Error Types (Priority Order)

1. **HTTP_ERROR** (404, 403, 500)
   - **Diagnosis:** URL changed or site down
   - **Fix Strategy:** Try `firecrawl_map` to find new URL pattern
   - **Fallback:** Mark as DEAD if domain is gone

2. **PARSE_ERROR** (selector returns None/empty)
   - **Diagnosis:** DOM structure changed
   - **Fix Strategy:** Re-analyze HTML with Scout, generate new selectors
   - **Validation:** Must match expected schema

3. **SCHEMA_MISMATCH** (data shape changed)
   - **Diagnosis:** Site added/removed fields
   - **Fix Strategy:** Update blueprint, regenerate parser
   - **Validation:** Ensure critical fields still present

4. **TIMEOUT** (page too slow)
   - **Diagnosis:** Site performance issue
   - **Fix Strategy:** Increase `waitFor` in Firecrawl
   - **Fallback:** Retry with exponential backoff

5. **RATE_LIMIT** (429 Too Many Requests)
   - **Diagnosis:** Hitting API limits
   - **Fix Strategy:** Add delay, use batch operations
   - **Fallback:** Reduce scrape frequency

## The HTML Diff Algorithm

### Why Diff Matters
The LLM needs to see **what changed** in the DOM structure, not just "it broke."

```python
def _compute_html_diff(self, original: str, current: str) -> str:
    """
    Compute a structural diff of HTML.
    Focus on changes to data containers, not styling.
    """
    from bs4 import BeautifulSoup
    import difflib
    
    # Parse both versions
    orig_soup = BeautifulSoup(original, 'html.parser')
    curr_soup = BeautifulSoup(current, 'html.parser')
    
    # Remove noise (scripts, styles, comments)
    for soup in [orig_soup, curr_soup]:
        for tag in soup(['script', 'style', 'svg', 'noscript']):
            tag.decompose()
    
    # Get simplified structure (tag names + classes only)
    orig_structure = self._extract_structure(orig_soup)
    curr_structure = self._extract_structure(curr_soup)
    
    # Compute diff
    diff = difflib.unified_diff(
        orig_structure.splitlines(),
        curr_structure.splitlines(),
        lineterm='',
        fromfile='original',
        tofile='current'
    )
    
    return '\n'.join(diff)

def _extract_structure(self, soup) -> str:
    """
    Extract a simplified DOM structure for diffing.
    Example: div.container > table.stats > tr > td.score
    """
    lines = []
    for element in soup.find_all():
        path = self._get_css_path(element)
        if element.string and element.string.strip():
            lines.append(f"{path}: {element.string.strip()[:50]}")
        else:
            lines.append(path)
    return '\n'.join(lines)
```

## Circuit Breaker Logic

### The 3-Strike Rule

```python
class CircuitBreaker:
    MAX_ATTEMPTS_PER_DAY = 3
    QUARANTINE_DURATION_HOURS = 24
    
    def check_before_fix(self, source_name: str) -> CircuitBreakerState:
        """
        Check if we should attempt a fix or quarantine the source.
        """
        attempts_today = self._count_attempts(source_name, hours=24)
        
        if attempts_today >= self.MAX_ATTEMPTS_PER_DAY:
            return CircuitBreakerState(
                can_attempt=False,
                reason="MAX_ATTEMPTS_REACHED",
                action="QUARANTINE",
                alert_human=True
            )
        
        # Check if source is permanently dead (domain gone)
        if self._is_domain_dead(source_name):
            return CircuitBreakerState(
                can_attempt=False,
                reason="DOMAIN_DEAD",
                action="MARK_DEAD",
                alert_human=True
            )
        
        return CircuitBreakerState(
            can_attempt=True,
            attempts_remaining=self.MAX_ATTEMPTS_PER_DAY - attempts_today
        )
```

## The Staging Registry

### Two-Phase Deployment

```python
class DeploymentManager:
    def deploy_patch(self, source_name: str, patched_code: str) -> DeploymentResult:
        """
        Deploy to staging, validate, then promote to production.
        """
        # 1. Deploy to staging
        staging_path = f"src/registry/staging/{source_name}.py"
        self._write_code(staging_path, patched_code)
        
        # 2. Run validation tests
        validation = self._validate_staged_scraper(source_name)
        
        if validation.passed:
            # 3. Promote to production
            prod_path = f"src/registry/{source_name}.py"
            self._write_code(prod_path, patched_code)
            
            # 4. Archive old version
            self._archive_version(source_name, old_code)
            
            return DeploymentResult(
                success=True,
                deployed_to="PRODUCTION",
                validation_score=validation.score
            )
        else:
            # Keep in staging, mark as failed attempt
            return DeploymentResult(
                success=False,
                deployed_to="STAGING_ONLY",
                validation_errors=validation.errors,
                action="QUARANTINE" if validation.critical else "RETRY"
            )
```

## The Baby Validator

### Schema Signature Validation

```python
class BabyValidator:
    """
    Minimal validation for Tier 2.
    Full Validator comes in Tier 3.
    """
    
    def validate_scraper_output(
        self, 
        output: Dict, 
        expected_schema: Dict[str, str]
    ) -> ValidationResult:
        """
        Check if scraper output matches expected schema.
        """
        errors = []
        
        # 1. Check required fields present
        for field_name in expected_schema.keys():
            if field_name not in output:
                errors.append(f"Missing field: {field_name}")
        
        # 2. Check no fields are None/empty
        for field_name, value in output.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Empty field: {field_name}")
        
        # 3. Basic type checking (all values should be strings for now)
        for field_name, value in output.items():
            if not isinstance(value, (str, int, float)):
                errors.append(f"Invalid type for {field_name}: {type(value)}")
        
        # 4. Sanity check: Did we get ANY data?
        if len(output) == 0:
            errors.append("No data returned")
        
        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            score=1.0 - (len(errors) / max(len(expected_schema), 1)),
            critical=any("Missing field" in e or "No data" in e for e in errors)
        )
```

## LLM Prompt Template

### The Diagnosis Prompt

```python
def _build_diagnosis_prompt(self, context: DiagnosisContext) -> str:
    """
    Build the LLM prompt with full context.
    """
    return f"""
You are a web scraping expert. A scraper has failed and needs to be fixed.

## Source Information
- Name: {context.source_name}
- URL: {context.blueprint.base_url}
- Last Success: {context.last_success_at or "Never"}
- Failure Count: {context.failure_count}

## Error
Type: {context.error_type}
Message: {context.error_message}

## Expected Data Schema
{json.dumps(context.expected_schema, indent=2)}

## What Changed (HTML Diff)
The website structure has changed. Here is the diff:

```diff
{context.html_diff[:2000]}  # Truncate to save tokens
```

## Current Scraper Code
```python
{context.current_code}
```

## Task
Generate a patch for the scraper code that:
1. Fixes the error
2. Returns data matching the expected schema
3. Uses the same code structure (BaseFetcher/BaseParser)

Output ONLY the corrected Python code, no explanations.
"""
```

## Database Schema for Orchestrator State

### Task Queue Table

```sql
CREATE TABLE task_queue (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,  -- 'ADD_SOURCE', 'FIX_SOURCE', 'REFRESH_SOURCE'
    target TEXT NOT NULL,  -- source_name or URL
    state TEXT NOT NULL,  -- 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'QUARANTINED'
    priority INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    context_json TEXT  -- JSON blob of task-specific data
);

CREATE TABLE source_health (
    source_name TEXT PRIMARY KEY,
    state TEXT NOT NULL,  -- 'ACTIVE', 'DEGRADED', 'QUARANTINED', 'DEAD'
    last_success_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    fix_attempts_today INTEGER DEFAULT 0,
    quarantine_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fix_history (
    fix_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    diagnosis_context TEXT,  -- JSON of DiagnosisContext
    patch_generated TEXT,  -- The code patch
    validation_result TEXT,  -- JSON of ValidationResult
    deployed_to TEXT,  -- 'STAGING', 'PRODUCTION', 'FAILED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_name) REFERENCES source_health(source_name)
);
```

## Refined MVP Criteria

### Technical Constraints

1. **Zero-Touch Addition** - URL → working scraper **that persists across system restarts**
   - ✅ Task queue survives reboot
   - ✅ Source health tracked in DB
   - ✅ Orchestrator resumes in-progress tasks

2. **Self-Healing with Safeguards**
   - ✅ Max 3 fix attempts per 24 hours
   - ✅ Staging validation before production
   - ✅ Circuit breaker prevents infinite loops
   - ✅ Human alert on quarantine

3. **Data Quality Assurance**
   - ✅ Schema signature validation
   - ✅ Before/After HTML diff for diagnosis
   - ✅ Validation score tracking

## Implementation Priority

### Phase 1: Foundation (Week 1)
1. Database schema (task_queue, source_health, fix_history)
2. CircuitBreaker class
3. BabyValidator class
4. Staging registry structure

### Phase 2: Doctor Core (Week 2)
1. Context collection (with HTML diff)
2. Error classification
3. LLM diagnosis prompt
4. Patch generation

### Phase 3: Deployment (Week 3)
1. Staging deployment
2. Validation pipeline
3. Production promotion
4. Version archival

### Phase 4: Orchestrator (Week 4)
1. Task queue manager
2. State persistence
3. Resume logic (post-reboot)
4. Alert system

## Success Metrics

- **Fix Success Rate:** 80%+ of fixes pass validation
- **False Positive Rate:** <5% (fixes that pass staging but fail in production)
- **Quarantine Rate:** <10% of sources end up quarantined
- **Recovery Time:** <5 minutes average from error to fix deployed

---

**Next Step:** Implement the database schema and CircuitBreaker class as the foundation.
