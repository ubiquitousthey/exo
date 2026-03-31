"""Template Auditor — static analysis engine for UI design system fidelity.

Scans HTML templates for design system violations without requiring a running
server, browser, or database. Works with any HTML templating system (Jinja2,
Django, ERB, Handlebars, etc.).

Usage:
    from template_auditor import TemplateAuditor

    auditor = TemplateAuditor(
        templates_dir="app/",
        allowed_colors={"#0d1421", "#c09a3a", ...},
        required_classes={"buttons": ["btn-primary", "btn-ghost"], ...},
        standalone_templates={"app/pages/login.html"},
    )
    results = auditor.run_all()
    for violation in results.violations:
        print(violation)

Zero dependencies beyond Python stdlib. Designed to be dropped into any project.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    """A single design system violation."""
    rule: str
    file: str
    line: int | None
    detail: str
    severity: str = "error"  # error | warning

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity}] {self.rule}: {loc} — {self.detail}"


@dataclass
class AuditResults:
    """Aggregated results from all audit rules."""
    violations: list[Violation] = field(default_factory=list)
    templates_scanned: int = 0
    rules_checked: int = 0

    @property
    def passed(self) -> bool:
        return not any(v.severity == "error" for v in self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    def summary(self) -> str:
        return (
            f"Scanned {self.templates_scanned} templates, "
            f"checked {self.rules_checked} rules: "
            f"{self.error_count} errors, {self.warning_count} warnings"
        )


# ---------------------------------------------------------------------------
# Context detection helpers
# ---------------------------------------------------------------------------

HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}\b")


def _line_number(content: str, pos: int) -> int:
    """Get 1-based line number for a character position."""
    return content[:pos].count("\n") + 1


def _is_in_block(content: str, pos: int, open_marker: str, close_marker: str) -> bool:
    """Check if pos is inside a block delimited by open/close markers."""
    last_open = content.rfind(open_marker, 0, pos)
    if last_open == -1:
        return False
    last_close = content.rfind(close_marker, 0, pos)
    return last_close < last_open


def is_in_root_block(content: str, pos: int) -> bool:
    """Check if position is inside a :root { } CSS block."""
    root_start = content.rfind(":root", 0, pos)
    if root_start == -1:
        return False
    brace_start = content.find("{", root_start, pos)
    if brace_start == -1:
        return False
    brace_end = content.find("}", brace_start)
    return brace_end > pos


def is_in_style_block(content: str, pos: int) -> bool:
    """Check if position is inside a <style> block."""
    return _is_in_block(content, pos, "<style", "</style>")


def is_in_script_block(content: str, pos: int) -> bool:
    """Check if position is inside a <script> block."""
    return _is_in_block(content, pos, "<script", "</script>")


def is_in_comment(content: str, pos: int) -> bool:
    """Check if position is inside an HTML or template comment."""
    # HTML comment
    last_comment = content.rfind("<!--", 0, pos)
    if last_comment != -1:
        comment_end = content.find("-->", last_comment)
        if comment_end > pos:
            return True
    # Jinja/Twig comment
    last_jinja = content.rfind("{#", 0, pos)
    if last_jinja != -1:
        jinja_end = content.find("#}", last_jinja)
        if jinja_end > pos:
            return True
    # ERB comment
    last_erb = content.rfind("<%#", 0, pos)
    if last_erb != -1:
        erb_end = content.find("%>", last_erb)
        if erb_end > pos:
            return True
    return False


def is_in_tailwind_config(content: str, pos: int) -> bool:
    """Check if position is inside a tailwind.config block."""
    last_tw = content.rfind("tailwind.config", 0, pos)
    if last_tw == -1:
        return False
    config_end = content.find("</script>", last_tw)
    return config_end > pos


# ---------------------------------------------------------------------------
# Built-in audit rules
# ---------------------------------------------------------------------------

def check_hardcoded_colors(
    templates: list[Path],
    allowed_colors: set[str],
    base_dir: Path,
    standalone: set[Path] | None = None,
) -> list[Violation]:
    """Find hardcoded hex colors outside CSS variable definitions.

    Colors inside :root blocks, <style> class definitions, tailwind config,
    and comments are excluded. Colors in the allowed_colors set are also
    excluded (these are the design system token values that may appear in
    Tailwind bracket notation like bg-[#0d1421]).
    """
    violations = []
    standalone = standalone or set()

    for path in templates:
        if path in standalone:
            continue
        content = path.read_text(errors="replace")
        for match in HEX_COLOR_RE.finditer(content):
            color = match.group().lower()
            pos = match.start()
            if is_in_root_block(content, pos):
                continue
            if is_in_style_block(content, pos):
                continue
            if is_in_tailwind_config(content, pos):
                continue
            if is_in_comment(content, pos):
                continue
            if is_in_script_block(content, pos):
                continue
            if color in allowed_colors:
                continue
            violations.append(Violation(
                rule="hardcoded-color",
                file=str(path.relative_to(base_dir)),
                line=_line_number(content, pos),
                detail=f"Hardcoded color {color} — use a CSS variable or theme class",
            ))
    return violations


def check_required_classes(
    templates: list[Path],
    element_selector: str,
    required_classes: list[str],
    base_dir: Path,
    rule_name: str = "required-class",
) -> list[Violation]:
    """Verify that elements matching a pattern use one of the required classes.

    element_selector: regex pattern matching the HTML element (e.g., r'<button[^>]*>')
    required_classes: at least one of these classes must be present on the element.
    """
    violations = []
    element_re = re.compile(element_selector, re.IGNORECASE)

    for path in templates:
        content = path.read_text(errors="replace")
        for match in element_re.finditer(content):
            tag = match.group()
            pos = match.start()
            if is_in_comment(content, pos):
                continue
            if any(cls in tag for cls in required_classes):
                continue
            # Skip elements that are clearly non-styled (e.g., type="hidden")
            if 'type="hidden"' in tag or 'type="submit"' not in tag and "btn" not in tag.lower():
                continue
            violations.append(Violation(
                rule=rule_name,
                file=str(path.relative_to(base_dir)),
                line=_line_number(content, pos),
                detail=f"Element missing required class (need one of: {', '.join(required_classes)})",
                severity="warning",
            ))
    return violations


def check_inline_style_duplication(
    templates: list[Path],
    forbidden_patterns: list[str],
    base_dir: Path,
    rule_name: str = "inline-style-duplication",
) -> list[Violation]:
    """Find inline styles that duplicate shared utility classes.

    forbidden_patterns: regex patterns for inline styles that should use
    a utility class instead (e.g., r'style="[^"]*background:\\s*#c09a3a').
    """
    violations = []

    for path in templates:
        content = path.read_text(errors="replace")
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                pos = match.start()
                if is_in_comment(content, pos):
                    continue
                if is_in_style_block(content, pos):
                    continue
                violations.append(Violation(
                    rule=rule_name,
                    file=str(path.relative_to(base_dir)),
                    line=_line_number(content, pos),
                    detail=f"Inline style duplicates a shared class: {match.group()[:60]}",
                ))
    return violations


def check_class_presence(
    templates: list[Path],
    class_name: str,
    rule_name: str | None = None,
    at_least_one: bool = True,
) -> list[Violation]:
    """Verify a CSS class exists in at least one template (or a specific one)."""
    violations = []
    found = False
    for path in templates:
        content = path.read_text(errors="replace")
        if class_name in content:
            found = True
            break
    if at_least_one and not found:
        violations.append(Violation(
            rule=rule_name or f"missing-class-{class_name}",
            file="(all templates)",
            line=None,
            detail=f"Class '{class_name}' not found in any template",
        ))
    return violations


def check_class_defined_in_base(
    base_content: str,
    class_names: list[str],
    base_path: str = "base.html",
    rule_name: str = "class-in-base",
) -> list[Violation]:
    """Verify that utility classes are defined in the base template."""
    violations = []
    for cls in class_names:
        # Look for .class-name in CSS
        if f".{cls}" not in base_content:
            violations.append(Violation(
                rule=rule_name,
                file=base_path,
                line=None,
                detail=f"Utility class '.{cls}' not defined in base template",
            ))
    return violations


def check_no_local_redefinition(
    templates: list[Path],
    class_names: list[str],
    base_dir: Path,
    base_template: Path | None = None,
    rule_name: str = "local-redefinition",
) -> list[Violation]:
    """Ensure shared classes are not redefined in individual templates."""
    violations = []
    for path in templates:
        if base_template and path == base_template:
            continue
        content = path.read_text(errors="replace")
        for cls in class_names:
            pattern = re.compile(rf"\.{re.escape(cls)}\s*\{{", re.IGNORECASE)
            for match in pattern.finditer(content):
                if not is_in_comment(content, match.start()):
                    violations.append(Violation(
                        rule=rule_name,
                        file=str(path.relative_to(base_dir)),
                        line=_line_number(content, match.start()),
                        detail=f"Class '.{cls}' redefined locally — should only be in base template",
                    ))
    return violations


def check_token_sync(
    base_content: str,
    standalone_content: str,
    standalone_path: str,
    token_pattern: str = r"--[\w-]+:\s*([^;]+);",
    rule_name: str = "token-sync",
) -> list[Violation]:
    """Verify CSS custom property values match between base and standalone templates."""
    violations = []
    base_tokens = dict(re.findall(token_pattern, base_content))
    standalone_tokens = dict(re.findall(token_pattern, standalone_content))

    for token, base_value in base_tokens.items():
        if token in standalone_tokens:
            standalone_value = standalone_tokens[token]
            if base_value.strip() != standalone_value.strip():
                violations.append(Violation(
                    rule=rule_name,
                    file=standalone_path,
                    line=None,
                    detail=(
                        f"Token --{token} has value '{standalone_value.strip()}' "
                        f"but base has '{base_value.strip()}'"
                    ),
                ))
    return violations


def check_aria_landmarks(
    base_content: str,
    base_path: str = "base.html",
    rule_name: str = "aria-landmarks",
) -> list[Violation]:
    """Verify ARIA landmarks are present in the base layout."""
    violations = []
    if "<nav" not in base_content and 'role="navigation"' not in base_content:
        violations.append(Violation(
            rule=rule_name, file=base_path, line=None,
            detail="No <nav> element or role='navigation' found",
        ))
    if "<main" not in base_content and 'role="main"' not in base_content:
        violations.append(Violation(
            rule=rule_name, file=base_path, line=None,
            detail="No <main> element or role='main' found",
        ))
    return violations


# ---------------------------------------------------------------------------
# Auditor orchestrator
# ---------------------------------------------------------------------------

@dataclass
class AuditRule:
    """A named audit rule with a callable that returns violations."""
    name: str
    check: Callable[[], list[Violation]]


class TemplateAuditor:
    """Configurable static analysis auditor for HTML templates.

    Args:
        templates_dir: Root directory to scan for .html files.
        allowed_colors: Set of hex colors (lowercase) that are part of the
            design system and allowed in templates.
        standalone_templates: Set of template paths that define their own
            CSS (not extending the base template).
        base_template: Path to the base/layout template.
        file_glob: Glob pattern for template files. Default: "**/*.html"
    """

    def __init__(
        self,
        templates_dir: str | Path,
        allowed_colors: set[str] | None = None,
        standalone_templates: set[str | Path] | None = None,
        base_template: str | Path | None = None,
        file_glob: str = "**/*.html",
    ):
        self.base_dir = Path(templates_dir).resolve()
        self.allowed_colors = {c.lower() for c in (allowed_colors or set())}
        self.standalone = {Path(p).resolve() for p in (standalone_templates or set())}
        self.base_template = Path(base_template).resolve() if base_template else None
        self.file_glob = file_glob
        self._custom_rules: list[AuditRule] = []

    def find_templates(self) -> list[Path]:
        """Find all template files under the templates directory."""
        return sorted(self.base_dir.rglob(self.file_glob))

    def find_extending_templates(self) -> list[Path]:
        """Find templates that are not standalone."""
        return [p for p in self.find_templates() if p not in self.standalone]

    def base_content(self) -> str:
        """Read the base template content."""
        if self.base_template and self.base_template.exists():
            return self.base_template.read_text(errors="replace")
        return ""

    # -- Rule registration --

    def add_color_check(self) -> "TemplateAuditor":
        """Add the hardcoded color check."""
        self._custom_rules.append(AuditRule(
            name="hardcoded-colors",
            check=lambda: check_hardcoded_colors(
                self.find_extending_templates(),
                self.allowed_colors,
                self.base_dir,
                self.standalone,
            ),
        ))
        return self

    def add_class_check(
        self,
        element_pattern: str,
        required_classes: list[str],
        rule_name: str = "required-class",
    ) -> "TemplateAuditor":
        """Add a check that elements must use specific classes."""
        self._custom_rules.append(AuditRule(
            name=rule_name,
            check=lambda: check_required_classes(
                self.find_templates(),
                element_pattern,
                required_classes,
                self.base_dir,
                rule_name,
            ),
        ))
        return self

    def add_no_redefinition_check(
        self,
        class_names: list[str],
        rule_name: str = "no-local-redefinition",
    ) -> "TemplateAuditor":
        """Add a check that shared classes aren't redefined locally."""
        self._custom_rules.append(AuditRule(
            name=rule_name,
            check=lambda: check_no_local_redefinition(
                self.find_templates(),
                class_names,
                self.base_dir,
                self.base_template,
                rule_name,
            ),
        ))
        return self

    def add_base_class_check(
        self,
        class_names: list[str],
        rule_name: str = "classes-in-base",
    ) -> "TemplateAuditor":
        """Add a check that utility classes are defined in the base template."""
        self._custom_rules.append(AuditRule(
            name=rule_name,
            check=lambda: check_class_defined_in_base(
                self.base_content(),
                class_names,
                str(self.base_template.relative_to(self.base_dir)) if self.base_template else "base.html",
                rule_name,
            ),
        ))
        return self

    def add_token_sync_check(
        self,
        standalone_path: str | Path,
        rule_name: str = "token-sync",
    ) -> "TemplateAuditor":
        """Add a check that tokens match between base and a standalone template."""
        sp = Path(standalone_path).resolve()
        self._custom_rules.append(AuditRule(
            name=rule_name,
            check=lambda: check_token_sync(
                self.base_content(),
                sp.read_text(errors="replace") if sp.exists() else "",
                str(sp.relative_to(self.base_dir)),
                rule_name=rule_name,
            ),
        ))
        return self

    def add_aria_check(self, rule_name: str = "aria-landmarks") -> "TemplateAuditor":
        """Add ARIA landmark checks on the base template."""
        self._custom_rules.append(AuditRule(
            name=rule_name,
            check=lambda: check_aria_landmarks(
                self.base_content(),
                str(self.base_template.relative_to(self.base_dir)) if self.base_template else "base.html",
                rule_name,
            ),
        ))
        return self

    def add_inline_style_check(
        self,
        forbidden_patterns: list[str],
        rule_name: str = "inline-style-duplication",
    ) -> "TemplateAuditor":
        """Add a check for inline styles that duplicate shared classes."""
        self._custom_rules.append(AuditRule(
            name=rule_name,
            check=lambda: check_inline_style_duplication(
                self.find_templates(),
                forbidden_patterns,
                self.base_dir,
                rule_name,
            ),
        ))
        return self

    def add_custom_rule(
        self,
        name: str,
        check: Callable[[], list[Violation]],
    ) -> "TemplateAuditor":
        """Add an arbitrary custom rule."""
        self._custom_rules.append(AuditRule(name=name, check=check))
        return self

    # -- Execution --

    def run_all(self) -> AuditResults:
        """Run all registered audit rules and return aggregated results."""
        results = AuditResults()
        results.templates_scanned = len(self.find_templates())
        results.rules_checked = len(self._custom_rules)

        for rule in self._custom_rules:
            results.violations.extend(rule.check())

        return results

    def run_rule(self, rule_name: str) -> list[Violation]:
        """Run a single named rule."""
        for rule in self._custom_rules:
            if rule.name == rule_name:
                return rule.check()
        raise KeyError(f"No rule named '{rule_name}'")


# ---------------------------------------------------------------------------
# Convenience: create auditor from a config dict
# ---------------------------------------------------------------------------

def from_config(config: dict) -> TemplateAuditor:
    """Create a TemplateAuditor from a configuration dictionary.

    Expected config structure:
    {
        "templates_dir": "app/",
        "base_template": "app/templates/base.html",
        "file_glob": "**/*.html",  # optional
        "allowed_colors": ["#0d1421", "#c09a3a", ...],
        "standalone_templates": ["app/pages/login.html", ...],
        "rules": {
            "hardcoded_colors": true,
            "aria_landmarks": true,
            "required_classes": [
                {
                    "name": "button-classes",
                    "element_pattern": "<button[^>]*>",
                    "classes": ["btn-primary", "btn-ghost"]
                }
            ],
            "no_redefinition": [
                {
                    "name": "no-local-alerts",
                    "classes": ["alert-warn", "alert-error", "alert-success"]
                }
            ],
            "base_classes": [
                {
                    "name": "utility-classes",
                    "classes": ["btn-brass", "btn-ghost", "status-badge"]
                }
            ],
            "token_sync": [
                {
                    "name": "participate-sync",
                    "standalone": "app/meetings/templates/participate.html"
                }
            ],
            "inline_styles": [
                {
                    "name": "no-inline-button-bg",
                    "patterns": ["style=\"[^\"]*background:\\s*#"]
                }
            ]
        }
    }
    """
    auditor = TemplateAuditor(
        templates_dir=config["templates_dir"],
        allowed_colors=set(config.get("allowed_colors", [])),
        standalone_templates=set(config.get("standalone_templates", [])),
        base_template=config.get("base_template"),
        file_glob=config.get("file_glob", "**/*.html"),
    )

    rules = config.get("rules", {})

    if rules.get("hardcoded_colors"):
        auditor.add_color_check()

    if rules.get("aria_landmarks"):
        auditor.add_aria_check()

    for rc in rules.get("required_classes", []):
        auditor.add_class_check(
            element_pattern=rc["element_pattern"],
            required_classes=rc["classes"],
            rule_name=rc.get("name", "required-class"),
        )

    for nr in rules.get("no_redefinition", []):
        auditor.add_no_redefinition_check(
            class_names=nr["classes"],
            rule_name=nr.get("name", "no-local-redefinition"),
        )

    for bc in rules.get("base_classes", []):
        auditor.add_base_class_check(
            class_names=bc["classes"],
            rule_name=bc.get("name", "classes-in-base"),
        )

    for ts in rules.get("token_sync", []):
        auditor.add_token_sync_check(
            standalone_path=ts["standalone"],
            rule_name=ts.get("name", "token-sync"),
        )

    for ist in rules.get("inline_styles", []):
        auditor.add_inline_style_check(
            forbidden_patterns=ist["patterns"],
            rule_name=ist.get("name", "inline-style-duplication"),
        )

    return auditor
