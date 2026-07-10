import os
import re
import logging
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


class EnvVarManager:
    """Replace {{CRD_VAR_NAME}} patterns with environment variable CRD_VAR_NAME."""
    
    # Pattern: {{CRD_VAR_NAME}}
    # Extracts: CRD_VAR_NAME
    # Looks up: Environment variable named CRD_VAR_NAME (with CRD_ prefix)
    PATTERN = re.compile(r'\{\{(CRD_[A-Z_][A-Z0-9_]*)\}\}')
    
    @classmethod
    def substitute(
        cls,
        data: Union[str, Dict, list],
        strict: bool = False
    ) -> Union[str, Dict, list]:
        """
        Replace {{CRD_VAR_NAME}} with environment variable CRD_VAR_NAME.
        
        The FULL variable name (including CRD_ prefix) is used to lookup env vars.
        
        Args:
            data: String, dict, or list containing {{CRD_*}} patterns
            strict: If True, raise error on missing env variables
            
        Returns:
            Data with all {{CRD_*}} replaced with env values
            
        Examples:
            # Environment: CRD_DB_HOST=localhost, CRD_DB_PORT=5432
            
            EnvVarManager.substitute("{{CRD_DB_HOST}}:{{CRD_DB_PORT}}")
            # → "localhost:5432"
            
            # Pattern {{CRD_DB_HOST}} looks for env var CRD_DB_HOST
            
            EnvVarManager.substitute({
                "host": "{{CRD_DB_HOST}}",
                "port": "{{CRD_DB_PORT}}"
            })
            # → {"host": "localhost", "port": "5432"}
        """
        if isinstance(data, str):
            return cls._substitute_string(data, strict=strict)
        elif isinstance(data, dict):
            return {k: cls.substitute(v, strict=strict) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.substitute(item, strict=strict) for item in data]
        else:
            return data
    
    @classmethod
    def _substitute_string(cls, text: str, strict: bool = False) -> str:
        """Replace {{CRD_VAR_NAME}} patterns with env vars."""
        def replace_var(match):
            # Extract CRD_VAR_NAME (full name including CRD_ prefix)
            var_name = match.group(1)
            
            # Look for environment variable with FULL name (e.g., CRD_DB_HOST)
            value = os.getenv(var_name)
            
            if value is None:
                if strict:
                    raise ValueError(
                        f"❌ Environment variable not found: {var_name}\n"
                        f"Pattern: {{{{{{var_name}}}}}})"
                    )
                return match.group(0)  # Keep placeholder unchanged

            return value
        
        return cls.PATTERN.sub(replace_var, text)
    
    @classmethod
    def find_placeholders(cls, data: Union[str, Dict, list]) -> list[str]:
        """Find all {{CRD_*}} placeholders in data."""
        placeholders = set()
        
        if isinstance(data, str):
            matches = cls.PATTERN.findall(data)
            placeholders.update(matches)
        elif isinstance(data, dict):
            for v in data.values():
                placeholders.update(cls.find_placeholders(v))
        elif isinstance(data, list):
            for item in data:
                placeholders.update(cls.find_placeholders(item))
        
        return sorted(list(placeholders))
    
    @classmethod
    def validate_all_present(cls, data: Union[str, Dict, list]) -> tuple[bool, list[str]]:
        """Check if all {{CRD_*}} placeholders have matching env variables."""
        placeholders = cls.find_placeholders(data)
        missing = [var for var in placeholders if os.getenv(var) is None]
        
        return len(missing) == 0, missing
