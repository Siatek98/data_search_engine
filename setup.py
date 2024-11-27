from setuptools import setup, find_packages

setup(
    name="data-search-engine",
    version="1.0.7",  # Zwiększ numer wersji
    description="A Python-based data search and visualization engine.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Siatek98",
    url="https://github.com/Siatek98/data_search_engine",
    packages=find_packages(),  # Znajduje wszystkie pakiety, w tym data_search_engine
    include_package_data=True,
    install_requires=[
        "pandas",
        "matplotlib",
        "fredapi",
        "pyperclip",
        "yfinance",
        "requests",
        "reportlab",
        "openpyxl",
        "eurostat",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
