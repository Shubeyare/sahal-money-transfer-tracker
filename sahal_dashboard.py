import re
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== DATA PARSING ==========
def clean_input(text):
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

def parse_date_from_text(text):
    """Parse date from text using multiple patterns."""
    if not text:
        return None
    
    # Pattern 1: "Tuesday, October 17, 2023 · 11:17 AM"
    pattern1 = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4}) · (\d{1,2}):(\d{2})(?:\u202F|\s)?(AM|PM)'
    match1 = re.search(pattern1, text)
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
        except (ValueError, KeyError):
            pass
    
    # Pattern 2: "Tar: 17/10/23 13:35:59"
    pattern2 = r'Tar: (\d{1,2})/(\d{1,2})/(\d{2}) (\d{1,2}):(\d{2}):(\d{2})'
    match2 = re.search(pattern2, text)
    if match2:
        try:
            day, month, year, hour, minute, second = match2.groups()
            full_year = 2000 + int(year)
            return datetime(full_year, int(month), int(day), int(hour), int(minute), int(second))
        except ValueError:
            pass
    
    return None

def extract_transactions(text):
    """Extract transactions from SAHAL text with improved regex patterns and date extraction."""
    if not text:
        return [], []
    
    blocks = [b.strip() for b in text.split('[SAHAL]') if b.strip()]
    transactions = []
    unmatched_blocks = []
    dates = []

    for block in blocks:
        block = block.strip()
        transaction = None
        
        # Extract date from block
        block_date = parse_date_from_text(block)
        if block_date:
            dates.append(block_date)

        # Pattern 1: Sent money to person
        if m := re.search(r"\$ ?([\d.]+) ayaad u dirtay (.+?)\(", block):
            transaction = {
                'type': 'sent', 
                'name': m.group(2).strip(), 
                'amount': float(m.group(1)),
                'category': 'person',
                'date': block_date
            }
        
        # Pattern 2: Sent airtime to phone number
        elif m := re.search(r"Waxaad \$([\d.]+) ugu shubtay (\d{9,})", block):
            transaction = {
                'type': 'sent', 
                'name': m.group(2), 
                'amount': float(m.group(1)),
                'category': 'airtime',
                'date': block_date
            }
        
        # Pattern 3: Received money from person
        elif m := re.search(r"Waxaad \$([\d.]+) ka heshay (.+?)\(", block):
            transaction = {
                'type': 'received', 
                'name': m.group(2).strip(), 
                'amount': float(m.group(1)),
                'category': 'person',
                'date': block_date
            }
        
        # Pattern 4: Received airtime from phone number
        elif m := re.search(r"You have received airtime of \$([\d.]+) from (\d{9,})", block):
            transaction = {
                'type': 'received', 
                'name': m.group(2), 
                'amount': float(m.group(1)),
                'category': 'airtime',
                'date': block_date
            }

        if transaction:
            transactions.append(transaction)
        else:
            unmatched_blocks.append(block)

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

    logger.info(f"Extracted {len(transactions)} transactions, {len(unmatched_blocks)} unmatched blocks")
    return transactions, unmatched_blocks, date_range

# ========== DASHBOARD LOGIC ==========
def group_transactions(transactions):
    """Group transactions by name with enhanced statistics."""
    if not transactions:
        return pd.DataFrame()
    
    data = defaultdict(lambda: {
        'sent': 0, 
        'received': 0, 
        'sent_count': 0, 
        'received_count': 0,
        'sent_airtime': 0,
        'received_airtime': 0,
        'sent_person': 0,
        'received_person': 0
    })
    
    for tx in transactions:
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
    
    df = pd.DataFrame([
        {
            'Name': name, 
            'Sent': round(info['sent'], 2), 
            'Received': round(info['received'], 2),
            'Net': round(info['received'] - info['sent'], 2),
            'Sent Count': info['sent_count'],
            'Received Count': info['received_count'],
            'Sent Airtime': round(info['sent_airtime'], 2),
            'Sent Person': round(info['sent_person'], 2),
            'Received Airtime': round(info['received_airtime'], 2),
            'Received Person': round(info['received_person'], 2)
        }
        for name, info in data.items()
    ])
    
    return df

def calculate_summary_stats(df, date_range=None):
    """Calculate summary statistics for the dashboard."""
    if df.empty:
        return {}
    
    total_sent = df['Sent'].sum()
    total_received = df['Received'].sum()
    total_net = df['Net'].sum()
    total_transactions = df['Sent Count'].sum() + df['Received Count'].sum()
    
    # Top senders and receivers
    top_senders = df.nlargest(5, 'Sent')[['Name', 'Sent']]
    top_receivers = df.nlargest(5, 'Received')[['Name', 'Received']]
    
    # People you owe money to (negative net)
    owe_money = df[df['Net'] < 0].nlargest(5, 'Net')[['Name', 'Net']]
    
    # People who owe you money (positive net)
    owed_money = df[df['Net'] > 0].nlargest(5, 'Net')[['Name', 'Net']]
    
    stats = {
        'total_sent': total_sent,
        'total_received': total_received,
        'total_net': total_net,
        'total_transactions': total_transactions,
        'top_senders': top_senders,
        'top_receivers': top_receivers,
        'owe_money': owe_money,
        'owed_money': owed_money
    }
    
    # Add date range information
    if date_range:
        stats['date_range'] = date_range
    
    return stats

