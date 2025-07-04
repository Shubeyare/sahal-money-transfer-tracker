import re
import csv
import sys

def clean_input(raw_data):
    # Remove lines like "Monday, September 2, 2024 · 10:55 PM"
    cleaned = re.sub(
        r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), .*?\d{4} · \d{1,2}:\d{2}(?:\u202F|\s)?(?:AM|PM)',
        '',
        raw_data
    )
    return cleaned

def parse_transactions(raw_data):
    transactions = [tx.strip() for tx in raw_data.split("[SAHAL]") if tx.strip()]

    results = []
    unmatched = []

    for tx in transactions:
        # Sent money (either to user or shop)
        sent = re.search(r"\$\s*([\d.]+)\s*(ayaad u dirtay|ugu shubtay)", tx)
        if sent:
            amount = float(sent.group(1))
            results.append({
                "type": "sent",
                "amount": amount,
                "raw": tx
            })
            continue

        # Received airtime
        received = re.search(r"You have received airtime of \$(\d+\.?\d*)", tx)
        if received:
            amount = float(received.group(1))
            results.append({
                "type": "received",
                "amount": amount,
                "raw": tx
            })
            continue

        unmatched.append(tx)

    return results, unmatched

def summarize(results):
    total_sent = sum(r['amount'] for r in results if r['type'] == 'sent')
    total_received = sum(r['amount'] for r in results if r['type'] == 'received')
    count = len(results)
    return total_sent, total_received, count

def export_csv(results, filename):
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['type', 'amount', 'raw'])
        writer.writeheader()
        for r in results:
            writer.writerow(r)

def export_unmatched(unmatched, filename):
    with open(filename, mode='w', encoding='utf-8') as f:
        for line in unmatched:
            f.write(line + "\n\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: python transaction_parser.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = f.read()

    cleaned_data = clean_input(raw_data)
    results, unmatched = parse_transactions(cleaned_data)
    total_sent, total_received, count = summarize(results)

    print(f"Total transactions parsed: {count}")
    print(f"Total sent (money out): ${total_sent:.2f}")
    print(f"Total received (airtime in): ${total_received:.2f}")
    print(f"Unmatched transaction count: {len(unmatched)}")

    export_csv(results, 'parsed_transactions.csv')
    export_unmatched(unmatched, 'unmatched_transactions.txt')

    print("Parsed transactions exported to parsed_transactions.csv")
    print("Unmatched transactions exported to unmatched_transactions.txt")

if __name__ == "__main__":
    main()
