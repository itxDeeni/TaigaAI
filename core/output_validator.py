import re

class OutputValidator:
    @staticmethod
    def validate_review(content):
        """
        Validates output contract for taiga-review using robust regular expressions.
        Each block must conform to:
        [AI-TOOL: taiga-review]
        Severity: [Low|Medium|High]
        Issue: ...
        Evidence: ...
        Fix: ...
        """
        if not re.search(r"\[AI-TOOL:\s*taiga-review\]", content, re.IGNORECASE):
            return False, "Missing [AI-TOOL: taiga-review] tag"
            
        # Find all blocks (split by the tool tag)
        blocks = re.split(r"\[AI-TOOL:\s*taiga-review\]", content, flags=re.IGNORECASE)[1:]
        
        for idx, block in enumerate(blocks, 1):
            # Check fields are present in sequential order with content in each
            severity_match = re.search(r"^\s*Severity:\s*(Low|Medium|High)\b", block, re.IGNORECASE | re.MULTILINE)
            if not severity_match:
                return False, f"Block {idx}: Missing or invalid 'Severity:' (must be Low, Medium, or High)"
                
            if not re.search(r"^\s*Issue:\s*\S+", block, re.IGNORECASE | re.MULTILINE):
                return False, f"Block {idx}: Missing or empty 'Issue:'"
                
            if not re.search(r"^\s*Evidence:\s*\S+", block, re.IGNORECASE | re.MULTILINE):
                return False, f"Block {idx}: Missing or empty 'Evidence:'"
                
            if not re.search(r"^\s*Fix:\s*\S+", block, re.IGNORECASE | re.MULTILINE):
                return False, f"Block {idx}: Missing or empty 'Fix:'"
                
        return True, ""

    @staticmethod
    def validate_security(content):
        """
        Validates output contract for taiga-sec using robust regular expressions.
        Each block must conform to:
        [AI-TOOL: taiga-sec]
        Severity: [Low|Medium|High|Critical]
        Vulnerability: ...
        Location: ...
        Evidence: ...
        Remediation: ...
        """
        if not re.search(r"\[AI-TOOL:\s*taiga-sec\]", content, re.IGNORECASE):
            return False, "Missing [AI-TOOL: taiga-sec] tag"
            
        blocks = re.split(r"\[AI-TOOL:\s*taiga-sec\]", content, flags=re.IGNORECASE)[1:]
        
        for idx, block in enumerate(blocks, 1):
            severity_match = re.search(r"^\s*Severity:\s*(Low|Medium|High|Critical)\b", block, re.IGNORECASE | re.MULTILINE)
            if not severity_match:
                return False, f"Block {idx}: Missing or invalid 'Severity:' (must be Low, Medium, High, or Critical)"
                
            if not re.search(r"^\s*Vulnerability:\s*\S+", block, re.IGNORECASE | re.MULTILINE):
                return False, f"Block {idx}: Missing or empty 'Vulnerability:'"
                
            if not re.search(r"^\s*Location:\s*\S+", block, re.IGNORECASE | re.MULTILINE):
                return False, f"Block {idx}: Missing or empty 'Location:'"
                
            if not re.search(r"^\s*Evidence:\s*\S+", block, re.IGNORECASE | re.MULTILINE):
                return False, f"Block {idx}: Missing or empty 'Evidence:'"
                
            if not re.search(r"^\s*Remediation:\s*\S+", block, re.IGNORECASE | re.MULTILINE):
                return False, f"Block {idx}: Missing or empty 'Remediation:'"
                
        return True, ""

    @classmethod
    def validate(cls, tool_name, content):
        """Router for format validations."""
        if tool_name == "taiga-review":
            return cls.validate_review(content)
        elif tool_name == "taiga-sec":
            return cls.validate_security(content)
        return True, "" # Other tools (like git or core ai) don't enforce rigid schemas