# ========== STREAMLIT UI ==========
def main():
    st.set_page_config(
        page_title="SAHAL Money Tracker", 
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("💰 SAHAL Money Transfer Tracker")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.header("📊 Dashboard Options")
    show_raw_data = st.sidebar.checkbox("Show Raw Transaction Data", value=False)
    show_unmatched = st.sidebar.checkbox("Show Unmatched Transactions", value=False)
    
    # File upload
    uploaded = st.file_uploader(
        "📁 Upload your SAHAL transaction text file", 
        type="txt",
        help="Upload the text file containing your SAHAL transaction history"
    )

    if uploaded:
        try:
            # Read and process file
            raw_text = uploaded.read().decode("utf-8")
            cleaned = clean_input(raw_text)
            transactions, unmatched, date_range = extract_transactions(cleaned)
            
            if not transactions:
                st.error("❌ No transactions found in the uploaded file. Please check the file format.")
                return
            
            # Process transactions
            df = group_transactions(transactions)
            stats = calculate_summary_stats(df, date_range)
            
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💸 Total Sent", f"${stats['total_sent']:,.2f}")
            with col2:
                st.metric("💰 Total Received", f"${stats['total_received']:,.2f}")
            with col3:
                st.metric("⚖️ Net Balance", f"${stats['total_net']:,.2f}", 
                         delta=f"{stats['total_net']:+.2f}")
            with col4:
                st.metric("📊 Total Transactions", f"{stats['total_transactions']:,}")
            
            # Display date range information
            if 'date_range' in stats:
                date_range = stats['date_range']
                st.markdown("---")
                st.subheader("📅 Transaction Date Range")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📅 From", date_range['earliest_date'].strftime('%B %d, %Y'))
                with col2:
                    st.metric("📅 To", date_range['latest_date'].strftime('%B %d, %Y'))
                with col3:
                    st.metric("📊 Span", f"{date_range['date_span_days']} days")
                with col4:
                    st.metric("📈 Dates Found", f"{date_range['total_dates_found']}")
            
            st.markdown("---")
            
            # Main content tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Transaction Summary", 
                "📈 Charts & Analytics", 
                "👥 People Analysis",
                "🔍 Raw Data",
                "❓ Unmatched"
            ])
            
            with tab1:
                st.subheader("📋 Complete Transaction Summary")
                st.dataframe(
                    df.sort_values(by="Net", ascending=False), 
                    use_container_width=True,
                    hide_index=True
                )
            
            with tab2:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("💸 Top 10 Money Sent")
                    if not df.empty:
                        top_sent = df.nlargest(10, 'Sent')[['Name', 'Sent']]
                        st.bar_chart(top_sent.set_index('Name')['Sent'])
                
                with col2:
                    st.subheader("💰 Top 10 Money Received")
                    if not df.empty:
                        top_received = df.nlargest(10, 'Received')[['Name', 'Received']]
                        st.bar_chart(top_received.set_index('Name')['Received'])
                
                # Pie chart for overall sent vs received
                st.subheader("🔄 Overall Sent vs Received")
                if stats['total_sent'] > 0 or stats['total_received'] > 0:
                    fig, ax = plt.subplots(figsize=(8, 6))
                    labels = ['Sent', 'Received']
                    sizes = [stats['total_sent'], stats['total_received']]
                    colors = ['#ff6b6b', '#4ecdc4']
                    
                    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')
                    st.pyplot(fig)
            
            with tab3:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("💳 People You Owe Money To")
                    if not stats['owe_money'].empty:
                        st.dataframe(stats['owe_money'], use_container_width=True, hide_index=True)
                    else:
                        st.info("✅ You don't owe money to anyone!")
                
                with col2:
                    st.subheader("💵 People Who Owe You Money")
                    if not stats['owed_money'].empty:
                        st.dataframe(stats['owed_money'], use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ No one owes you money.")
            
            with tab4:
                if show_raw_data:
                    st.subheader("🔍 Raw Transaction Data")
                    raw_df = pd.DataFrame(transactions)
                    st.dataframe(raw_df, use_container_width=True)
                else:
                    st.info("Enable 'Show Raw Transaction Data' in the sidebar to view detailed transaction information.")
            
            with tab5:
                if show_unmatched and unmatched:
                    st.subheader("❓ Unmatched Transaction Blocks")
                    st.warning(f"Found {len(unmatched)} transaction blocks that couldn't be parsed:")
                    for i, block in enumerate(unmatched[:10], 1):  # Show first 10
                        st.text_area(f"Block {i}", block, height=100)
                    if len(unmatched) > 10:
                        st.info(f"... and {len(unmatched) - 10} more unmatched blocks")
                elif unmatched:
                    st.info(f"Found {len(unmatched)} unmatched transaction blocks. Enable 'Show Unmatched Transactions' in the sidebar to view them.")
                else:
                    st.success("✅ All transactions were successfully parsed!")
            
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            logger.error(f"Error processing uploaded file: {e}")
    
    else:
        st.info("👆 Please upload a SAHAL transaction text file to get started.")
        
        # Show sample format
        with st.expander("📝 Expected File Format"):
            st.markdown("""
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
            """)

if __name__ == "__main__":
    main()
