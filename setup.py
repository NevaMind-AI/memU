import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setuptools.setup(
    name="personalab",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python framework for creating and managing AI personas and laboratory environments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NevaMind-AI/PersonaLab",
    project_urls={
        "Bug Tracker": "https://github.com/NevaMind-AI/PersonaLab/issues",
        "Documentation": "https://github.com/NevaMind-AI/PersonaLab#readme",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=5.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            # "your-cli-command=your_package.cli:main",
        ],
    },
) 