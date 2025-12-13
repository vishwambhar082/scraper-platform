"""
Prompt Template Manager

YAML-based versioned prompt template system for LLM operations.
Supports template inheritance, variable substitution, and version control.

Author: Scraper Platform Team
Date: 2025-12-13
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from src.common.logging_utils import get_logger

log = get_logger("prompt_manager")


@dataclass
class PromptTemplate:
    """Prompt template with metadata."""

    name: str
    version: str
    template: str
    description: str = ""
    variables: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = "system"
    parent: Optional[str] = None  # Parent template for inheritance

    def render(self, **variables: Any) -> str:
        """Render template with variables.

        Args:
            **variables: Template variables

        Returns:
            Rendered template string

        Raises:
            KeyError if required variable is missing
        """
        # Check for missing variables
        missing = set(self.variables) - set(variables.keys())
        if missing:
            raise KeyError(f"Missing required variables: {missing}")

        # Render template
        try:
            return self.template.format(**variables)
        except KeyError as e:
            raise KeyError(f"Undefined variable in template: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "template": self.template,
            "description": self.description,
            "variables": self.variables,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "author": self.author,
            "parent": self.parent,
        }


class PromptTemplateManager:
    """
    Manage versioned prompt templates.

    Features:
    - YAML-based template storage
    - Version control
    - Template inheritance
    - Variable validation
    - Template caching
    - Git-friendly format
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """Initialize prompt template manager.

        Args:
            templates_dir: Directory containing template YAML files
                          (default: ./config/prompts)
        """
        self.templates_dir = Path(templates_dir or "./config/prompts")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        self._templates: Dict[str, Dict[str, PromptTemplate]] = {}
        self._load_templates()

        log.info(f"Initialized prompt manager: {len(self._templates)} templates loaded")

    def _load_templates(self) -> None:
        """Load all templates from YAML files."""
        for yaml_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data:
                    continue

                # Load templates from file
                for template_data in data.get("templates", []):
                    template = PromptTemplate(
                        name=template_data["name"],
                        version=template_data["version"],
                        template=template_data["template"],
                        description=template_data.get("description", ""),
                        variables=template_data.get("variables", []),
                        tags=template_data.get("tags", []),
                        author=template_data.get("author", "system"),
                        parent=template_data.get("parent"),
                    )

                    # Store template
                    if template.name not in self._templates:
                        self._templates[template.name] = {}

                    self._templates[template.name][template.version] = template

                log.debug(f"Loaded templates from {yaml_file.name}")

            except Exception as e:
                log.error(f"Failed to load templates from {yaml_file}: {e}")

    def get_template(
        self, name: str, version: Optional[str] = None
    ) -> Optional[PromptTemplate]:
        """Get template by name and version.

        Args:
            name: Template name
            version: Template version (default: latest)

        Returns:
            PromptTemplate or None if not found
        """
        if name not in self._templates:
            return None

        versions = self._templates[name]

        if version:
            return versions.get(version)

        # Return latest version
        if versions:
            latest_version = max(versions.keys())
            return versions[latest_version]

        return None

    def get_template_versions(self, name: str) -> List[str]:
        """Get all versions of a template.

        Args:
            name: Template name

        Returns:
            List of version strings
        """
        if name not in self._templates:
            return []

        return sorted(self._templates[name].keys())

    def render(
        self, name: str, version: Optional[str] = None, **variables: Any
    ) -> str:
        """Render template with variables.

        Args:
            name: Template name
            version: Template version (optional, uses latest)
            **variables: Template variables

        Returns:
            Rendered template string

        Raises:
            ValueError if template not found
            KeyError if required variable missing
        """
        template = self.get_template(name, version)
        if not template:
            raise ValueError(f"Template not found: {name} (version={version})")

        # Handle inheritance
        if template.parent:
            parent_template = self.get_template(template.parent)
            if parent_template:
                # Merge parent template content
                base_content = parent_template.render(**variables)
                # Allow child to reference parent content
                variables["_parent"] = base_content

        return template.render(**variables)

    def create_template(
        self,
        name: str,
        version: str,
        template: str,
        variables: List[str],
        description: str = "",
        tags: Optional[List[str]] = None,
        author: str = "system",
        parent: Optional[str] = None,
        save: bool = True,
    ) -> PromptTemplate:
        """Create and register new template.

        Args:
            name: Template name
            version: Template version (semantic versioning recommended)
            template: Template string with {variable} placeholders
            variables: List of required variables
            description: Template description
            tags: Template tags for categorization
            author: Template author
            parent: Parent template name for inheritance
            save: Whether to save to disk immediately

        Returns:
            Created PromptTemplate
        """
        prompt_template = PromptTemplate(
            name=name,
            version=version,
            template=template,
            description=description,
            variables=variables,
            tags=tags or [],
            author=author,
            parent=parent,
        )

        # Register template
        if name not in self._templates:
            self._templates[name] = {}

        self._templates[name][version] = prompt_template

        # Save to disk if requested
        if save:
            self._save_template(prompt_template)

        log.info(f"Created template: {name} v{version}")

        return prompt_template

    def _save_template(self, template: PromptTemplate) -> None:
        """Save template to YAML file.

        Args:
            template: Template to save
        """
        # Determine file path
        file_path = self.templates_dir / f"{template.name}.yaml"

        # Load existing data or create new
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {"templates": []}

        # Update or add template
        templates = data.get("templates", [])
        existing_idx = None

        for idx, t in enumerate(templates):
            if t["name"] == template.name and t["version"] == template.version:
                existing_idx = idx
                break

        template_dict = {
            "name": template.name,
            "version": template.version,
            "template": template.template,
            "description": template.description,
            "variables": template.variables,
            "tags": template.tags,
            "author": template.author,
        }

        if template.parent:
            template_dict["parent"] = template.parent

        if existing_idx is not None:
            templates[existing_idx] = template_dict
        else:
            templates.append(template_dict)

        data["templates"] = templates

        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        log.debug(f"Saved template to {file_path}")

    def list_templates(
        self, tag: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all templates, optionally filtered by tag.

        Args:
            tag: Optional tag to filter by

        Returns:
            List of template dictionaries
        """
        results = []

        for name, versions in self._templates.items():
            for version, template in versions.items():
                if tag and tag not in template.tags:
                    continue

                results.append({
                    "name": name,
                    "version": version,
                    "description": template.description,
                    "variables": template.variables,
                    "tags": template.tags,
                })

        return results

    def reload(self) -> None:
        """Reload all templates from disk."""
        self._templates.clear()
        self._load_templates()
        log.info("Reloaded all templates")


# Global prompt manager singleton
_prompt_manager: Optional[PromptTemplateManager] = None


def get_prompt_manager(templates_dir: Optional[str] = None) -> PromptTemplateManager:
    """Get global prompt template manager.

    Args:
        templates_dir: Optional templates directory (only used on first call)

    Returns:
        PromptTemplateManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptTemplateManager(templates_dir)
    return _prompt_manager


# Create default templates
def create_default_templates():
    """Create default prompt templates."""
    manager = get_prompt_manager()

    # Selector repair template
    manager.create_template(
        name="selector_repair",
        version="1.0.0",
        template="""You are an expert web scraper. The following CSS selector is broken:

Selector: {selector}
Error: {error}
HTML Context:
{html_context}

Please provide a fixed CSS selector that will work. Return ONLY the selector, no explanation.""",
        variables=["selector", "error", "html_context"],
        description="Repair broken CSS selectors using LLM",
        tags=["repair", "selector"],
    )

    # Data normalization template
    manager.create_template(
        name="data_normalization",
        version="1.0.0",
        template="""Normalize the following data field to a standard format:

Field: {field_name}
Raw Value: {raw_value}
Expected Format: {expected_format}

Return ONLY the normalized value, no explanation.""",
        variables=["field_name", "raw_value", "expected_format"],
        description="Normalize data fields to standard formats",
        tags=["normalization", "data"],
    )

    # QC validation template
    manager.create_template(
        name="qc_validation",
        version="1.0.0",
        template="""Review the following scraped record for quality issues:

{record}

Check for:
- Missing required fields
- Invalid data formats
- Suspicious values

Return JSON with: {{"valid": true/false, "issues": ["issue1", "issue2"]}}""",
        variables=["record"],
        description="Validate scraped records for quality",
        tags=["qc", "validation"],
    )

    log.info("Created default prompt templates")


# Initialize default templates on import
try:
    create_default_templates()
except Exception as e:
    log.warning(f"Failed to create default templates: {e}")
