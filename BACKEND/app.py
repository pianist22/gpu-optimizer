import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from cachetools import cached, TTLCache
import re
import math  # For potential scaling in scoring
import traceback  # For logging scoring errors
import uuid  # For generating unique IDs for fallback GPUs

# --- Configuration ---
STATIC_DATA_PATH = os.environ.get("STATIC_DATA_PATH", "gpu_static_specs_and_suitability_v2.json")
ACECLOUD_API_BASE_URL = os.environ.get("ACECLOUD_API_BASE_URL", "https://customer.acecloudhosting.com/api/v1/pricing?is_gpu=true&resource=instances")
API_CACHE_TTL_SECONDS = int(os.environ.get("API_CACHE_TTL_SECONDS", 300))
FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
# Scoring normalization constants
MAX_PRICE_MONTHLY = float(os.environ.get("MAX_PRICE_MONTHLY", 20000.0))
MAX_TFLOPS = float(os.environ.get("MAX_TFLOPS", 100.0))
MAX_BANDWIDTH_GBPS = float(os.environ.get("MAX_BANDWIDTH_GBPS", 3000.0))
DEFAULT_FAILURE_SCORE = -999.0  # Score assigned if heuristic calculation fails

# --- Global Variables ---
static_gpu_lookup = {}  # Lookup for static enrichment data by normalized name
MODEL_SCALE_MAP = {
    "gpt-3.5": "Large", "gpt-3.5-turbo": "Large",
    "claude": "Large", "claude-2": "Large", "claude-3-opus": "XLarge",
    "sonnet": "Medium", "claude-3-sonnet": "Medium",
    "gemini pro": "Large", "gemini-pro": "Large",
    "mistral-7b": "Medium",
    "llama-2": "Large", "llama-2-7b": "Medium", "llama-2-13b": "Medium", "llama-2-70b": "Large",
}
MODEL_VRAM_ESTIMATES_GB = {
    "Small": 8, "Medium": 20, "Large": 40, "XLarge": 80
}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def normalize_gpu_name(name_input):
    """Normalizes various GPU name formats into a consistent key."""
    if not name_input or not isinstance(name_input, str):
        return "unknown"

    name = name_input.lower()
    # Pre-emptive common substitutions
    name = name.replace("nvidia ", "").replace("(", "").replace(")", "")
    name = name.replace("-", "").replace("_", "")
    name = re.sub(r'\s+', '', name)  # Remove spaces early

    # Handle specific common cases (order might matter)
    if "h100" in name:
        if "sxm" in name: return "h100_sxm"
        if "nvl" in name: return "h100_nvl"
        if "pcie" in name or "80gb" in name: return "h100_pcie"
        return "h100_unknown"
    if "a100" in name:
        if "80gb" in name: return "a100_80gb"
        if "40gb" in name: return "a100_40gb"
        return "a100_unknown"
    if "a6000" in name or "rtxa6000" in name: return "a6000"
    if "l40s" in name: return "l40s"
    if "a40" in name: return "a40"
    if "a30" in name: return "a30"
    if "a10g" in name: return "a10g"
    if "a10" in name: return "a10"
    if "a2" in name: return "a2"
    if "l4" in name: return "l4"
    if "rtx8000" in name: return "rtx8000"
    if "rtx6000ada" in name: return "rtx6000ada"
    if "rtx5000" in name: return "rtx5000"
    if "rtx4000" in name: return "rtx4000"
    if "rtx3090" in name: return "rtx3090"

    # Basic fallback cleanup
    cleaned_name = name.replace("1x", "").replace("gb", "")
    if cleaned_name != name and name != "unknown":  # Log if fallback cleanup changed the name
        logging.debug(f"GPU name '{name_input}' normalized using fallback cleanup to '{cleaned_name}'")
        name = cleaned_name

    return name if name else "unknown"


