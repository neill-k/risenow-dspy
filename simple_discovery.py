"""Simple vendor discovery script using the main runner."""

import sys
from typing import Optional

from config.environment import validate_environment
from main import run

def main(category: str = "General Industrial Supplies", 
         n: int = 15, 
         country_or_region: Optional[str] = "United States"):
    """
    Simple entry point for vendor discovery.
    
    Uses the main.run function which includes GEPA optimization.
    """
    print(f"Starting vendor discovery for {category}...")
    print(f"Finding {n} vendors" + (f" in {country_or_region}" if country_or_region else "") + "...")
    
    try:
        # Run vendor discovery via main.run
        result = run(category=category, n=n, country_or_region=country_or_region)
        
        print(f"\n✅ Vendor discovery completed!")
        print(f"Found {len(result.vendor_list)} vendors:\n")
        
        # Display results in a concise format
        for i, vendor in enumerate(result.vendor_list, 1):
            print(f"{i:2d}. {vendor.name}")
            print(f"    Website: {vendor.website}")
            if vendor.contact_emails:
                print(f"    Email: {vendor.contact_emails[0].email}")
            if vendor.countries_served:
                print(f"    Countries: {', '.join(vendor.countries_served[:3])}" + 
                      (f" + {len(vendor.countries_served)-3} more" if len(vendor.countries_served) > 3 else ""))
            print()
        
        return result
        
    except Exception as e:
        print(f"❌ Error during vendor discovery: {e}")
        raise


if __name__ == "__main__":
    # Very simple CLI handling - could be expanded with argparse if needed
    if len(sys.argv) > 1:
        category = sys.argv[1]
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
        country = sys.argv[3] if len(sys.argv) > 3 else "United States"
        main(category, n, country)
    else:
        main()  # Use defaults
