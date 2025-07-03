# Contributing to PersonaLab

Thank you for your interest in contributing to PersonaLab! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- PostgreSQL database
- Git

### Local Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/PersonaLab.git
   cd PersonaLab
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Set up database**
   ```bash
   # Configure PostgreSQL
   source setup_postgres_env.sh
   ```

## Development Workflow

### Branch Naming
- `feature/description` - for new features
- `fix/description` - for bug fixes
- `docs/description` - for documentation updates
- `refactor/description` - for code refactoring

### Commit Messages
Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(memory): add enhanced memory storage capabilities
fix(persona): resolve database compatibility issue
docs(readme): update installation instructions
```

### Code Style
- Follow PEP 8 style guidelines
- Use `black` for code formatting
- Use `isort` for import sorting
- Add type hints where appropriate
- Write descriptive docstrings

### Testing
```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=personalab

# Run specific test
python -m pytest tests/test_memory.py
```

### Documentation
- Update docstrings for new functions/classes
- Update README.md for significant changes
- Add examples for new features
- Update CHANGELOG.md

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code with appropriate tests
   - Update documentation
   - Follow code style guidelines

3. **Test your changes**
   ```bash
   python -m pytest
   pre-commit run --all-files
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**
   - Use a descriptive title
   - Include a detailed description
   - Reference any related issues
   - Add screenshots if applicable

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Areas for Contribution

### High Priority
- Additional LLM provider integrations
- Performance optimizations for large datasets
- Enhanced vector search capabilities
- Mobile/web interface development

### Medium Priority
- Additional database backends (MongoDB, Redis)
- Advanced conversation analytics
- Multi-language support
- API rate limiting and caching

### Documentation
- Tutorial improvements
- API documentation
- Example applications
- Video tutorials

## Code of Conduct

### Our Pledge
We pledge to make participation in our project a harassment-free experience for everyone.

### Standards
- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what is best for the community

### Enforcement
Instances of unacceptable behavior may be reported to the project maintainers.

## Questions?

- Create an issue for bugs or feature requests
- Join our discussions for general questions
- Check existing issues before creating new ones

Thank you for contributing to PersonaLab! 🚀 