# CiviSenti WhatsApp Community Flood Reporting Setup

CiviSenti allows community members to report flooding through WhatsApp. The chatbot receives incoming WhatsApp-style messages, converts them into structured flood reports, validates the report content, checks available NFCC rainfall/risk evidence, and stores the report for admin review.

## Files Added

- `src/chatbot/whatsapp_bot.py`  
  Handles WhatsApp-style incoming payloads and converts them into structured community flood reports.

- `scripts/civisenti_handler.py`  
  Processes incoming reports, validates report quality, checks available rainfall/risk evidence, stores reports, and generates summary output.

- `.github/workflows/civisenti.yml`  
  Runs scheduled CiviSenti validation and uploads report outputs as workflow artifacts.

- `docs/civisenti_setup.md`  
  Explains configuration, testing, and usage.

## WhatsApp Reporting Flow

1. A community member sends a WhatsApp message about flooding.
2. The WhatsApp/Twilio webhook payload is passed to the CiviSenti bot.
3. The bot extracts:
   - reporter phone number
   - message text
   - location text
   - GPS latitude and longitude
   - photo/media metadata
   - estimated severity
4. The handler validates the report.
5. The handler checks available rainfall/risk data from the NFCC processed dataset.
6. The report is stored in `data/community_reports/reports.jsonl`.
7. The dashboard/admin workflow can review stored reports.

## Expected WhatsApp Message Example

```text
Flooding at Kaneshie. Water is high and the road is blocked.