def load_static_gpu_data():
    """Loads the static GPU specs and suitability data for enrichment."""
    global static_gpu_lookup
    static_gpu_lookup = {}
    if not os.path.exists(STATIC_DATA_PATH):
        logging.error(f"Static GPU data file not found: {STATIC_DATA_PATH}")
        return False

    try:
        with open(STATIC_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict) or "data" not in data or not isinstance(data["data"], list):
            logging.error(f"Invalid format or missing 'data' key in static GPU data file: {STATIC_DATA_PATH}")
            return False

        loaded_count = 0
        for gpu_spec in data["data"]:
            if not isinstance(gpu_spec, dict):
                logging.warning(f"Skipping non-dictionary item in static data: {gpu_spec}")
                continue
            gpu_model_name = gpu_spec.get("gpu_model")
            if not gpu_model_name:
                logging.warning(f"Skipping static GPU entry with missing 'gpu_model': {gpu_spec}")
                continue
            normalized_name = normalize_gpu_name(gpu_model_name)
            if normalized_name != "unknown":
                # --- Validation & Type Conversion ---
                mem_val = gpu_spec.get('memory_size_gb')
                try: gpu_spec['memory_size_gb'] = int(mem_val) if mem_val is not None else 0
                except (ValueError, TypeError): gpu_spec['memory_size_gb'] = 0
                tflops_val = gpu_spec.get('fp32_tflops')
                try: gpu_spec['fp32_tflops'] = float(tflops_val) if tflops_val is not None else 0.0
                except (ValueError, TypeError): gpu_spec['fp32_tflops'] = 0.0
                bw_val = gpu_spec.get('bandwidth')
                bw_gbps = 0.0
                if isinstance(bw_val, (int, float)): bw_gbps = float(bw_val)
                elif isinstance(bw_val, str):
                    bw_str = bw_val.lower().replace(" ", "")
                    try:
                        if "tb/s" in bw_str: bw_gbps = float(bw_str.replace("tb/s", "")) * 1000
                        elif "gb/s" in bw_str: bw_gbps = float(bw_str.replace("gb/s", ""))
                        else: bw_gbps = float(bw_str)
                    except (ValueError, TypeError): pass
                gpu_spec['bandwidth_gbps'] = bw_gbps

                if normalized_name in static_gpu_lookup:
                    logging.warning(f"Duplicate normalized name '{normalized_name}' found in static data. Overwriting.")
                static_gpu_lookup[normalized_name] = gpu_spec
                loaded_count += 1
            else:
                logging.warning(f"Could not normalize static GPU entry: {gpu_model_name}")

        logging.info(f"Loaded {loaded_count} static GPU specs for enrichment from {STATIC_DATA_PATH}. Lookup size: {len(static_gpu_lookup)}")
        return True
    except Exception as e:
        logging.exception(f"Unexpected error loading static GPU data: {e}")
        return False


# Cache for API responses
api_cache = TTLCache(maxsize=20, ttl=API_CACHE_TTL_SECONDS)

