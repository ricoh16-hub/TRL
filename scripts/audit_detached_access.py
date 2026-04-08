#!/usr/bin/env python
"""
Audit script to find all detached-object access patterns in UI code.
"""
import ast
from pathlib import Path

# Potential lazy-load attributes (relationships and properties that might lazy-load)
LAZY_LOAD_ATTRS = {
    'role_links',  # relationship
    'password_record',  # relationship
    'pin_record',  # relationship
    'role',  # property that accesses role_links
    'nama',  # property that returns full_name (scalar, but included for completeness)
}

# Attributes that are safe (scalar columns loaded immediately with object)
SAFE_ATTRS = {
    'id', 'username', 'full_name', 'email', 'phone', 'status',
    'created_at', 'updated_at', 'deleted_at', 'password', 'pin_hash',
    'password_hash', 'password_salt', 'pin_salt'
}

class UserAttributeVisitor(ast.NodeVisitor):
    """Find all attribute accesses on user objects."""
    
    def __init__(self) -> None:
        self.user_attrs: set[tuple[int, str, str]] = set()
        self.current_context = ""
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check for user attribute access patterns
        if isinstance(node.value, ast.Name):
            if node.value.id in ('user', '_user', 'self._user'):
                # Get line number and construct the full expression
                line_num = node.lineno
                attr_name = node.attr
                context = self.current_context or "toplevel"
                self.user_attrs.add((line_num, f"{node.value.id}.{attr_name}", context))
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        # Check for getattr(user, ...) patterns
        if isinstance(node.func, ast.Name) and node.func.id == 'getattr':
            if len(node.args) >= 2:
                first_arg = node.args[0]
                second_arg = node.args[1]
                
                if isinstance(first_arg, ast.Name) and first_arg.id in ('user', '_user'):
                    if isinstance(second_arg, ast.Constant):
                        attr_name = second_arg.value
                        line_num = node.lineno
                        context = self.current_context or "toplevel"
                        self.user_attrs.add((line_num, f"getattr({first_arg.id}, '{attr_name}')", context))
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_context = self.current_context
        self.current_context = f"func:{node.name}"
        self.generic_visit(node)
        self.current_context = old_context
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old_context = self.current_context
        self.current_context = f"class:{node.name}"
        self.generic_visit(node)
        self.current_context = old_context


def audit_file(filepath: Path) -> list[tuple[int, str, str, bool]]:
    """Audit a file and return list of user attribute accesses."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code)
        visitor = UserAttributeVisitor()
        visitor.visit(tree)
        
        results: list[tuple[int, str, str, bool]] = []
        for line_num, access_expr, context in sorted(visitor.user_attrs):
            # Extract the attribute name
            if '.' in access_expr:
                attr_name = access_expr.split('.')[-1]
            elif "'" in access_expr:
                attr_name = access_expr.split("'")[1]
            else:
                attr_name = "unknown"
            
            is_potential_issue = attr_name in LAZY_LOAD_ATTRS
            results.append((line_num, access_expr, context, is_potential_issue))
        
        return results
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return []


def main() -> None:
    ui_dir = Path("src/ui")
    auth_dir = Path("src/auth")
    
    print("=" * 80)
    print("UI CODE AUDIT: DETACHED-OBJECT ACCESS PATTERNS")
    print("=" * 80)
    
    files_to_audit: list[tuple[str, list[Path]]] = [
        ("UI Files", list(ui_dir.glob("*.py"))),
        ("Auth Files", list(auth_dir.glob("*.py"))),
    ]
    
    all_issues: list[tuple[Path, int, str, str]] = []
    
    for category, files in files_to_audit:
        print(f"\n{category}:")
        print("-" * 80)
        
        for filepath in sorted(files):
            results = audit_file(filepath)
            if results:
                print(f"\n📄 {filepath}")
                for line_num, expr, context, is_issue in results:
                    marker = "⚠️  POTENTIAL ISSUE" if is_issue else "✅ SAFE"
                    print(f"  {marker}: Line {line_num} - {context}")
                    print(f"           {expr}")
                    if is_issue:
                        all_issues.append((filepath, line_num, expr, context))
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Potential detached-object access issues found: {len(all_issues)}")
    
    if all_issues:
        print("\n⚠️  Issues requiring review:")
        for filepath, line_num, expr, context in all_issues:
            print(f"  • {filepath}:{line_num} - {expr} (in {context})")
    else:
        print("✅ No obvious detached-object issues found in grep search!")
    
    print(f"\n📊 Lazy-load attributes watched: {LAZY_LOAD_ATTRS}")
    print(f"✅ Safe attributes: {SAFE_ATTRS}")


if __name__ == "__main__":
    main()
