# Contributing to PersonaLab

We welcome contributions to PersonaLab! This document provides guidelines for contributing to the project.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/PersonaLab.git
   cd PersonaLab
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```
5. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## 🛠️ Development Guidelines

### Code Style

We maintain high code quality standards:

- **Python**: Follow PEP 8 guidelines
- **Code Formatting**: Use Black for consistent formatting
- **Linting**: Use Flake8 for code linting
- **Type Hints**: Use MyPy for type checking
- **Documentation**: Write clear docstrings for all functions and classes

### Running Code Quality Checks

```bash
# Format code with Black
black .

# Run linting with Flake8
flake8 personalab/

# Run type checking with MyPy
mypy personalab/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Testing

We maintain comprehensive test coverage:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=personalab --cov-report=term-missing

# Run specific test file
pytest tests/test_memory.py

# Run tests with verbose output
pytest -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test function names
- Include both unit tests and integration tests
- Mock external dependencies (LLM APIs, etc.)

Example test structure:
```python
def test_memory_creation():
    """Test basic memory creation functionality."""
    memory = Memory("test_agent")
    assert memory.agent_id == "test_agent"
    assert memory.get_profile_content() == ""
```

## 📝 Pull Request Process

### Before Submitting

1. **Run all tests** and ensure they pass
2. **Run code quality checks** and fix any issues
3. **Update documentation** if you're changing APIs
4. **Add or update tests** for new functionality
5. **Check for breaking changes** and document them

### Pull Request Guidelines

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make focused commits** with clear messages:
   ```bash
   git commit -m "Add Theory of Mind analysis pipeline"
   ```

3. **Write a clear PR description**:
   - Explain what changes you made
   - Why you made them
   - How to test the changes
   - Link any related issues

4. **Keep PRs small and focused** - one feature or fix per PR

5. **Respond to review feedback** promptly and professionally

### Commit Message Format

Use clear, descriptive commit messages:

```
Add support for custom LLM providers

- Implement BaseLLM interface for custom providers
- Add provider registration system
- Update documentation with custom provider examples

Fixes #123
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected vs actual behavior**
4. **Environment details** (Python version, OS, dependencies)
5. **Minimal code example** that demonstrates the issue
6. **Error messages and stack traces**

Use our bug report template:

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- Python version:
- PersonaLab version:
- Operating System:
- LLM Provider:

## Code Example
```python
# Minimal code that reproduces the issue
```

## Error Messages
```
Paste any error messages or stack traces here
```
```

## 💡 Feature Requests

For feature requests, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** clearly
3. **Explain the expected behavior**
4. **Consider implementation complexity**
5. **Discuss API design** if applicable

## 🔍 Code Review Guidelines

### For Reviewers

- **Be constructive** and helpful in feedback
- **Focus on code quality**, not personal preferences
- **Suggest improvements** with explanations
- **Test the changes** locally when possible
- **Check for edge cases** and error handling

### For Contributors

- **Respond to feedback** thoughtfully
- **Ask questions** if feedback is unclear
- **Make requested changes** promptly
- **Test your changes** after modifications
- **Thank reviewers** for their time

## 🏗️ Architecture Guidelines

### Memory System

- **Unified Memory Architecture**: Use the new Memory class with ProfileMemory, EventMemory, and ToMMemory components
- **LLM Integration**: Follow the BaseLLM interface for new providers
- **Pipeline Design**: Maintain the three-stage update pipeline (Modification → Update → Theory of Mind)

### Adding New Features

1. **Follow existing patterns** in the codebase
2. **Maintain backward compatibility** when possible
3. **Add comprehensive tests** for new functionality
4. **Update documentation** and examples
5. **Consider performance implications**

### Database Changes

- **Use migrations** for schema changes
- **Maintain backward compatibility** with existing data
- **Test with different database sizes**
- **Document any new database requirements**

## 📚 Documentation

### Types of Documentation

1. **Code Documentation**: Docstrings and comments
2. **API Documentation**: Function and class references
3. **User Guides**: How-to guides and tutorials
4. **Architecture Documentation**: System design and principles

### Documentation Standards

- **Write clear, concise explanations**
- **Include code examples** where helpful
- **Keep documentation up-to-date** with code changes
- **Use proper markdown formatting**
- **Link to related documentation**

## 🌟 Recognition

Contributors are recognized in several ways:

- **GitHub Contributors** section
- **Release notes** acknowledgments
- **Community showcases** for significant contributions
- **Maintainer roles** for consistent contributors

## 📞 Getting Help

If you need help with contributing:

1. **Check existing documentation** and issues
2. **Ask in GitHub Discussions** for general questions
3. **Create an issue** for specific problems
4. **Join our Discord** for real-time chat
5. **Email maintainers** for sensitive issues

## 🏷️ Issue Labels

We use labels to categorize issues:

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested
- `wontfix`: This will not be worked on

## 🎯 Project Goals

Keep these goals in mind when contributing:

1. **User-Friendly**: Make AI memory management accessible
2. **Performant**: Optimize for speed and memory efficiency
3. **Extensible**: Support multiple LLM providers and use cases
4. **Reliable**: Ensure robust error handling and testing
5. **Well-Documented**: Maintain comprehensive documentation

## 📄 License

By contributing to PersonaLab, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to PersonaLab! 🙏 