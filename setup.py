from setuptools import setup, find_packages

with open("requirements.txt", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

try:
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = ""

setup(
    name="autoclipper",
    version="1.0.0",
    author="Alberto",
    description="Herramienta inteligente para automatizar la extraccion de clips para TikTok y Shorts usando IA.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alberto2005-coder/auto-clipper-ai",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    py_modules=["main", "gui", "run_gui"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "autoclipper=main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
)
