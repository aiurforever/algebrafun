import argparse
import collections
import requests
import pandas as pd
import matplotlib.pyplot as plt


API_ENDPOINT = "https://api.fda.gov/drug/event.json"
DEFAULT_LIMIT = 100  # maximum allowed by the API


def fetch_reports(drug_name: str, max_results: int = 1000):
    """Fetch adverse event reports related to `drug_name`.

    Parameters
    ----------
    drug_name : str
        Name of the medicinal product to search for.
    max_results : int
        Maximum number of reports to retrieve.
    """
    all_results = []
    for skip in range(0, max_results, DEFAULT_LIMIT):
        params = {
            "search": f"patient.drug.medicinalproduct:\"{drug_name}\"",
            "limit": DEFAULT_LIMIT,
            "skip": skip,
        }
        response = requests.get(API_ENDPOINT, params=params)
        if response.status_code != 200:
            break
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if len(results) < DEFAULT_LIMIT:
            break
    return all_results


def parse_report(raw_report: dict, drug_name: str):
    patient = raw_report.get("patient", {})
    report_id = raw_report.get("safetyreportid")
    report_date = raw_report.get("receivedate")
    country = raw_report.get("primarysource", {}).get("reportercountry")

    # Patient demographics
    age = patient.get("patientonsetage")
    sex_code = str(patient.get("patientsex"))
    sex_lookup = {"1": "Male", "2": "Female"}
    sex = sex_lookup.get(sex_code, "Unknown")

    # Collect reactions
    reactions = [r.get("reactionmeddrapt") for r in patient.get("reaction", []) if r.get("reactionmeddrapt")]

    # Determine route and suspect drug role
    route = None
    role = None
    for drug in patient.get("drug", []):
        med = drug.get("medicinalproduct", "").lower()
        if med == drug_name.lower():
            route = drug.get("drugadministrationroute")
            role_code = str(drug.get("drugcharacterization"))
            role_lookup = {"1": "Suspect", "2": "Concomitant", "3": "Interacting"}
            role = role_lookup.get(role_code)
            break

    return {
        "report_id": report_id,
        "date": report_date,
        "country": country,
        "age": age,
        "sex": sex,
        "route": route,
        "role": role,
        "reactions": reactions,
    }


def summarize_events(parsed_reports):
    counter = collections.Counter()
    for rep in parsed_reports:
        counter.update(rep["reactions"])
    return counter.most_common(10)


def visualize_event_counts(event_counts):
    terms = [t for t, _ in event_counts]
    counts = [c for _, c in event_counts]
    plt.figure(figsize=(10, 6))
    plt.barh(terms, counts)
    plt.xlabel("Frequency")
    plt.ylabel("Adverse Event")
    plt.title("Top Adverse Events")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query FAERS adverse events")
    parser.add_argument("drug", help="Drug name to search (e.g., Zolgensma)")
    parser.add_argument("--max", type=int, default=1000, help="Maximum number of results to fetch")
    parser.add_argument("--plot", action="store_true", help="Visualize top events")
    args = parser.parse_args()

    reports_raw = fetch_reports(args.drug, args.max)
    parsed = [parse_report(r, args.drug) for r in reports_raw]
    df = pd.DataFrame(parsed)
    print(df.head())

    event_counts = summarize_events(parsed)
    print("Top adverse events:")
    for term, cnt in event_counts:
        print(f"{term}: {cnt}")

    if args.plot:
        visualize_event_counts(event_counts)
