from scripts.pipeline_step_tester import vendor_markdown
from models.vendor import Vendor, ContactEmail, PhoneNumber

vendor = Vendor(
    name="TestCo",
    website="https://example.com",
    description="desc",
    justification="Great choice",
    contact_emails=[ContactEmail(email="info@example.com", description="Support")],
    phone_numbers=[PhoneNumber(number="+1234567890", description="Sales")],
    countries_served=["US", "CA"],
)
print(vendor_markdown("Test", "North America", [vendor]))
