# Tariff Modelling Application - API Integration Update

## 🎉 What's New

This version integrates with the **Avalara Global Compliance API** to provide real, accurate duty calculations instead of mock data.

### Key Features:
- ✅ Real-time duty calculations via Avalara API
- ✅ Dynamic duty rows based on actual API responses
- ✅ Support for multiple duty types (MFN, ADD, CVD, Section 232, etc.)
- ✅ Automatic handling of varying duty structures per country
- ✅ API response debugging for troubleshooting
- ✅ Loading states and user-friendly error messages
- ✅ Flexible vendor comparison (1-6 vendors)

---

## 📋 Setup Instructions

### 1. Environment Variables

Create a `.env` file in the project root with your Avalara API credentials:

```env
AVALARA_USERNAME=your_username_here
AVALARA_PASSWORD=your_password_here
AVALARA_COMPANY_ID=your_company_id_here
```

**Note:** Use the same credentials as your existing Avalara quotes method.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python app.py
```

Access at: `http://localhost:5000`

---

## 🔧 How It Works

### API Integration Flow

1. **User fills in vendor data** (Vendor Country, COO, COGS)
2. **Click RUN button**
3. **For each complete vendor:**
   - Application calls Avalara Global Compliance API
   - API endpoint: `POST /api/v2/companies/{COMPANY_ID}/globalcompliance`
   - Request includes: HS Code, COO, Vendor Country, Cost, Quantity, Product Description
4. **API returns `dutyGranularity` array** with duty types and rates
5. **Application parses duties** and displays them dynamically
6. **Results shown** with proper alignment across vendors

### API Request Structure

```json
{
    "companyId": 112244,
    "currency": "usd",
    "b2b": true,
    "shipFrom": {
        "country": "TH"
    },
    "destinations": [{
        "shipTo": {
            "country": "us",
            "region": "ca",
            "postalCode": "20240"
        }
    }],
    "lines": [{
        "lineNumber": 1,
        "quantity": 100,
        "item": {
            "itemCode": "TARIFF-CALC-001",
            "description": "Product description",
            "classifications": [{
                "country": "US",
                "hscode": "7317006530"
            }],
            "classificationParameters": [{
                "name": "price",
                "value": "100.50",
                "unit": "usd"
            }, {
                "name": "coo",
                "value": "TH"
            }],
            "parameters": [{
                "name": "SHIPPING",
                "value": "0",
                "unit": "usd"
            }]
        }
    }],
    "type": "QUOTE_MAXIMUM"
}
```

### API Response Parsing

The application extracts duties from the `dutyGranularity` array:

```json
"dutyGranularity": [
    {
        "description": "MFN Duty",
        "rate": "0.095",
        "type": "MFN"
    },
    {
        "description": "ADD Duty",
        "rate": "0.0188",
        "type": "ADD"
    },
    {
        "description": "SECTION 232 STEEL",
        "rate": "0.5",
        "type": "PUNITIVE"
    }
]
```

Each duty is displayed as a separate row with:
- **Label**: `description` field (e.g., "MFN Duty")
- **Rate**: `rate * 100` as percentage (e.g., 9.5%)
- **N/A**: Shown if duty type doesn't apply to a specific vendor

---

## 🎨 Dynamic Duty Display

### Example Output

**Vendor 1 (Thailand → US)**
- MFN Duty: 9.50%
- ADD Duty: 1.88%
- SECTION 232 STEEL: 50.00%
- **Total Duty Rate: 61.38%**
- **Total Duty: $6,138.00**

**Vendor 2 (China → US)**
- MFN Duty: 0.00%
- ADD Duty: 13.00%
- SECTION 301 TARIFF: 25.00%
- SECTION 232 STEEL: N/A
- **Total Duty Rate: 38.00%**
- **Total Duty: $3,800.00**

### How Alignment Works

The application ensures all vendors show the same duty types:
1. Collects all unique duty types from all vendor responses
2. Creates labels for each duty type
3. For each vendor:
   - Shows actual rate if duty applies
   - Shows "N/A" if duty doesn't apply
4. Maintains consistent row order across all vendors

---

## 🐛 Debugging

### API Response Viewing

Click **"Toggle API Debug Responses"** button to view:
- Raw API requests sent to Avalara
- Complete API responses received
- Error messages and stack traces
- Per-vendor calculation details

### Debug Section Shows:

