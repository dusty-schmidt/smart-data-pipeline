import os
import ast
import json
from loguru import logger
from src.agents.base import BaseAgent
from src.agents.models import DataBlueprint


class BuilderAgent(BaseAgent):
    """
    The Construction Agent.
    Role: Takes a 'Blueprint' and writes the actual Python code to `src/registry/`.
    """
    
    def __init__(self):
        super().__init__()
        self.registry_path = "src/registry"

    def build(self, blueprint: DataBlueprint) -> str:
        """
        Generates and saves the Python Code for the given blueprint.
        Returns the path to the created file.
        """
        logger.info(f"Builder is constructing source: {blueprint.source_name}")
        
        # 1. Generate Code using LLM
        code = self._generate_code(blueprint)
        
        # 2. Validate Syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            logger.error(f"Generated code has syntax errors: {e}")
            raise ValueError(f"LLM generated invalid Python code: {e}")

        # 3. Save to Registry
        filename = f"{blueprint.source_name}.py"
        file_path = os.path.join(self.registry_path, filename)
        
        os.makedirs(self.registry_path, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(code)
            
        logger.info(f"Successfully created plugin: {file_path}")
        return file_path

    def _generate_code(self, blueprint: DataBlueprint) -> str:
        if not self.llm.api_key:
            raise ValueError("LLM API Key missing. Cannot generate code.")

        # Context for the LLM
        system_prompt = """
        You are a Senior Python Engineer for a Data Pipeline. 
        Your job is to write a new Source Plugin based on a Data Blueprint.
        
        The plugin must:
        1. Import `BaseFetcher` from `src.ingestion.fetcher`.
        2. Import `BaseParser`, `ParsingResult` from `src.processing.base`.
        3. Define a class `{SourceName}Fetcher(BaseFetcher)`.
        4. Define a class `{SourceName}Parser(BaseParser)`.
        5. Follow the 'Golden Template' style.
        6. Return ONLY the python code. No markdown formatting.
        """
        
        user_message = f"""
        Blueprint:
        {blueprint.model_dump_json(indent=2)}
        
        Task:
        Write a Python file that implements the Fetcher and Parser for this source.
        
        - The Fetcher should use the `base_url`.
        - The Parser should implement `parse(self, message: Dict[str, Any]) -> List[ParsingResult]`.
        - The Parser should extract fields described in 'fields' (using BeautifulSoup logic since the blueprint defines selectors).
        - Assume the input 'message' to the parser is the JSON/Dict returned by the Fetcher (or containing the HTML).
        
        Example Parser Logic if selectors are present:
        soup = BeautifulSoup(message.get("html", ""), "html.parser")
        items = soup.select(root_selector)
        # loop items and extract fields
        """
        
        code = self.llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        # Strip markdown fences if present
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
            
        return code
