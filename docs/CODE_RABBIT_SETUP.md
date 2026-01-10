# CodeRabbit Setup for Folder Extractor

## 🎉 Welcome to CodeRabbit!

This guide helps you set up and use **CodeRabbit** with the Folder Extractor repository.

**Repository**: https://github.com/0ui-labs/folder-extractor

## ✅ Current Status

CodeRabbit is **already configured** for this repository:

- `.coderabbit.yaml` ✅ (v2 schema)
- GitHub App installed ✅
- Auto-review enabled ✅
- German language support ✅

## 🔧 Prerequisites

- GitHub repository access
- CodeRabbit account (sign up at [coderabbit.ai](https://coderabbit.ai))
- Admin access for initial setup (already done)

## 📋 Current Configuration

The repository uses this `.coderabbit.yaml`:

```yaml
# yaml-language-server: $schema=https://coderabbit.ai/integrations/schema.v2.json
# CodeRabbit Configuration for Folder Extractor

language: de  # German language for reviews

reviews:
  profile: assertive  # Options: chill, assertive

  auto_review:
    enabled: true

  path_filters:
    - "folder_extractor/**/*.py"
    - "tests/**/*.py"
    - "setup.py"
    - "!**/__pycache__/**"
    - "!**/*.pyc"
    - "!**/*.pyo"
    - "!**/*.pyd"
    - "!tests/fixtures/**"
    - "!.github/**"
    - "!.vscode/**"
    - "!.idea/**"

chat:
  auto_reply: true
```

### Configuration Explained

| Setting | Value | Description |
|---------|-------|-------------|
| `language` | `de` | Reviews in German |
| `profile` | `assertive` | Thorough, detailed reviews |
| `auto_review` | `true` | Automatic review on every PR |
| `path_filters` | `folder_extractor/**` | Focus on source and test files |
| `auto_reply` | `true` | AI responds to questions in PR comments |

## 🚀 How to Use CodeRabbit

### 1. Create a Pull Request

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes...
git add .
git commit -m "feat: add my new feature"

# Push to GitHub
git push -u origin feature/my-new-feature
```

Then create a Pull Request on GitHub.

### 2. CodeRabbit Automatically Reviews

Within minutes, CodeRabbit will:
- 🔍 **Analyze** all changed files
- 📝 **Comment** with detailed review
- 🔐 **Check** for security issues
- ⚡ **Suggest** performance improvements
- 🧹 **Recommend** code quality improvements

### 3. Interact with CodeRabbit

You can ask CodeRabbit questions directly in PR comments:

```markdown
@coderabbitai explain this function
@coderabbitai is there a security issue here?
@coderabbitai suggest a better approach
@coderabbitai summarize the changes
```

### 4. Address Feedback

- ✅ Fix critical issues before merging
- 💡 Consider suggestions for improvements
- 💬 Ask for clarification if needed
- 🔄 Push fixes → CodeRabbit re-reviews automatically

## 🤖 CodeRabbit Features

### Automatic Code Reviews
- **AI-powered analysis** for every pull request
- **Python best practices** enforcement
- **Security vulnerability** detection
- **Performance optimization** suggestions
- **Ruff compatibility** checks

### Chat Integration
- **Ask questions** in any PR comment
- **Context-aware** responses based on your codebase
- **Multi-file analysis** for complex questions
- **German language** support

### What CodeRabbit Checks

| Category | Examples |
|----------|----------|
| **Security** | SQL injection, path traversal, hardcoded secrets |
| **Performance** | Inefficient loops, unnecessary allocations |
| **Quality** | Unused variables, dead code, complexity |
| **Style** | PEP 8 compliance, naming conventions |
| **Testing** | Missing tests, weak assertions |

## 📊 Integration with CI/CD

### Workflow with GitHub Actions + Ruff + CodeRabbit

```
┌─────────────────┐
│   Create PR     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ CodeRabbit      │    │ GitHub Actions  │
│ AI Review       │    │ (Ruff + pytest) │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌─────────────────┐
         │ Human Review    │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Merge to main   │
         └─────────────────┘
```

### All Checks Must Pass

1. **CodeRabbit** - No critical issues
2. **Ruff** - No linting errors
3. **pytest** - All tests pass
4. **Human approval** - At least 1 reviewer

## 🎯 Best Practices

### Writing Good Commit Messages

CodeRabbit understands conventional commits:

```bash
feat: add global deduplication
fix: handle empty directories correctly
docs: update README with new options
test: add hash calculation tests
refactor: extract file operations to separate module
```

### Organizing Pull Requests

- **Small, focused PRs** get better reviews
- **Clear descriptions** help CodeRabbit understand context
- **Link issues** with `Fixes #123` or `Closes #456`

### Responding to Feedback

```markdown
# Good responses:
@coderabbitai I fixed the issue in the latest commit
@coderabbitai This is intentional because [reason]
@coderabbitai Can you explain why this is a problem?

# Request re-review after fixes:
@coderabbitai review again
```

## 🔧 Customizing Configuration

### Switch to English Reviews

```yaml
language: en
```

### Use Relaxed Review Profile

```yaml
reviews:
  profile: chill  # Less strict, fewer comments
```

### Exclude More Files

```yaml
path_filters:
  - "folder_extractor/**/*.py"
  - "!**/migrations/**"
  - "!**/generated/**"
```

## 🤔 Troubleshooting

### CodeRabbit Not Reviewing

1. Check if GitHub App is installed: [github.com/apps/coderabbit](https://github.com/apps/coderabbit)
2. Verify `.coderabbit.yaml` exists in repo root
3. Ensure PR is not a draft
4. Check repository permissions

### Too Many Comments

```yaml
reviews:
  profile: chill  # Switch from assertive to chill
```

### Wrong Language

```yaml
language: en  # or de, fr, es, etc.
```

## 📚 Resources

- **CodeRabbit Docs**: [docs.coderabbit.ai](https://docs.coderabbit.ai)
- **Configuration Schema**: [coderabbit.ai/integrations/schema.v2.json](https://coderabbit.ai/integrations/schema.v2.json)
- **Ruff Docs**: [docs.astral.sh/ruff](https://docs.astral.sh/ruff/)
- **GitHub Actions**: [docs.github.com/en/actions](https://docs.github.com/en/actions)

## 🎉 Benefits

| Benefit | Description |
|---------|-------------|
| ⚡ **Faster Reviews** | AI reviews in minutes, not hours |
| 🔒 **Better Security** | Catches vulnerabilities humans miss |
| 📈 **Higher Quality** | Consistent standards across all PRs |
| 🎓 **Learning** | Explains issues and teaches best practices |
| 🌍 **German Support** | Native language reviews |

---

**Happy Coding with CodeRabbit!** 🐰🚀
