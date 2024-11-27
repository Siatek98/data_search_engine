# Data Search App

An application for searching, analyzing, and visualizing financial and economic data from multiple sources such as FRED, Eurostat, World Bank, and Yahoo Finance. The app enables creating reports, generating dynamic charts, and exporting results to Excel and PDF files.

## Features

- **Data Search:**
  - Search macroeconomic indicators from FRED (Federal Reserve Economic Data).
  - Retrieve stock market data and fundamentals via Yahoo Finance.
  - Explore statistical datasets from Eurostat.
  - Access global development indicators from the World Bank.

- **Data Export:**
  - Save search results as Excel spreadsheets or PDF reports.
  - Generate detailed financial reports for selected datasets.

- **Data Visualization:**
  - Create dynamic, interactive charts for financial data.
  - Choose specific countries, indicators, or date ranges for detailed analysis.

- **Favorites Management:**
  - Save frequently used indicators to a "Favorites" section for quick access.

## System Requirements

- **Python:** Version 3.8 or newer.
- **Operating System:** Works on Windows, macOS, and Linux.
- **Dependencies:** Install required Python libraries listed in `requirements.txt`.

## Installation and Setup

To install and run the application, clone the repository using:
```bash
git clone https://github.com/your-username/data-search-app.git
cd data-search-app
```
Install the required dependencies:
```bash
pip install -r requirements.txt
```
Start the application:
```bash
python main.py
```
You will need API keys for the following services:

- **FRED API Key:** Obtain it [here](https://fred.stlouisfed.org/docs/api/fred/).
- **Financial Modeling Prep (FMP) API Key:** Obtain it [here](https://financialmodelingprep.com/developer).

When the application launches, it will prompt you to enter these API keys. Once saved, the application will remember your keys for future use.

## Screenshots

- **Main Window:**
  ![Main Window](https://via.placeholder.com/800x400?text=Main+Window)

- **Excel Report Example:**
  ![Excel Report](https://via.placeholder.com/800x400?text=Excel+Report)

- **Data Visualization:**
  ![Data Visualization](https://via.placeholder.com/800x400?text=Data+Visualization)

## Future Development

Planned features include:

- Automatic Data Fetching: Schedule regular updates for selected datasets.
- Additional Data Sources: Expand support to include IMF, Eikon, and other APIs.
- Database Integration: Allow data storage and retrieval from SQL and MongoDB.
- Custom Indicators: Create user-defined metrics and calculations using downloaded data.

## Support

If you encounter any issues, have questions, or want to suggest improvements, please:

- Create an issue in the GitHub repository.
- Contact me via email at `your-email@example.com`.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT). You are free to use, modify, and distribute this project as long as proper credit is given.

