import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Core dependencies - minimal installation
core_requirements = [
    "requests>=2.31.0",
    "python-dotenv>=0.19.0",
    "json5>=0.9.0",
    "httpx>=0.24.0",
]

# Optional dependencies
extras_require = {
    # Core AI features
    "ai": [
        "openai>=1.0.0",
        "sentence-transformers>=2.2.0",
    ],
    # Full LLM support
    "llm": [
        "openai>=1.0.0",
        "anthropic>=0.7.0",
        "google-generativeai>=0.3.0",
        "cohere>=4.0.0",
        "boto3>=1.26.0",
        "together>=0.2.0",
        "replicate>=0.15.0",
    ],
    # Local model support
    "local": [
        "transformers>=4.21.0",
        "torch>=1.12.0",
        "sentence-transformers>=2.2.0",
    ],
    # Development dependencies
    "dev": [
        "pytest>=7.0",
        "pytest-cov>=4.0",
        "black>=22.0",
        "flake8>=5.0",
        "mypy>=1.0",
        "pre-commit>=3.0",
    ],
}

# Full installation (includes all features)
extras_require["all"] = list(set(sum(extras_require.values(), [])))

setuptools.setup(
    name="personalab",
    version="0.1.2",
    author="PersonaLab Team",
    author_email="support@personalab.ai",
    description="AI Memory and Conversation Management Framework - Simple as mem0, Powerful as PersonaLab",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NevaMind-AI/PersonaLab",
    project_urls={
        "Bug Tracker": "https://github.com/NevaMind-AI/PersonaLab/issues",
        "Documentation": "https://github.com/NevaMind-AI/PersonaLab#readme",
        "Source Code": "https://github.com/NevaMind-AI/PersonaLab",
        "Homepage": "https://personalab.ai",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="ai, memory, conversation, llm, chatbot, persona, agent",
    packages=setuptools.find_packages(),
    python_requires=">=3.8",
    install_requires=core_requirements,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "personalab=personalab.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 