import re
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import logging
from datetime import datetime, timedelta
import io
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
                'date': block_date,
                'raw_block': block
            }
        
        # Pattern 2: Sent airtime to phone number
        elif m := re.search(r"Waxaad \$([\d.]+) ugu shubtay (\d{9,})", block):
            transaction = {
                'type': 'sent', 
                'name': m.group(2), 
                'amount': float(m.group(1)),
                'category': 'airtime',
                'date': block_date,
                'raw_block': block
            }
        
        # Pattern 3: Received money from person
        elif m := re.search(r"Waxaad \$([\d.]+) ka heshay (.+?)\(", block):
            transaction = {
                'type': 'received', 
                'name': m.group(2).strip(), 
                'amount': float(m.group(1)),
                'category': 'person',
                'date': block_date,
                'raw_block': block
            }
        
        # Pattern 4: Received airtime from phone number
        elif m := re.search(r"You have received airtime of \$([\d.]+) from (\d{9,})", block):
            transaction = {
                'type': 'received', 
                'name': m.group(2), 
                'amount': float(m.group(1)),
                'category': 'airtime',
                'date': block_date,
                'raw_block': block
            }
        
        # Pattern 5: Business transactions (Kusoo dhawaaw)
        elif m := re.search(r"Kusoo dhawaaw\s+(.+?)\s+Tixraac:\s+\d+,\s+\$([\d.]+)\s+ayaad u dirtay", block):
            transaction = {
                'type': 'sent', 
                'name': m.group(1).strip(), 
                'amount': float(m.group(2)),
                'category': 'business',
                'date': block_date,
                'raw_block': block
            }
        
        # Pattern 6: Alternative business transaction format
        elif m := re.search(r"Kusoo dhawaaw\s+(.+?)\s+\d+\s+Tixraac:\s+\d+,\s+\$([\d.]+)\s+ayaad u dirtay", block):
            transaction = {
                'type': 'sent', 
                'name': m.group(1).strip(), 
                'amount': float(m.group(2)),
                'category': 'business',
                'date': block_date,
                'raw_block': block
            }
        
        # Pattern 7: Business transactions with different spacing
        elif m := re.search(r"Kusoo dhawaaw\s+(.+?)\s+Tixraac:\s+\d+,\s+\$([\d.]+)\s+ayaad u dirtay", block, re.DOTALL):
            transaction = {
                'type': 'sent', 
                'name': m.group(1).strip(), 
                'amount': float(m.group(2)),
                'category': 'business',
                'date': block_date,
                'raw_block': block
            }
        
        # Pattern 8: Business transactions with phone numbers
        elif m := re.search(r"Kusoo dhawaaw\s+(.+?)\s+\d{9,}\s+Tixraac:\s+\d+,\s+\$([\d.]+)\s+ayaad u dirtay", block):
            transaction = {
                'type': 'sent', 
                'name': m.group(1).strip(), 
                'amount': float(m.group(2)),
                'category': 'business',
                'date': block_date,
                'raw_block': block
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

def process_csv_upload(uploaded_file):
    """Process uploaded CSV file and convert to transaction format."""
    try:
        df = pd.read_csv(uploaded_file)
        
        # Check if it's already in the right format
        if 'Name' in df.columns and 'Sent' in df.columns and 'Received' in df.columns:
            return df
        
        # Try to convert from raw transaction format
        transactions = []
        for _, row in df.iterrows():
            if 'type' in row and 'name' in row and 'amount' in row:
                transaction = {
                    'type': row['type'],
                    'name': row['name'],
                    'amount': float(row['amount']),
                    'category': row.get('category', 'unknown'),
                    'date': pd.to_datetime(row.get('date', datetime.now())),
                    'raw_block': row.get('raw_block', '')
                }
                transactions.append(transaction)
        
        if transactions:
            return group_transactions(transactions)
        else:
            st.error("CSV format not recognized. Please upload a SAHAL text file or properly formatted CSV.")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error processing CSV: {str(e)}")
        return pd.DataFrame()

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

# ========== EXPORT FUNCTIONS ==========
def generate_pdf_report(df, stats, date_range=None):
    """Generate PDF report of the analysis."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Title
    elements.append(Paragraph("SAHAL Transaction Analysis Report", title_style))
    elements.append(Spacer(1, 20))
    
    # Summary Statistics
    elements.append(Paragraph("Summary Statistics", styles['Heading2']))
    summary_data = [
        ['Metric', 'Value'],
        ['Total Sent', f"${stats['total_sent']:,.2f}"],
        ['Total Received', f"${stats['total_received']:,.2f}"],
        ['Net Balance', f"${stats['total_net']:,.2f}"],
        ['Total Transactions', f"{stats['total_transactions']:,}"],
        ['Unique Contacts', f"{len(df)}"]
    ]
    
    if date_range:
        summary_data.extend([
            ['Date Range', f"{date_range['earliest_date'].strftime('%B %d, %Y')} - {date_range['latest_date'].strftime('%B %d, %Y')}"],
            ['Span', f"{date_range['date_span_days']} days"]
        ])
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Top Transactions Table
    elements.append(Paragraph("Top Transactions by Net Amount", styles['Heading2']))
    top_transactions = df.nlargest(10, 'Net')[['Name', 'Sent', 'Received', 'Net']]
    top_data = [['Name', 'Sent', 'Received', 'Net']]
    for _, row in top_transactions.iterrows():
        top_data.append([
            row['Name'][:30],  # Truncate long names
            f"${row['Sent']:.2f}",
            f"${row['Received']:.2f}",
            f"${row['Net']:.2f}"
        ])
    
    top_table = Table(top_data)
    top_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    elements.append(top_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def get_download_link(data, filename, text):
    """Generate download link for files."""
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

# ========== STREAMLIT UI ==========
def main():
    st.set_page_config(
        page_title="SAHAL Money Tracker", 
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="collapsed"  # Mobile-friendly: collapsed sidebar
    )
    
    # Custom CSS for mobile optimization
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stDataFrame {
            font-size: 12px;
        }
        .stMetric {
            font-size: 14px;
        }
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("💰 SAHAL Money Transfer Tracker")
    st.markdown("---")
    
    # File upload section with both text and CSV support
    st.subheader("📁 Upload Your Data")
    
    upload_option = st.radio(
        "Choose upload type:",
        ["SAHAL Text File", "CSV File", "RAW Data"],
        horizontal=True
    )
    
    uploaded = None
    pasted_csv = None
    if upload_option == "SAHAL Text File":
        uploaded = st.file_uploader(
            "Upload your SAHAL transaction text file", 
            type="txt",
            help="Upload the text file containing your SAHAL transaction history"
        )
    elif upload_option == "CSV File":
        uploaded = st.file_uploader(
            "Upload your CSV file", 
            type="csv",
            help="Upload a CSV file with transaction data"
        )
    elif upload_option == "RAW Data":
        # Initialize or increment the key counter in session state
        if 'raw_data_key_counter' not in st.session_state:
            st.session_state.raw_data_key_counter = 0
        
        with st.form("raw_data_form"):
            pasted_csv = st.text_area(
                "Paste your RAW Data here:",
                height=300,
                placeholder="Name,Sent,Received,Net\nAxmed Maxamed,10.00,0.00,10.00\nFadumo Cali,0.00,5.00,5.00\nCabdirahman Yusuf,2.50,1.25,1.25\nHodan Warsame,0.00,3.00,3.00\n1234567,5.00,0.00,5.00\n252900011122,0.00,7.00,7.00",
                key=f"raw_data_input_{st.session_state.raw_data_key_counter}"
            )
            submit_button = st.form_submit_button("Process Data")
        
        # Process data from session state if available
        if 'pending_raw_data' in st.session_state and st.session_state.pending_raw_data:
            data_to_process = st.session_state.pending_raw_data
            st.session_state.pending_raw_data = ""  # Clear the pending data
            
            st.info("📝 Processing raw SAHAL text data...")
            cleaned = clean_input(data_to_process)
            transactions, unmatched, date_range = extract_transactions(cleaned)
            if transactions:
                df = group_transactions(transactions)
                st.success(f"✅ Successfully parsed {len(transactions)} transactions from raw text!")
                with st.expander("📋 Preview of Parsed Data"):
                    st.dataframe(df.head(10), use_container_width=True)
                if unmatched:
                    with st.expander(f"❓ Unmatched Blocks ({len(unmatched)})"):
                        for i, block in enumerate(unmatched[:5], 1):
                            st.text(f"Block {i}: {block[:100]}...")
                        if len(unmatched) > 5:
                            st.info(f"... and {len(unmatched) - 5} more unmatched blocks")
            else:
                st.error("❌ No transactions found in the pasted text. Please check the format.")
                return
        
        # Handle new form submission
        elif submit_button and pasted_csv and pasted_csv.strip():
            # Store the data in session state before clearing
            st.session_state.pending_raw_data = pasted_csv
            # Increment the key counter to force the field to clear on next render
            st.session_state.raw_data_key_counter += 1
            st.rerun()

    if uploaded or (pasted_csv and pasted_csv.strip()):
        try:
            if upload_option == "SAHAL Text File":
                raw_text = uploaded.read().decode("utf-8")
                cleaned = clean_input(raw_text)
                transactions, unmatched, date_range = extract_transactions(cleaned)
                if not transactions:
                    st.error("❌ No transactions found in the uploaded file. Please check the file format.")
                    return
                df = group_transactions(transactions)
            elif upload_option == "CSV File":
                df = process_csv_upload(uploaded)
                date_range = None
                unmatched = []
            elif upload_option == "RAW Data":
                # The parsing is already done above, just use the results
                if 'df' not in locals():
                    st.error("❌ Error processing pasted text. Please try again.")
                    return
                # df, date_range, and unmatched are already set above
                pass
            
            if df.empty:
                st.error("❌ No valid data found in the uploaded file.")
                return
            
            # Calculate stats for the data
            stats = calculate_summary_stats(df, date_range)
            
            # Display summary metrics in mobile-friendly layout
            st.markdown("---")
            st.subheader("📊 Summary Statistics")
            
            # Use columns for better mobile layout
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💸 Total Sent", f"${stats['total_sent']:,.2f}")
            with col2:
                st.metric("💰 Total Received", f"${stats['total_received']:,.2f}")
            with col3:
                st.metric("⚖️ Net Balance", f"${stats['total_net']:,.2f}", 
                         delta=f"{stats['total_net']:+.2f}")
            with col4:
                st.metric("📊 Transactions", f"{stats['total_transactions']:,}")
            
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
            
            # Export section
            st.markdown("---")
            st.subheader("📤 Export Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # CSV Export
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv,
                    file_name=f"sahal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # JSON Export
                json_data = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📋 Download JSON",
                    data=json_data,
                    file_name=f"sahal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            with col3:
                # PDF Export
                if st.button("📑 Generate PDF Report"):
                    pdf_buffer = generate_pdf_report(df, stats, date_range)
                    st.download_button(
                        label="📑 Download PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"sahal_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
            
            st.markdown("---")
            
            # Main content tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Transactions", 
                "📈 Charts", 
                "👥 People",
                "🔍 Raw Data",
                "❓ Unmatched"
            ])
            
            with tab1:
                st.subheader("📋 Transaction Summary")
                st.dataframe(
                    df.sort_values(by="Net", ascending=False), 
                    use_container_width=True,
                    hide_index=True
                )
            
            with tab2:
                # Use Plotly for better mobile charts
                if not df.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("💸 Top 10 Money Sent")
                        top_sent = df.nlargest(10, 'Sent')
                        fig_sent = px.bar(
                            top_sent, 
                            x='Name', 
                            y='Sent',
                            title="Top 10 Money Sent"
                        )
                        fig_sent.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig_sent, use_container_width=True)
                    
                    with col2:
                        st.subheader("💰 Top 10 Money Received")
                        top_received = df.nlargest(10, 'Received')
                        fig_received = px.bar(
                            top_received, 
                            x='Name', 
                            y='Received',
                            title="Top 10 Money Received"
                        )
                        fig_received.update_layout(xaxis_tickangle=-45, height=400)
                        st.plotly_chart(fig_received, use_container_width=True)
                    
                    # Pie chart for overall sent vs received
                    st.subheader("🔄 Overall Sent vs Received")
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=['Sent', 'Received'],
                        values=[stats['total_sent'], stats['total_received']],
                        hole=0.3
                    )])
                    fig_pie.update_layout(height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)
            
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
                st.subheader("🔍 Raw Transaction Data")
                if 'transactions' in locals():
                    raw_df = pd.DataFrame(transactions)
                    st.dataframe(raw_df, use_container_width=True)
                else:
                    st.info("Raw transaction data not available for CSV uploads.")
            
            with tab5:
                if unmatched:
                    st.subheader("❓ Unmatched Transaction Blocks")
                    st.warning(f"Found {len(unmatched)} transaction blocks that couldn't be parsed:")
                    for i, block in enumerate(unmatched[:5], 1):  # Show first 5 on mobile
                        with st.expander(f"Block {i}"):
                            st.text(block)
                    if len(unmatched) > 5:
                        st.info(f"... and {len(unmatched) - 5} more unmatched blocks")
                else:
                    st.success("✅ All transactions were successfully parsed!")
            
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            logger.error(f"Error processing uploaded file: {e}")
    
    else:
        st.info("👆 Please upload a SAHAL transaction file or CSV to get started.")
        
        # Show sample format
        with st.expander("📝 Expected File Format"):
            st.markdown("""
            **SAHAL Text File Format:**
            ```
            [SAHAL]
            $50.00 ayaad u dirtay John Doe(
            
            [SAHAL]
            Waxaad $25.00 ka heshay Jane Smith(
            ```
            
            **CSV File Format:**
            ```
            Name,Sent,Received,Net,Sent Count,Received Count
            John Doe,50.00,0.00,-50.00,1,0
            Jane Smith,0.00,25.00,25.00,0,1
            ```
            """)

if __name__ == "__main__":
    main()
