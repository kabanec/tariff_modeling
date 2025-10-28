from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import random
import requests
import os
from dotenv import load_dotenv
import logging
import uuid

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

VALID_USER = os.getenv("AUTH_USER", "admin")
VALID_PASS = os.getenv("AUTH_PASS", "password")

def auth_required():
    request_id = str(uuid.uuid4())
    auth = request.authorization
    logger.debug(f"[{request_id}] Authorization header: {auth}")
    if not auth:
        logger.error(f"[{request_id}] No authorization header provided")
        return Response('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
    if auth.username != VALID_USER or auth.password != VALID_PASS:
        logger.error(f"[{request_id}] Invalid credentials: username={auth.username}, expected={VALID_USER}")
        return Response('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
    logger.debug(f"[{request_id}] Authentication successful")
    return None

load_dotenv()

app = Flask(__name__)
CORS(app)

# Avalara API Configuration
AVALARA_TOKEN = os.getenv('AVALARA_TOKEN')
AVALARA_COMPANY_ID = os.getenv('AVALARA_COMPANY_ID')
AVALARA_API_BASE = 'https://ns1-quoting-sbx.xbo.avalara.com/api/v2'

# ISO-2 Country codes
COUNTRIES = [
    "US", "CN", "CA", "MX", "GB", "DE", "FR", "IT", "ES", "JP",
    "KR", "IN", "BR", "AU", "RU", "VN", "TH", "MY", "ID", "PH",
    "Not Specified"
]

# Mock HS Code data
HS_CODES = {
    "8517.62.00": {"description": "Machines for reception, conversion of voice, image", "baseline_rate": 0.0},
    "6109.10.00": {"description": "T-shirts, cotton", "baseline_rate": 16.5},
    "8471.30.01": {"description": "Portable computers", "baseline_rate": 0.0},
    "9503.00.00": {"description": "Tricycles, scooters, pedal cars, toys", "baseline_rate": 0.0},
    "8528.72.64": {"description": "Reception apparatus for TV", "baseline_rate": 5.0},
}


def get_avalara_auth_header():
    """Generate Basic Auth header for Avalara API using token from .env"""
    return f"Basic {AVALARA_TOKEN}"


def call_global_compliance_api(hs_code, coo, vendor_country, cost_per_unit, quantity, description, import_country,
                               spi_applicable):
    """
    Call Avalara Global Compliance API for real duty calculations

    Args:
        hs_code: Harmonized System code
        coo: Country of Origin
        vendor_country: Vendor's country (ship from)
        cost_per_unit: Cost per unit in USD
        quantity: Quantity of goods
        description: Product description
        import_country: Import destination country (default US)
        spi_applicable: Whether SPI is applicable (True/False)

    Returns:
        Dictionary with API response and parsed duty data
    """
    try:
        url = f"{AVALARA_API_BASE}/companies/{AVALARA_COMPANY_ID}/globalcompliance"

        headers = {
            'Content-Type': 'application/json',
            'Authorization': get_avalara_auth_header()
        }

        # Build request payload matching exact Avalara format
        payload = {
            "id": "TARIFF-MODEL-001",
            "companyId": int(AVALARA_COMPANY_ID),
            "currency": "usd",
            "sellerCode": "SELLER-001",
            "b2b": True,
            "shipFrom": {
                "country": vendor_country
            },
            "destinations": [{
                "shipTo": {
                    "country": import_country.lower(),
                    "region": "ca"
                },
                "parameters": [],
                "taxRegistered": False
            }],
            "lines": [{
                "lineNumber": 1,
                "quantity": quantity,
                "preferenceProgramApplicable": spi_applicable,
                "item": {
                    "itemCode": 11,
                    "description": description,
                    "classifications": [{
                        "country": import_country.upper(),
                        "hscode": hs_code.replace(".", "").replace(" ", "")
                    }],
                    "classificationParameters": [{
                        "name": "price",
                        "value": str(cost_per_unit),
                        "unit": "usd"
                    }, {
                        "name": "coo",
                        "value": coo
                    }],
                    "parameters": [{
                        "name": "weight",
                        "value": "0",
                        "unit": "lb"
                    }, {
                        "name": "SHIPPING",
                        "value": "0.00",
                        "unit": "usd"
                    }]
                },
                "classificationParameters": []
            }],
            "type": "QUOTE_MAXIMUM",
            "disableCalculationSummary": False,
            "restrictionsCheck": False,
            "program": "Regular"
        }

        # Make API call
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        api_response = response.json()

        # Parse dutyGranularity from response
        duty_lines = []
        total_duty_rate = 0.0

        if 'globalCompliance' in api_response and len(api_response['globalCompliance']) > 0:
            quote = api_response['globalCompliance'][0].get('quote', {})
            lines = quote.get('lines', [])

            if len(lines) > 0:
                calculation_summary = lines[0].get('calculationSummary', {})
                duty_granularity = calculation_summary.get('dutyGranularity', [])

                # Extract each duty type
                for duty in duty_granularity:
                    description_text = duty.get('description', 'Unknown Duty')
                    rate = float(duty.get('rate', 0))
                    rate_percent = rate * 100
                    duty_type = duty.get('type', '')

                    duty_lines.append({
                        'description': description_text,
                        'rate': rate,
                        'rate_percent': rate_percent,
                        'type': duty_type
                    })

                    # Sum up total duty rate
                    total_duty_rate += rate

        # Calculate total duty amount
        total_duty_amount = quantity * cost_per_unit * total_duty_rate

        return {
            'success': True,
            'duty_lines': duty_lines,
            'total_duty_rate': total_duty_rate,
            'total_duty_rate_percent': total_duty_rate * 100,
            'total_duty_amount': total_duty_amount,
            'api_response': api_response,
            'request_payload': payload  # Include request for debugging
        }

    except requests.exceptions.RequestException as e:
        # Capture more detailed error information
        error_details = str(e)
        response_text = None
        if hasattr(e, 'response') and e.response is not None:
            try:
                response_text = e.response.json()
            except:
                response_text = e.response.text

        return {
            'success': False,
            'error': error_details,
            'error_response': response_text,
            'api_response': None,
            'request_payload': payload if 'payload' in locals() else None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'api_response': None,
            'request_payload': payload if 'payload' in locals() else None
        }


def calculate_tariff(hs_code, coo, vendor_country, cost_per_unit, quantity, calculation_method="standard"):
    """
    Calculate tariff for a single vendor

    Args:
        hs_code: Harmonized System code
        coo: Country of Origin
        vendor_country: Vendor's country
        cost_per_unit: Cost per unit in USD
        quantity: Quantity of goods
        calculation_method: "standard" or "preferential"

    Returns:
        Dictionary with calculation results
    """

    # Get baseline tariff
    hs_info = HS_CODES.get(hs_code, {"baseline_rate": 0.0})
    baseline_tariff = hs_info.get("baseline_rate", 0.0)

    # Calculate other tariff components
    reciprocal_tariff = 0.0
    chapter_301_tariff = 0.0
    ieepa_tariff = 0.0
    spi_tariff = 0.0

    # Reciprocal tariff logic (example: applies to certain countries)
    if coo in ["CN", "MX", "CA"]:
        reciprocal_tariff = random.uniform(0, 5)

    # Chapter 301 tariff (China specific)
    if coo == "CN":
        chapter_301_tariff = random.uniform(7.5, 25)

    # IEEPA or SPI depending on calculation method
    if calculation_method == "preferential":
        # SPI (Special Preferential Initiative) for preferential calculation
        if coo in ["MX", "CA", "VN"]:
            spi_tariff = random.uniform(0, 10)
    else:
        # IEEPA (International Emergency Economic Powers Act)
        if coo in ["CN", "RU"]:
            ieepa_tariff = random.uniform(10, 25)

    # Calculate total tariff
    total_tariff_rate = baseline_tariff + reciprocal_tariff + chapter_301_tariff

    if calculation_method == "preferential":
        total_tariff_rate += spi_tariff
    else:
        total_tariff_rate += ieepa_tariff

    # Check for de minimis
    customs_value = cost_per_unit * quantity
    duty_deminimis_applied = False

    # US de minimis threshold is $800
    if customs_value < 800:
        duty_deminimis_applied = True
        duty_amount = 0.0
        effective_tariff_rate = 0.0
    else:
        duty_amount = customs_value * (total_tariff_rate / 100)
        effective_tariff_rate = total_tariff_rate

    # Calculate total cost
    total_cost = customs_value + duty_amount

    # Build response
    result = {
        "vendor_country": vendor_country,
        "country_of_origin": coo,
        "cost_per_unit": cost_per_unit,
        "quantity": quantity,
        "customs_value": customs_value,
        "baseline_tariff_rate": baseline_tariff,
        "reciprocal_tariff_rate": reciprocal_tariff,
        "chapter_301_tariff_rate": chapter_301_tariff,
        "total_tariff_rate": effective_tariff_rate,
        "duty_amount": duty_amount,
        "total_cost": total_cost,
        "dutyCalculationSummary": [
            {"name": "DUTY_DEMINIMIS_APPLIED", "value": str(duty_deminimis_applied).lower()}
        ]
    }

    # Add either IEEPA or SPI depending on calculation method
    if calculation_method == "preferential":
        result["spi_tariff_rate"] = spi_tariff
    else:
        result["ieepa_tariff_rate"] = ieepa_tariff

    return result


@app.route('/')
def index():
    """Serve the main application page"""
    auth_error = auth_required()
    if auth_error:
        return auth_error
    auth = request.authorization

    countries = [{'code': c, 'name': c, 'flag': '🌍'} for c in COUNTRIES]
    incoterms = ['FCA', 'FOB', 'CIF', 'DDP']
    vendors_form = [{'id': i, 'name': '', 'country': '', 'coo': '', 'cost': '', 'quantity': ''} for i in range(1, 7)]
    return render_template('index.html', countries=countries, incoterms=incoterms, vendors_form=vendors_form,
                           form_data={})



@app.route('/classify_hs', methods=['POST'])
def classify_hs():
    """Classify HS Code based on product description"""
    data = request.json
    description = data.get('description', '').lower()

    # Simple keyword matching for demo
    hs_code = None
    for code, info in HS_CODES.items():
        if any(word in description for word in info['description'].lower().split()):
            hs_code = code
            break

    if not hs_code:
        # Default to first code if no match
        hs_code = list(HS_CODES.keys())[0]

    return jsonify({
        'hs_code': hs_code,
        'description': HS_CODES[hs_code]['description']
    })


@app.route('/calculate_vendor', methods=['POST'])
def calculate_vendor():
    """Calculate tariff for a single vendor using Avalara Global Compliance API"""
    data = request.json

    description = data.get('description', '')
    hs_code = data.get('hs_code', '').replace('.', '')
    coo = data.get('coo')
    vendor_country = coo  # Default ship from = COO
    cost = float(data.get('cost', 0))
    quantity = int(data.get('quantity', 1))
    import_country = data.get('import_country', 'US')
    spi_applicable = data.get('spi_applicable', False)

    # Call Avalara Global Compliance API
    result = call_global_compliance_api(
        hs_code=hs_code,
        coo=coo,
        vendor_country=vendor_country,
        cost_per_unit=cost,
        quantity=quantity,
        description=description,
        import_country=import_country,
        spi_applicable=spi_applicable
    )

    if result['success']:
        # Return structured data for dynamic duty rows
        return jsonify({
            'success': True,
            'duty_lines': result['duty_lines'],
            'total_duty_rate': f"{result['total_duty_rate_percent']:.2f}%",
            'total_duty_amount': result['total_duty_amount'],
            'api_response': result['api_response'],
            'request_payload': result.get('request_payload')
        })
    else:
        # Return error with API response for debug
        return jsonify({
            'success': False,
            'error': result['error'],
            'error_response': result.get('error_response'),
            'api_response': result.get('api_response'),
            'request_payload': result.get('request_payload')
        }), 500


@app.route('/api/countries', methods=['GET'])
def get_countries():
    """Return list of country codes"""
    return jsonify({"countries": COUNTRIES})


@app.route('/api/hs-codes', methods=['GET'])
def get_hs_codes():
    """Return list of HS codes"""
    return jsonify({"hs_codes": list(HS_CODES.keys())})


@app.route('/api/hs-code/<code>', methods=['GET'])
def get_hs_code_info(code):
    """Return info for specific HS code"""
    info = HS_CODES.get(code)
    if info:
        return jsonify({"hs_code": code, **info})
    else:
        return jsonify({"error": "HS Code not found"}), 404


@app.route('/api/calculate', methods=['POST'])
def calculate():
    """
    Calculate tariff for a single vendor

    Expected JSON body:
    {
        "hs_code": "8517.62.00",
        "country_of_origin": "CN",
        "vendor_country": "CN",
        "cost_per_unit": 100.50,
        "quantity": 1000,
        "calculation_method": "standard"  // or "preferential"
    }
    """
    try:
        data = request.json

        # Validate required fields
        required_fields = ['hs_code', 'country_of_origin', 'cost_per_unit', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate COO is not "Not Specified"
        if data['country_of_origin'] == 'Not Specified':
            return jsonify({"error": "Country of Origin cannot be 'Not Specified' for calculations"}), 400

        # Validate cost > 0
        if data['cost_per_unit'] <= 0:
            return jsonify({"error": "Cost per unit must be greater than 0"}), 400

        # Validate quantity > 0
        if data['quantity'] <= 0:
            return jsonify({"error": "Quantity must be greater than 0"}), 400

        # Get calculation method (default to standard)
        calculation_method = data.get('calculation_method', 'standard')

        # Perform calculation
        result = calculate_tariff(
            hs_code=data['hs_code'],
            coo=data['country_of_origin'],
            vendor_country=data.get('vendor_country', data['country_of_origin']),
            cost_per_unit=data['cost_per_unit'],
            quantity=data['quantity'],
            calculation_method=calculation_method
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)