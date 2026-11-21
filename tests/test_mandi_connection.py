
from services.mandi_service import fetch_mandi_prices


print("=" * 55)
print("AGROVISION - MANDI API CONNECTION TEST")
print("=" * 55)

try:
    print("\nConnecting to Government of India API...")

    result = fetch_mandi_prices(limit=5)

    print("\nAPI CONNECTION SUCCESSFUL!")
    print("Total available records:", result["total_records"])
    print("Records retrieved:", result["count"])

    print("\nSAMPLE REAL MARKET DATA")
    print("-" * 55)

    for record in result["records"]:
        print(
            f"State: {record.get('state')}\n"
            f"District: {record.get('district')}\n"
            f"Market: {record.get('market')}\n"
            f"Commodity: {record.get('commodity')}\n"
            f"Arrival Date: {record.get('arrival_date')}\n"
            f"Minimum Price: {record.get('min_price')}\n"
            f"Maximum Price: {record.get('max_price')}\n"
            f"Modal Price: {record.get('modal_price')}\n"
        )
        print("-" * 55)

except Exception as error:
    print("\nAPI CONNECTION FAILED!")
    print("Reason:", error)
