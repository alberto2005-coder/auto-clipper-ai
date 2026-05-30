from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="autoclipper",
    version="0.1.0",
    author="Antigravity",
    description="Herramienta ligera de IA para automatizar clips de YouTube Shorts y TikTok.",
    packages=find_packages(),
    py_modules=["main", "transcriber", "analyzer", "subtitle_generator", "video_editor"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "autoclipper=main:main",
        ],
    },
    python_requires=">=3.8",
)
