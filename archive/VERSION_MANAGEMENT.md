# Version Management

This project uses **Semantic Versioning** (SemVer): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (e.g., 1.0.0 → 1.0.1)

## Current Version

```bash
python -c "from src.__version__ import __version__; print(__version__)"
```

Or use the Makefile:
```bash
make version
```

## Bumping Versions

### Using Makefile (Recommended)

```bash
# Patch version (1.0.0 → 1.0.1)
make version-patch

# Minor version (1.0.0 → 1.1.0)
make version-minor

# Major version (1.0.0 → 2.0.0)
make version-major
```

### Using Script Directly

```bash
# With release note
python scripts/bump_version.py patch "Fixed health tracker bug"

# Without release note
python scripts/bump_version.py minor
```

## What Happens During Version Bump

1. **Updates `src/__version__.py`** with new version number
2. **Adds release note** to `RELEASE_NOTES` dict (if provided)
3. **Commits the change** with message: `chore: bump version to X.Y.Z`
4. **Creates git tag** `vX.Y.Z` with annotation
5. **Prints push instructions**

## Publishing a Release

After bumping the version:

```bash
# Push the commit and tag
git push origin main
git push origin v1.0.1

# Or push all tags at once
git push origin main --tags
```

## GitHub Releases

After pushing the tag, create a GitHub release:

1. Go to https://github.com/dusty-schmidt/smart-data-pipeline/releases
2. Click "Draft a new release"
3. Select the tag (e.g., `v1.0.1`)
4. Add release notes
5. Publish

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.0.0 | 2025-12-07 | Initial release - Tier 2 Autonomy Kernel complete |

## Automated Workflows (Future)

Consider setting up GitHub Actions to:
- Auto-create releases when tags are pushed
- Run tests before allowing version bumps
- Generate changelog from commit messages
- Publish to PyPI (if making it a package)

## Example Workflow

```bash
# Make some changes
git add .
git commit -m "feat: add new feature"

# Bump version (creates commit + tag)
make version-minor

# Push everything
git push origin main --tags

# Create GitHub release (manual or automated)
```
