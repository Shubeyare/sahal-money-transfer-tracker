#!/usr/bin/env python3
"""
SAHAL Money Transfer Transaction Analyzer
Enhanced version with improved error handling, data validation, and features
"""

import re
import csv
import json
import logging
import argparse
from datetime import datetime, date
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SAHALTransactionParser:
    """Enhanced SAHAL transaction parser with validation and error handling."""
    
    def __init__(self):
        self.transaction_patterns = [
            # Sent money to person
            (r"\$ ?([\d.]+) ayaad u dirtay (.+?)\(", 'sent', 'person'),
            # Sent airtime to phone number
            (r"Waxaad \$([\d.]+) ugu shubtay (\d{9,})", 'sent', 'airtime'),
            # Received money from person
            (r"Waxaad \$([\d.]+) ka heshay (.+?)\(", 'received', 'person'),
            # Received airtime from phone number
            (r"You have received airtime of \$([\d.]+) from (\d{9,})", 'received', 'airtime'),
        ]
        
        # Date patterns for extraction
        self.date_patterns = [
            # Pattern 1: "Tuesday, October 17, 2023 · 11:17 AM"
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4}) · (\d{1,2}):(\d{2})(?:\u202F|\s)?(AM|PM)',
            # Pattern 2: "Tar: 17/10/23 13:35:59" (DD/MM/YY HH:MM:SS)
            r'Tar: (\d{1,2})/(\d{1,2})/(\d{2}) (\d{1,2}):(\d{2}):(\d{2})',
        ]
    
    def clean_input(self, text: str) -> str:
        """Clean input text by removing date/time stamps and extra whitespace."""
        if not text:
            return ""
        
        # Remove date lines like "Monday, September 2, 2024 · 10:55 PM"
        cleaned = re.sub(
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), .*?\d{4} · \d{1,2}:\d{2}(?:\u202F|\s)?(?:AM|PM)', 
            '', 
            text
        )
        return cleaned.strip()
    
    def parse_date_from_text(self, text: str) -> Optional[datetime]:
        """Parse date from text using multiple patterns."""
        if not text:
            return None
        
        # Try pattern 1: "Tuesday, October 17, 2023 · 11:17 AM"
        match1 = re.search(self.date_patterns[0], text)
        if match1:
            try:
                day_name, month_name, day, year, hour, minute, ampm = match1.groups()
                month_map = {
                    'January': 1, 'February': 2, 'March': 3, 'April': 4,
                    'May': 5, 'June': 6, 'July': 7, 'August': 8,
                    'September': 9, 'October': 10, 'November': 11, 'December': 12
                }
                month = month_map[month_name]
                hour = int(hour)
                if ampm.upper() == 'PM' and hour != 12:
                    hour += 12
                elif ampm.upper() == 'AM' and hour == 12:
                    hour = 0
                
                return datetime(int(year), month, int(day), hour, int(minute))
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing date pattern 1: {e}")
        
        # Try pattern 2: "Tar: 17/10/23 13:35:59"
        match2 = re.search(self.date_patterns[1], text)
        if match2:
            try:
                day, month, year, hour, minute, second = match2.groups()
                # Convert 2-digit year to 4-digit (assuming 20xx)
                full_year = 2000 + int(year)
                return datetime(full_year, int(month), int(day), int(hour), int(minute), int(second))
            except ValueError as e:
                logger.warning(f"Error parsing date pattern 2: {e}")
        
        return None
    
    def validate_amount(self, amount_str: str) -> Optional[float]:
        """Validate and convert amount string to float."""
        try:
            amount = float(amount_str)
            if amount <= 0:
                logger.warning(f"Invalid amount: {amount_str} (must be positive)")
                return None
            return amount
        except ValueError:
            logger.warning(f"Invalid amount format: {amount_str}")
            return None
    
    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format."""
        return bool(re.match(r'^\d{9,}$', phone))
    
    def extract_transactions(self, text: str) -> Tuple[List[Dict], List[str], Dict]:
        """Extract transactions from SAHAL text with comprehensive validation and date range."""
        if not text:
            return [], [], {}
        
        blocks = [b.strip() for b in text.split('[SAHAL]') if b.strip()]
        transactions = []
        unmatched_blocks = []
        dates = []
        
        logger.info(f"Processing {len(blocks)} transaction blocks")
        
        for i, block in enumerate(blocks, 1):
            block = block.strip()
            transaction = None
            
            # Extract date from block
            block_date = self.parse_date_from_text(block)
            if block_date:
                dates.append(block_date)
            
            for pattern, tx_type, category in self.transaction_patterns:
                match = re.search(pattern, block)
                if match:
                    amount_str = match.group(1)
                    name = match.group(2).strip()
                    
                    # Validate amount
                    amount = self.validate_amount(amount_str)
                    if amount is None:
                        continue
                    
                    # Validate phone number if applicable
                    if category == 'airtime' and not self.validate_phone_number(name):
                        logger.warning(f"Invalid phone number in block {i}: {name}")
                        continue
                    
                    transaction = {
                        'type': tx_type,
                        'name': name,
                        'amount': amount,
                        'category': category,
                        'block_index': i,
                        'raw_block': block,
                        'date': block_date
                    }
                    break
            
            if transaction:
                transactions.append(transaction)
            else:
                unmatched_blocks.append(block)
                logger.debug(f"Unmatched block {i}: {block[:100]}...")
        
        # Calculate date range
        date_range = {}
        if dates:
            min_date = min(dates)
            max_date = max(dates)
            date_range = {
                'earliest_date': min_date,
                'latest_date': max_date,
                'date_span_days': (max_date - min_date).days,
                'total_dates_found': len(dates)
            }
            logger.info(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')} ({date_range['date_span_days']} days)")
        else:
            logger.warning("No dates found in transaction data")
        
        logger.info(f"Successfully extracted {len(transactions)} transactions, {len(unmatched_blocks)} unmatched")
        return transactions, unmatched_blocks, date_range

class SAHALAnalyzer:
    """Analyze SAHAL transactions and generate insights."""
    
    def __init__(self, transactions: List[Dict], date_range: Dict = None):
        self.transactions = transactions
        self.date_range = date_range or {}
        self.df = self._create_dataframe()
    
    def _create_dataframe(self) -> pd.DataFrame:
        """Create a comprehensive DataFrame from transactions."""
        if not self.transactions:
            return pd.DataFrame()
        
        data = defaultdict(lambda: {
            'sent': 0.0,
            'received': 0.0,
            'sent_count': 0,
            'received_count': 0,
            'sent_airtime': 0.0,
            'received_airtime': 0.0,
            'sent_person': 0.0,
            'received_person': 0.0,
            'last_transaction': None,
            'transaction_history': []
        })
        
        for tx in self.transactions:
            name = tx['name']
            amount = tx['amount']
            
            if tx['type'] == 'sent':
                data[name]['sent'] += amount
                data[name]['sent_count'] += 1
                if tx['category'] == 'airtime':
                    data[name]['sent_airtime'] += amount
                else:
                    data[name]['sent_person'] += amount
            elif tx['type'] == 'received':
                data[name]['received'] += amount
                data[name]['received_count'] += 1
                if tx['category'] == 'airtime':
                    data[name]['received_airtime'] += amount
                else:
                    data[name]['received_person'] += amount
            
            data[name]['last_transaction'] = tx
            data[name]['transaction_history'].append(tx)
        
        df = pd.DataFrame([
            {
                'Name': name,
                'Sent': round(info['sent'], 2),
                'Received': round(info['received'], 2),
                'Net': round(info['received'] - info['sent'], 2),
                'Sent Count': info['sent_count'],
                'Received Count': info['received_count'],
                'Total Transactions': info['sent_count'] + info['received_count'],
                'Sent Airtime': round(info['sent_airtime'], 2),
                'Sent Person': round(info['sent_person'], 2),
                'Received Airtime': round(info['received_airtime'], 2),
                'Received Person': round(info['received_person'], 2),
                'Last Transaction': info['last_transaction']['raw_block'] if info['last_transaction'] else None
            }
            for name, info in data.items()
        ])
        
        return df
    
    def get_summary_stats(self) -> Dict:
        """Calculate comprehensive summary statistics."""
        if self.df.empty:
            return {}
        
        total_sent = self.df['Sent'].sum()
        total_received = self.df['Received'].sum()
        total_net = self.df['Net'].sum()
        total_transactions = self.df['Total Transactions'].sum()
        
        # Top senders and receivers
        top_senders = self.df.nlargest(10, 'Sent')[['Name', 'Sent', 'Sent Count']]
        top_receivers = self.df.nlargest(10, 'Received')[['Name', 'Received', 'Received Count']]
        
        # People you owe money to (negative net)
        owe_money = self.df[self.df['Net'] < 0].nlargest(10, 'Net')[['Name', 'Net']]
        
        # People who owe you money (positive net)
        owed_money = self.df[self.df['Net'] > 0].nlargest(10, 'Net')[['Name', 'Net']]
        
        # Most active contacts
        most_active = self.df.nlargest(10, 'Total Transactions')[['Name', 'Total Transactions', 'Net']]
        
        stats = {
            'total_sent': total_sent,
            'total_received': total_received,
            'total_net': total_net,
            'total_transactions': total_transactions,
            'top_senders': top_senders,
            'top_receivers': top_receivers,
            'owe_money': owe_money,
            'owed_money': owed_money,
            'most_active': most_active,
            'unique_contacts': len(self.df),
            'avg_transaction_amount': (total_sent + total_received) / total_transactions if total_transactions > 0 else 0
        }
        
        # Add date range information
        if self.date_range:
            stats['date_range'] = self.date_range
        
        return stats
    
    def export_to_csv(self, filename: str = 'sahal_analysis.csv') -> None:
        """Export analysis to CSV file."""
        if not self.df.empty:
            self.df.to_csv(filename, index=False, encoding='utf-8')
            logger.info(f"Analysis exported to {filename}")
    
    def export_to_json(self, filename: str = 'sahal_analysis.json') -> None:
        """Export analysis to JSON file."""
        if not self.df.empty:
            # Convert DataFrame to JSON-serializable format
            summary_stats = self.get_summary_stats()
            
            # Convert pandas DataFrames to lists of dicts for JSON serialization
            json_data = {
                'summary': {
                    'total_sent': float(summary_stats['total_sent']),
                    'total_received': float(summary_stats['total_received']),
                    'total_net': float(summary_stats['total_net']),
                    'total_transactions': int(summary_stats['total_transactions']),
                    'unique_contacts': int(summary_stats['unique_contacts']),
                    'avg_transaction_amount': float(summary_stats['avg_transaction_amount'])
                },
                'transactions': self.df.to_dict('records'),
                'export_date': datetime.now().isoformat()
            }
            
            # Add date range if available
            if 'date_range' in summary_stats:
                date_range = summary_stats['date_range']
                json_data['date_range'] = {
                    'earliest_date': date_range['earliest_date'].isoformat() if date_range['earliest_date'] else None,
                    'latest_date': date_range['latest_date'].isoformat() if date_range['latest_date'] else None,
                    'date_span_days': date_range['date_span_days'],
                    'total_dates_found': date_range['total_dates_found']
                }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis exported to {filename}")

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='SAHAL Transaction Analyzer')
    parser.add_argument('input_file', help='Input SAHAL transaction text file')
    parser.add_argument('--output-csv', default='sahal_analysis.csv', help='Output CSV file')
    parser.add_argument('--output-json', default='sahal_analysis.json', help='Output JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Read input file
        logger.info(f"Reading input file: {args.input_file}")
        with open(args.input_file, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        
        # Parse transactions
        parser = SAHALTransactionParser()
        cleaned_text = parser.clean_input(raw_text)
        transactions, unmatched, date_range = parser.extract_transactions(cleaned_text)
        
        if not transactions:
            logger.error("No transactions found in the input file")
            return 1
        
        # Analyze transactions
        analyzer = SAHALAnalyzer(transactions, date_range)
        stats = analyzer.get_summary_stats()
        
        # Print summary
        print("\n" + "="*50)
        print("SAHAL TRANSACTION ANALYSIS")
        print("="*50)
        print(f"Total Transactions: {stats['total_transactions']:,}")
        print(f"Total Sent: ${stats['total_sent']:,.2f}")
        print(f"Total Received: ${stats['total_received']:,.2f}")
        print(f"Net Balance: ${stats['total_net']:,.2f}")
        print(f"Unique Contacts: {stats['unique_contacts']}")
        print(f"Average Transaction: ${stats['avg_transaction_amount']:.2f}")
        print(f"Unmatched Blocks: {len(unmatched)}")
        
        # Print date range information
        if 'date_range' in stats:
            date_range = stats['date_range']
            print(f"\n📅 DATE RANGE:")
            print(f"   From: {date_range['earliest_date'].strftime('%B %d, %Y')}")
            print(f"   To:   {date_range['latest_date'].strftime('%B %d, %Y')}")
            print(f"   Span: {date_range['date_span_days']} days")
            print(f"   Dates Found: {date_range['total_dates_found']}")
        
        # Export results
        analyzer.export_to_csv(args.output_csv)
        analyzer.export_to_json(args.output_json)
        
        # Print top contacts
        print("\n" + "-"*30)
        print("TOP 5 PEOPLE YOU OWE MONEY TO:")
        print("-"*30)
        for _, row in stats['owe_money'].head().iterrows():
            print(f"{row['Name']}: ${abs(row['Net']):.2f}")
        
        print("\n" + "-"*30)
        print("TOP 5 PEOPLE WHO OWE YOU MONEY:")
        print("-"*30)
        for _, row in stats['owed_money'].head().iterrows():
            print(f"{row['Name']}: ${row['Net']:.2f}")
        
        return 0
        
    except FileNotFoundError:
        logger.error(f"Input file not found: {args.input_file}")
        return 1
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 