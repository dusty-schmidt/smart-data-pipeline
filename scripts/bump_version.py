#!/usr/bin/env python3
"""
Version management script for Smart Data Pipeline.

Usage:
    python scripts/bump_version.py [major|minor|patch]
    
Examples:
    python scripts/bump_version.py patch   # 1.0.0 -> 1.0.1
    python scripts/bump_version.py minor   # 1.0.0 -> 1.1.0
    python scripts/bump_version.py major   # 1.0.0 -> 2.0.0
"""
import sys
import re
from pathlib import Path
from datetime import datetime

# Paths
ROOT = Path(__file__).parent.parent
VERSION_FILE = ROOT / "src" / "__version__.py"


def get_current_version():
    """Read current version from __version__.py"""
    content = VERSION_FILE.read_text()
    match = re.search(r'__version__ = "(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        raise ValueError("Could not find version in __version__.py")
    return tuple(map(int, match.groups()))


def bump_version(bump_type):
    """Bump version based on type (major, minor, patch)"""
    major, minor, patch = get_current_version()
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use major, minor, or patch")
    
    return (major, minor, patch)


def update_version_file(version, release_note=None):
    """Update __version__.py with new version"""
    major, minor, patch = version
    version_str = f"{major}.{minor}.{patch}"
    
    # Read current content
    content = VERSION_FILE.read_text()
    
    # Update version string
    content = re.sub(
        r'__version__ = "[\d\.]+"',
        f'__version__ = "{version_str}"',
        content
    )
    
    # Update version info tuple
    content = re.sub(
        r'__version_info__ = \([\d, ]+\)',
        f'__version_info__ = {version}',
        content
    )
    
    # Add release note if provided
    if release_note:
        # Find RELEASE_NOTES dict and add new entry
        notes_match = re.search(r'(RELEASE_NOTES = \{[^}]+)', content, re.DOTALL)
        if notes_match:
            # Insert new note at the beginning of the dict
            content = re.sub(
                r'(RELEASE_NOTES = \{\n)',
                f'\\1    "{version_str}": "{release_note}",\n',
                content
            )
    
    VERSION_FILE.write_text(content)
    return version_str


def create_git_tag(version_str, message=None):
    """Create and push git tag"""
    import subprocess
    
    tag_name = f"v{version_str}"
    tag_message = message or f"Release {version_str}"
    
    # Create annotated tag
    subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", tag_message],
        check=True
    )
    
    print(f"✅ Created tag: {tag_name}")
    return tag_name


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    bump_type = sys.argv[1].lower()
    release_note = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Get current version
    old_version = get_current_version()
    old_version_str = f"{old_version[0]}.{old_version[1]}.{old_version[2]}"
    
    # Bump version
    new_version = bump_version(bump_type)
    new_version_str = update_version_file(new_version, release_note)
    
    print(f"📦 Version bumped: {old_version_str} → {new_version_str}")
    
    # Stage the version file
    import subprocess
    subprocess.run(["git", "add", str(VERSION_FILE)], check=True)
    
    # Commit
    commit_msg = f"chore: bump version to {new_version_str}"
    if release_note:
        commit_msg += f"\n\n{release_note}"
    
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    print(f"✅ Committed version bump")
    
    # Create tag
    tag_name = create_git_tag(new_version_str, release_note)
    
    print(f"\n🎉 Version {new_version_str} ready!")
    print(f"\nTo push to GitHub:")
    print(f"  git push origin main")
    print(f"  git push origin {tag_name}")


if __name__ == "__main__":
    main()
