import re
import csv
from collections import defaultdict

def clean_input(text):
    # Strip out date lines like "Tuesday, September 3, 2024 · 7:55 PM"
    return re.sub(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), .*?\d{4} · \d{1,2}:\d{2}(?:\u202F|\s)?(?:AM|PM)', '', text)

def extract_transactions(text):
    blocks = [b.strip() for b in text.split('[SAHAL]') if b.strip()]
    transactions = []

    for block in blocks:
        block = block.strip()

        # Match: Sent money
        match_sent = re.search(r"\$ ?([\d.]+) ayaad u dirtay (.+?)\(", block)
        if match_sent:
            amount = float(match_sent.group(1))
            name = match_sent.group(2).strip()
            transactions.append({'type': 'sent', 'name': name, 'amount': amount})
            continue

        # Match: Sent airtime
        match_airtime_sent = re.search(r"Waxaad \$([\d.]+) ugu shubtay (\d{9,})", block)
        if match_airtime_sent:
            amount = float(match_airtime_sent.group(1))
            name = match_airtime_sent.group(2)
            transactions.append({'type': 'sent', 'name': name, 'amount': amount})
            continue

        # Match: Received money
        match_received_money = re.search(r"Waxaad \$([\d.]+) ka heshay (.+?)\(", block)
        if match_received_money:
            amount = float(match_received_money.group(1))
            name = match_received_money.group(2).strip()
            transactions.append({'type': 'received', 'name': name, 'amount': amount})
            continue

        # Match: Received airtime
        match_airtime_received = re.search(r"You have received airtime of \$([\d.]+) from (\d{9,})", block)
        if match_airtime_received:
            amount = float(match_airtime_received.group(1))
            name = match_airtime_received.group(2)
            transactions.append({'type': 'received', 'name': name, 'amount': amount})
            continue

    return transactions

def group_by_name(transactions):
    grouped = defaultdict(lambda: {'sent_total': 0.0, 'received_total': 0.0, 'sent_count': 0, 'received_count': 0})

    for tx in transactions:
        name = tx['name']
        if tx['type'] == 'sent':
            grouped[name]['sent_total'] += tx['amount']
            grouped[name]['sent_count'] += 1
        elif tx['type'] == 'received':
            grouped[name]['received_total'] += tx['amount']
            grouped[name]['received_count'] += 1

    return grouped

def export_to_csv(grouped_data, filename='grouped_by_name.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Sent Total', 'Received Total', 'Sent Count', 'Received Count'])
        for name, stats in sorted(grouped_data.items(), key=lambda x: x[0].lower()):
            writer.writerow([
                name,
                f"${stats['sent_total']:.2f}",
                f"${stats['received_total']:.2f}",
                stats['sent_count'],
                stats['received_count']
            ])

def main():
    with open('transactions.txt', 'r', encoding='utf-8') as f:
        raw_text = f.read()

    cleaned = clean_input(raw_text)
    transactions = extract_transactions(cleaned)
    grouped = group_by_name(transactions)
    export_to_csv(grouped)

    print(f"Processed {len(transactions)} transactions.")
    print(f"Grouped data saved to grouped_by_name.csv")

if __name__ == "__main__":
    main()