```
Vendor 1: Thai Supplier - Success
{
  "globalCompliance": [...],
  "dutyGranularity": [...],
  ...full API response...
}

Vendor 2: Chinese Supplier - Failed
{
  "error": "Connection timeout",
  ...error details...
}
```

### Common Issues

**"Calculation failed" message:**
- Check debug section for detailed error
- Verify API credentials in `.env`
- Ensure COMPANY_ID is correct
- Check network connectivity

**Empty duty results:**
- API may return no duties for certain country combinations
- Check if HS Code is valid
- Verify COO and destination country

**N/A showing for all duties:**
- Vendor may have no applicable duties
- Check API response in debug section

---

## 📊 Calculation Details

### Total Duty Rate
Sum of all applicable duty rates:
```
Total Duty Rate = MFN + ADD + CVD + Section 232 + Section 301 + ...
```

### Total Duty Amount
```
Total Duty = Quantity × COGS × (Total Duty Rate / 100)
```

Example:
- Quantity: 100
- COGS: $100
- Total Duty Rate: 61.38%
- Total Duty: 100 × 100 × 0.6138 = **$6,138.00**

---

## 🔄 Changes from Previous Version

### Removed Mock Calculations
- ❌ Baseline Tariff % (mock)
- ❌ Reciprocal % (mock)
- ❌ Chapter 301 % (mock)
- ❌ IEEPA % or SPI % (mock)

### Added Real API Integration
- ✅ Dynamic duty types from API
- ✅ MFN Duty (Most Favored Nation)
- ✅ ADD/CVD (Anti-dumping/Countervailing duties)
- ✅ Section 232 (Steel/Aluminum tariffs)
- ✅ Section 301 (China tariffs)
- ✅ Other punitive/preferential duties
- ✅ Accurate rate calculations
- ✅ Real-time data

### UI Improvements
- ✅ Dynamic row generation
- ✅ Proper duty type alignment across vendors
- ✅ Loading states during API calls
- ✅ User-friendly error messages
- ✅ Detailed API debugging

---

## 📁 Project Structure

```
tariff-modelling/
├── app.py                      # Flask backend with API integration
├── templates/
│   └── index.html             # Frontend with dynamic duty rendering
├── requirements.txt            # Python dependencies
├── .env                        # Your API credentials (create this)
├── .env.example               # Example environment variables
└── README.md                  # This file
```

---

## 🚀 Usage Guide

### Step 1: Enter Product Details
- Import Date
- Product Description (auto-fills HS Code)
- HS Code

### Step 2: Enter Order Details
- Order Quantity (auto-fills to all vendors)
- Incoterm
- SPI Applicable (optional)

### Step 3: Fill Vendor Data
For each vendor you want to compare:
- Vendor Country (auto-fills to COO)
- Country of Origin
- COGS per unit

**Note:** Use 1-6 vendors as needed. Empty vendors are skipped automatically.

### Step 4: Calculate
- Click **RUN** button
- Wait for calculations (shows "Calculating..." for each vendor)
- Review results across vendors
- Check debug section if needed

### Step 5: Compare Results
- Different duty types shown per vendor
- Total Duty Rate and Amount calculated
- Vendors with lowest/highest duties visible

---

## 🔐 Security Notes

- **Never commit `.env` file** to version control
- Keep API credentials secure
- Use `.env.example` as template only
- API credentials are same as Quotes method

---

## 📞 Support

### If calculations fail:
1. Check debug section for API response
2. Verify `.env` credentials
3. Ensure network connectivity
4. Review API endpoint URL

### If duties seem incorrect:
1. Verify HS Code is correct
2. Check Country of Origin
3. Review API response in debug section
4. Compare with Avalara's online tools

---

## ✨ Key Benefits

### Real Data
- Accurate duty calculations from Avalara
- Up-to-date tariff rates
- Comprehensive duty type coverage

### Flexible
- Handles varying duty structures
- Adapts to different countries
- Shows N/A for non-applicable duties

### Transparent
- View complete API responses
- Debug issues easily
- Understand calculation details

### User-Friendly
- Clean, aligned display
- Loading indicators
- Clear error messages

---

## 🎯 Next Steps

Suggested enhancements:
- Add currency conversion support
- Include freight cost estimates
- Save vendor comparisons
- Export results to Excel/PDF
- Historical rate tracking
- Batch calculations

---

**Ready to use!** Set up your `.env` file and start comparing tariffs across vendors with real Avalara data.