# SAHAL Money Transfer Transaction Analyzer

A comprehensive tool for analyzing SAHAL mobile money transfer transactions with date range tracking and detailed analytics.

## Features

- 📊 **Transaction Analysis**: Parse and analyze SAHAL transaction data
- 📅 **Date Range Tracking**: Automatically extract and display transaction date spans
- 💰 **Financial Insights**: Track sent/received amounts, net balances, and outstanding debts
- 📈 **Visual Analytics**: Charts and graphs for transaction patterns
- 🔍 **Data Validation**: Robust error handling and data validation
- 📁 **Multiple Export Formats**: CSV and JSON export options
- 🌐 **Web Dashboard**: Interactive Streamlit web application

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Analyze a transaction file:

```bash
python sahal_improved.py sample_transactions.txt
```

With custom output files:

```bash
python sahal_improved.py sample_transactions.txt --output-csv my_analysis.csv --output-json my_analysis.json
```

With verbose logging:

```bash
python sahal_improved.py sample_transactions.txt --verbose
```

### Streamlit Dashboard

Launch the interactive web dashboard:

```bash
streamlit run sahal_dashboard.py
```

Then open your browser to the provided URL (usually http://localhost:8501)

## Date Range Functionality

The analyzer now automatically extracts and displays:

- **Earliest Transaction Date**: The first transaction in your data
- **Latest Transaction Date**: The most recent transaction
- **Date Span**: Total number of days covered by your transactions
- **Dates Found**: Number of transactions with valid dates

### Supported Date Formats

The system recognizes these date patterns in your SAHAL data:

1. **Full Format**: `Tuesday, October 17, 2023 · 11:17 AM`
2. **Short Format**: `Tar: 17/10/23 13:35:59`

## Input File Format

Your SAHAL transaction file should contain blocks separated by `[SAHAL]` with patterns like:

```
[SAHAL]
$50.00 ayaad u dirtay John Doe(

[SAHAL]
Waxaad $25.00 ka heshay Jane Smith(

[SAHAL]
Waxaad $10.00 ugu shubtay 252907123456

[SAHAL]
You have received airtime of $5.00 from 252908123456
```

## Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run sahal_dashboard.py
```

### Heroku Deployment

1. Create a Heroku account and install Heroku CLI
2. Login to Heroku:

```bash
heroku login
```

3. Create a new Heroku app:

```bash
heroku create your-app-name
```

4. Deploy to Heroku:

```bash
git add .
git commit -m "Initial deployment"
git push heroku main
```

5. Open your app:

```bash
heroku open
```

### Streamlit Cloud Deployment

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Deploy with the following settings:
   - Main file path: `sahal_dashboard.py`
   - Python version: 3.9

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Railway will automatically detect the Python app
3. Set the start command: `streamlit run sahal_dashboard.py --server.port=$PORT --server.address=0.0.0.0`

## Output

### Command Line Output

- Summary statistics (total sent/received, net balance)
- Date range information
- Top people you owe money to
- Top people who owe you money
- CSV and JSON export files

### Dashboard Features

- Interactive transaction summary table
- Bar charts for top senders/receivers
- Pie chart for overall sent vs received
- People analysis (who owes whom)
- Raw transaction data viewer
- Unmatched transaction blocks viewer

## Files

- `sahal_improved.py` - Enhanced command-line analyzer with date functionality
- `sahal_dashboard.py` - Streamlit web dashboard
- `sample_transactions.txt` - Sample data for testing
- `requirements.txt` - Python dependencies
- `Procfile` - Heroku deployment configuration
- `runtime.txt` - Python version specification
- `setup.sh` - Deployment setup script
- `.gitignore` - Git ignore rules for personal data
- `README.md` - This documentation

## Example Output

```
==================================================
SAHAL TRANSACTION ANALYSIS
==================================================
Total Transactions: 10
Total Sent: $67.50
Total Received: $73.00
Net Balance: $5.50
Unique Contacts: 8
Average Transaction: $14.05
Unmatched Blocks: 0

📅 DATE RANGE:
   From: January 15, 2024
   To:   January 21, 2024
   Span: 6 days
   Dates Found: 10

TOP 5 PEOPLE YOU OWE MONEY TO:
RESTAURANT ABC: $8.50
SUPERMARKET XYZ: $15.75
John Doe: $25.00
Sarah Wilson: $12.00
Lisa Davis: $7.25
```

## Privacy & Security

- **No Personal Data**: The repository contains no personal transaction data
- **Local Processing**: All data processing happens locally on your machine
- **No Data Storage**: The app doesn't store or transmit your transaction data
- **Sample Data**: Use `sample_transactions.txt` for testing and demonstration

## Troubleshooting

- **No transactions found**: Check your input file format
- **Missing dates**: Ensure your transaction blocks contain date information
- **Import errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`
- **Deployment issues**: Check the deployment platform's logs for specific error messages

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the analyzer.

## License

This project is open source and available under the MIT License.