@cached(api_cache)
def fetch_live_gpu_data(region=None):
    """Fetches live GPU pricing and availability from AceCloud API, optionally filtered by region."""
    target_url = ACECLOUD_API_BASE_URL
    params = {}
    region_log_str = "all regions"
    if region and region.lower() != "any":
        params['region'] = region
        region_log_str = f"region '{region}'"

    logging.info(f"Fetching live data from AceCloud API ({region_log_str})... URL: {target_url}, Params: {params}")
    try:
        response = requests.get(target_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            logging.info(f"Successfully fetched {len(data['data'])} live GPU instances for {region_log_str}.")
            return data["data"]
        elif isinstance(data, dict) and data.get("error") is True:
            logging.error(f"API error for {region_log_str}: {data.get('message', 'Unknown API error')}")
            return None
        elif isinstance(data, dict) and "data" in data and data["data"] is None:
            logging.info(f"API returned 'data: null' for {region_log_str}. Treating as empty list.")
            return []
        else:
            logging.error(f"Live API response format unexpected for {region_log_str}. Response: {data}")
            return None
    except requests.exceptions.Timeout:
        logging.error(f"Timeout fetching live GPU data for {region_log_str} from {target_url}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error fetching live GPU data for {region_log_str}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON response from live API for {region_log_str}.")
        return None
    except Exception as e:
        logging.exception(f"Unexpected error during live API fetch for {region_log_str}: {e}")
        return None


def process_live_gpu_data(live_gpus):
    """
    Processes live GPU data, enriches with static specs IF available,
    and ensures each GPU instance is unique based on key attributes.
    """
    if live_gpus is None:
        logging.error("Cannot process GPU data because live_gpus input was None.")
        return []
    if not live_gpus:
        logging.info("No live GPU data provided to process_live_gpu_data.")
        return []

    processed_list = []
    processed_keys = set()  # To track unique GPU instances

    logging.info(f"Processing {len(live_gpus)} raw live GPU entries...")
    for live_gpu in live_gpus:
        if not isinstance(live_gpu, dict):
            logging.warning(f"Skipping non-dictionary item in live_gpus list: {live_gpu}")
            continue

        # --- Start with Live Data ---
        processed_gpu = live_gpu.copy()  # Base is the live data

        # Determine the best name source and normalize
        live_name_source = processed_gpu.get('gpu_description') or processed_gpu.get('resource_class') or 'Unknown Live GPU'
        normalized_name = normalize_gpu_name(live_name_source)
        processed_gpu['normalized_name'] = normalized_name  # Store for reference
        processed_gpu['gpu_model_live'] = live_name_source  # Store original live name

        # --- Create Unique Key for Deduplication ---
        # Use a tuple of key attributes to identify unique GPU instances
        live_key_tuple = (
            processed_gpu.get('region', 'N/A').lower(),
            normalized_name,
            processed_gpu.get('vcpus', 0),
            processed_gpu.get('ram', 0),
            processed_gpu.get('price_per_hour_float', None),
            processed_gpu.get('price_per_month_float', None)
        )
        if live_key_tuple in processed_keys:
            logging.debug(f"Skipping duplicate live GPU entry: {live_name_source} (Key: {live_key_tuple})")
            continue
        processed_keys.add(live_key_tuple)

        # --- Attempt Enrichment with Static Data ---
        static_specs = static_gpu_lookup.get(normalized_name)
        if static_specs:
            processed_gpu['has_static_specs'] = True
            # Add enrichment fields from static data, preferring static values
            processed_gpu['gpu_model'] = static_specs.get('gpu_model', live_name_source)
            processed_gpu['memory_size_gb'] = static_specs.get('memory_size_gb', 0)
            processed_gpu['fp32_tflops'] = static_specs.get('fp32_tflops', 0.0)
            processed_gpu['bandwidth_gbps'] = static_specs.get('bandwidth_gbps', 0.0)
            processed_gpu['model_scale_suitability'] = static_specs.get('model_scale_suitability', ["Unknown"])
            processed_gpu['primary_task_suitability'] = static_specs.get('primary_task_suitability', "Unknown")
            processed_gpu['use_case'] = static_specs.get('use_case', "Unknown")
            logging.debug(f"Enriched '{live_name_source}' (normalized: '{normalized_name}') with static specs.")
        else:
            # Set defaults for enrichment fields if no static match
            processed_gpu['has_static_specs'] = False
            processed_gpu['gpu_model'] = live_name_source
            processed_gpu['memory_size_gb'] = 0
            processed_gpu['fp32_tflops'] = 0.0
            processed_gpu['bandwidth_gbps'] = 0.0
            processed_gpu['model_scale_suitability'] = ["Unknown"]
            processed_gpu['primary_task_suitability'] = "Unknown"
            processed_gpu['use_case'] = "Unknown"
            if normalized_name != "unknown":
                logging.warning(f"No static specs found for enrichment: '{live_name_source}' (normalized: '{normalized_name}')")
            else:
                logging.debug(f"Could not normalize or find static specs for enrichment: '{live_name_source}'")

        # --- Ensure Core Live Fields & Types ---
        processed_gpu['region'] = processed_gpu.get('region', 'N/A')
        try:
            processed_gpu['vcpus'] = int(processed_gpu['vcpus']) if processed_gpu.get('vcpus') is not None else 0
        except (ValueError, TypeError): processed_gpu['vcpus'] = 0
        try:
            processed_gpu['ram'] = int(processed_gpu['ram']) if processed_gpu.get('ram') is not None else 0
        except (ValueError, TypeError): processed_gpu['ram'] = 0

        # --- Process Prices and Availability ---
        price_hr = processed_gpu.get('price_per_hour')
        price_mo = processed_gpu.get('price_per_month')
        price_sp = processed_gpu.get('price_per_spot')
        phr_float, pmo_float, psp_float = None, None, None
        is_available_priced = False
        try:
            phr_clean = price_hr if price_hr not in [None, "", "N/A"] else None
            pmo_clean = price_mo if price_mo not in [None, "", "N/A"] else None
            psp_clean = price_sp if price_sp not in [None, "", "N/A"] else None
            phr_float = float(phr_clean) if phr_clean is not None else None
            pmo_float = float(pmo_clean) if pmo_clean is not None else None
            psp_float = float(psp_clean) if psp_clean is not None else None
            is_available_priced = (phr_float is not None and phr_float > 0) or \
                                  (pmo_float is not None and pmo_float > 0)
        except (ValueError, TypeError) as e:
            logging.warning(f"Price conversion error for {processed_gpu.get('gpu_model')}: {e}. Prices: hr={price_hr}, mo={price_mo}")
            is_available_priced = False

        processed_gpu['price_per_hour_float'] = phr_float
        processed_gpu['price_per_month_float'] = pmo_float
        processed_gpu['price_per_spot_float'] = psp_float
        processed_gpu['is_available'] = is_available_priced
        processed_gpu['is_requestable'] = not is_available_priced
        processed_gpu['currency'] = processed_gpu.get('currency', 'N/A')

        # Ensure memory_size_gb is integer
        if not isinstance(processed_gpu.get('memory_size_gb'), int):
            processed_gpu['memory_size_gb'] = 0

        processed_list.append(processed_gpu)

    logging.info(f"Processed {len(processed_list)} unique live GPU entries after deduplication.")
    return processed_list


def generate_fallback_recommendations(required_scale, task_type, min_vram_required, existing_keys):
    """
    Generates fallback GPU recommendations from static data, ensuring no duplicates with existing processed GPUs.
    """
    fallback_gpus = []
    logging.info("Generating fallback recommendations from static GPU data...")

    # Select up to 3 GPUs from static data, prioritizing suitability
    candidate_gpus = list(static_gpu_lookup.values())
    if not candidate_gpus:
        logging.warning("No static GPU data available for fallback recommendations.")
        return []

    # Sort candidates by suitability for task and scale
    sorted_candidates = sorted(
        candidate_gpus,
        key=lambda x: (
            required_scale in x.get('model_scale_suitability', []),
            x.get('primary_task_suitability', 'Unknown') in [task_type, 'Balanced'],
            x.get('memory_size_gb', 0) >= min_vram_required,
            x.get('fp32_tflops', 0.0)
        ),
        reverse=True
    )

    # Take top 3 or fewer, ensuring no duplicates with existing_keys
    selected_count = 0
    for static_gpu in sorted_candidates:
        if selected_count >= 3:
            break
        normalized_name = normalize_gpu_name(static_gpu.get('gpu_model', 'Unknown GPU'))
        # Create a key for the fallback GPU
        fallback_key = (
            'N/A (Static Fallback)'.lower(),
            normalized_name,
            16,  # Default vCPUs
            64,  # Default RAM
            1.0 + selected_count * 0.5,  # Default price per hour
            (1.0 + selected_count * 0.5) * 730  # Default price per month
        )
        if fallback_key in existing_keys:
            logging.debug(f"Skipping duplicate fallback GPU: {static_gpu.get('gpu_model')} (Key: {fallback_key})")
            continue

        # Create fallback GPU entry
        fallback_gpu = {
            'gpu_model': static_gpu.get('gpu_model', 'Fallback GPU'),
            'gpu_model_live': static_gpu.get('gpu_model', 'Fallback GPU'),
            'normalized_name': normalized_name,
            'has_static_specs': True,
            'memory_size_gb': static_gpu.get('memory_size_gb', 0),
            'fp32_tflops': static_gpu.get('fp32_tflops', 0.0),
            'bandwidth_gbps': static_gpu.get('bandwidth_gbps', 0.0),
            'model_scale_suitability': static_gpu.get('model_scale_suitability', ["Unknown"]),
            'primary_task_suitability': static_gpu.get('primary_task_suitability', "Unknown"),
            'use_case': static_gpu.get('use_case', "Unknown"),
            'region': 'N/A (Static Fallback)',
            'vcpus': 16,
            'ram': 64,
            'price_per_hour_float': 1.0 + selected_count * 0.5,
            'price_per_month_float': (1.0 + selected_count * 0.5) * 730,
            'price_per_spot_float': None,
            'is_available': False,
            'is_requestable': True,
            'currency': 'USD',
            'resource_id': f"fallback-{uuid.uuid4()}",
            'message': 'This is a fallback recommendation based on static GPU data.'
        }
        fallback_gpus.append(fallback_gpu)
        existing_keys.add(fallback_key)
        selected_count += 1

    logging.info(f"Generated {len(fallback_gpus)} unique fallback GPU recommendations.")
    return fallback_gpus


# --- Flask App Setup ---
app = Flask(__name__)
CORS(app)

# --- API Endpoints ---
@app.route('/')
def home():
    return "GPU Recommender Backend (Heuristic + Live API v5 - Live First with Fallbacks and Deduplication)"


@app.route('/recommend', methods=['POST'])
def recommend_gpu_v5():
    """
    Recommends GPUs based on live data, enriched by static specs, with fallbacks.
    Ensures unique GPU instances and non-empty recommendations.
    """
    # 1. Get User Input & Validate
    payload = request.get_json() if request.data else {}
    if not isinstance(payload, dict): payload = {}

    model_type = str(payload.get('modelType', '')).lower().strip()
    task_type = str(payload.get('taskType', 'Training')).strip()
    preferred_region = str(payload.get('preferredRegion', '')).strip().lower()
    if not preferred_region: preferred_region = 'any'

    dataset_size_gb = 0
    try:
        ds_val = payload.get('datasetSizeGB')
        if ds_val not in [None, '']: dataset_size_gb = int(ds_val)
        if dataset_size_gb < 0: dataset_size_gb = 0
    except (ValueError, TypeError): dataset_size_gb = 0

    budget_monthly = None
    try:
        b_val = payload.get('budget')
        if b_val not in [None, '']: budget_monthly = float(b_val)
        if budget_monthly is not None and budget_monthly < 0: budget_monthly = None
    except (ValueError, TypeError): budget_monthly = None

    if task_type not in ['Training', 'Inference']: task_type = 'Training'

    logging.info(f"Recommend V5 Request: Model='{model_type or 'Default (Medium)'}', Dataset={dataset_size_gb}GB, Task={task_type}, Budget={budget_monthly or 'None'}, Region={preferred_region}")

    # 2. Calculate VRAM Requirement
    required_scale = MODEL_SCALE_MAP.get(model_type) if model_type else "Medium"
    if not MODEL_SCALE_MAP.get(model_type) and model_type:
        logging.warning(f"Model type '{model_type}' not found. Defaulting requirement to Medium scale.")
    estimated_model_vram = MODEL_VRAM_ESTIMATES_GB.get(required_scale, 20)
    min_vram_required = max(dataset_size_gb, estimated_model_vram) * 1.2

    # 3. Fetch Live Data
    region_to_fetch = preferred_region if preferred_region != "any" else None
    live_gpus_raw = fetch_live_gpu_data(region=region_to_fetch)

    if live_gpus_raw is None:
        logging.warning(f"Initial fetch/cache lookup failed for region '{region_to_fetch}'. Attempting non-cached refetch...")
        live_gpus_raw = fetch_live_gpu_data._wrapped_(region=region_to_fetch)
        if live_gpus_raw is None:
            logging.error("Refetch also failed. Falling back to static data.")
            live_gpus_raw = []

    # 4. Process Live Data with Deduplication
    processed_gpus = process_live_gpu_data(live_gpus_raw)

    # 5. Apply Post-Processing Region Filter
    gpus_to_score = []
    processed_keys = set()  # Track unique keys for deduplication across live and fallback
    for gpu in processed_gpus:
        key = (
            gpu.get('region', 'N/A').lower(),
            gpu.get('normalized_name', 'unknown'),
            gpu.get('vcpus', 0),
            gpu.get('ram', 0),
            gpu.get('price_per_hour_float', None),
            gpu.get('price_per_month_float', None)
        )
        processed_keys.add(key)

    if preferred_region and preferred_region != "any":
        gpus_to_score = [gpu for gpu in processed_gpus if gpu.get('region', '').lower() == preferred_region]
        if not gpus_to_score:
            logging.warning(f"Region filter '{preferred_region}' resulted in 0 GPUs. Relaxing region filter.")
            gpus_to_score = processed_gpus
    else:
        gpus_to_score = processed_gpus

    # 6. Add Fallback Recommendations if Needed
    if not gpus_to_score:
        logging.info("No live GPUs available after processing and filtering. Generating fallback recommendations.")
        gpus_to_score = generate_fallback_recommendations(required_scale, task_type, min_vram_required, processed_keys)
        if not gpus_to_score:
            logging.error("No fallback recommendations generated. Returning empty response with warning.")
            return jsonify({
                "recommendations": [],
                "message": "No GPU recommendations available due to lack of live and static data."
            }), 200

    logging.info(f"Scoring {len(gpus_to_score)} unique GPUs (including {len([g for g in gpus_to_score if g.get('is_requestable') and not g.get('is_available')])} fallback/requestable GPUs).")

    # 7. Scoring Heuristic
    scored_gpus = []
    logging.info(f"Starting heuristic scoring for {len(gpus_to_score)} GPUs...")

    max_price = MAX_PRICE_MONTHLY
    max_tflops = MAX_TFLOPS
    max_bw = MAX_BANDWIDTH_GBPS

    for gpu in gpus_to_score:
        try:
            score = 0.0
            # --- A. Suitability Scores ---
            task_score = 0
            scale_score = 0
            if gpu.get('has_static_specs'):
                primary_suitability = gpu.get('primary_task_suitability', 'Unknown')
                if task_type == 'Training' and primary_suitability in ['Training', 'Balanced']: task_score = 50
                elif task_type == 'Inference' and primary_suitability in ['Inference', 'Balanced']: task_score = 50
                elif primary_suitability == 'Balanced': task_score = 15

                gpu_scales = gpu.get('model_scale_suitability', [])
                if required_scale in gpu_scales: scale_score = 30
                elif any(s in ["Large", "XLarge"] for s in gpu_scales) and required_scale == "Medium": scale_score = 15
                elif any(s == "XLarge" for s in gpu_scales) and required_scale == "Large": scale_score = 15
            score += task_score + scale_score

            # --- B. VRAM Score ---
            gpu_vram = gpu.get('memory_size_gb', 0)
            vram_score = 0
            if min_vram_required <= 0: vram_score = 10
            elif gpu_vram >= min_vram_required: vram_score = 40
            elif gpu_vram > 0:
                vram_deficit_ratio = (min_vram_required - gpu_vram) / min_vram_required
                vram_score = max(-50.0, vram_deficit_ratio * -50.0)
            else:
                vram_score = -50 if min_vram_required > 0 else 0
            score += vram_score

            # --- C. Performance Scores ---
            tflops_score = 0.0
            bw_score = 0.0
            if gpu.get('has_static_specs'):
                tflops = gpu.get('fp32_tflops', 0.0)
                if max_tflops > 0 and tflops > 0:
                    tflops_score = min(1.0, tflops / max_tflops) * 30.0
                bw = gpu.get('bandwidth_gbps', 0.0)
                if max_bw > 0 and bw > 0:
                    bw_score = min(1.0, bw / max_bw) * 20.0
            score += tflops_score + bw_score

            # --- D. Budget and Cost Score ---
            price_mo = gpu.get('price_per_month_float')
            budget_score = 0.0
            cost_efficiency_score = 0.0
            if gpu.get('is_available'):
                if budget_monthly is not None:
                    if price_mo is not None and price_mo > 0 and price_mo <= budget_monthly: budget_score = 60.0
                    elif price_mo is not None and price_mo > 0:
                        over_ratio = (price_mo - budget_monthly) / budget_monthly if budget_monthly > 0 else 1.0
                        budget_score = max(-40.0, over_ratio * -40.0)
                    else: budget_score = -10.0
                if price_mo is not None and price_mo > 0 and max_price > 0:
                    cost_efficiency_score = max(0.0, (1.0 - (price_mo / max_price))) * 40.0
                else: cost_efficiency_score = -5
            elif gpu.get('is_requestable'):
                if budget_monthly is not None: budget_score = -10.0
                cost_efficiency_score = -20.0

            score += budget_score + cost_efficiency_score

            # --- Final Score Assignment ---
            gpu['heuristic_score'] = round(score, 2)

        except Exception as e:
            gpu_name_for_log = gpu.get('gpu_model', gpu.get('gpu_model_live', 'Unknown GPU'))
            logging.error(f"Heuristic scoring failed for GPU: {gpu_name_for_log} (Region: {gpu.get('region', 'N/A')}). Assigning default score. Error: {e}")
            logging.error(traceback.format_exc())
            gpu['heuristic_score'] = DEFAULT_FAILURE_SCORE
            gpu['scoring_error'] = f"Scoring failed: {e}"

        scored_gpus.append(gpu)

    # 8. Final Deduplication Before Sorting
    unique_scored_gpus = []
    seen_keys = set()
    for gpu in scored_gpus:
        key = (
            gpu.get('region', 'N/A').lower(),
            gpu.get('normalized_name', 'unknown'),
            gpu.get('vcpus', 0),
            gpu.get('ram', 0),
            gpu.get('price_per_hour_float', None),
            gpu.get('price_per_month_float', None)
        )
        if key not in seen_keys:
            unique_scored_gpus.append(gpu)
            seen_keys.add(key)
        else:
            logging.debug(f"Removed duplicate GPU in final scoring: {gpu.get('gpu_model', 'Unknown')} (Key: {key})")

    # 9. Sorting by Score
    unique_scored_gpus.sort(key=lambda x: x.get('heuristic_score', DEFAULT_FAILURE_SCORE), reverse=True)

    # Logging top result
    if unique_scored_gpus:
        top_gpu = unique_scored_gpus[0]
        logging.info(f"Ranking V5 complete. Ranked {len(unique_scored_gpus)} unique GPUs. Top result: {top_gpu.get('gpu_model','N/A')} | Score: {top_gpu.get('heuristic_score', 'N/A')}")
    else:
        logging.error("Ranking V5 complete. No GPUs available to rank, which should not happen due to fallbacks.")

    # 10. Format and Return Output
    response = {
        "recommendations": unique_scored_gpus,
        "message": "Recommendations include live data and/or fallback static data based on availability. Duplicates removed."
    }
    return jsonify(response), 200


# --- Main Execution Block ---
if __name__ == '__main__':
    print("Loading static GPU data for enrichment...")
    if not load_static_gpu_data():
        print("WARNING: Failed to load static GPU data. Enrichment and fallbacks may be limited.")
    print(f"Starting Flask server on http://0.0.0.0:{FLASK_PORT} (Debug Mode: {os.environ.get('FLASK_DEBUG', 'True')})")
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true')