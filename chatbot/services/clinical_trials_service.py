import requests
from time import sleep
from urllib.parse import quote

def search_clinical_trials(condition_terms, treatment_terms=None, max_results=200, retries=2):
    """
    Search ClinicalTrials.gov API using Essie syntax for any disease and optional treatment.
    Args:
        condition_terms: e.g., "diabetes" or "(diabetes OR prediabetes) AND obesity"
        treatment_terms: e.g., "metformin" or "(metformin OR glucophage)", optional
        max_results: Maximum number of trials to return
        retries: Number of retry attempts for failed requests
    Returns:
        List of formatted trial dictionaries or None if no results or error
    """
    try:
        base_url = "https://clinicaltrials.gov/api/v2/studies"
        
        # Synonym mapping for conditions and treatments
        condition_synonyms = {
            "diabetes": "diabetes OR type 2 diabetes OR type 1 diabetes OR diabetic",
            "breast cancer": "breast cancer OR mammary carcinoma OR breast neoplasm OR triple-negative breast cancer",
            "alzheimer’s disease": "Alzheimer’s Disease OR AD OR dementia OR cognitive impairment",
            "hypertension": "hypertension OR high blood pressure OR hypertensive"
        }
        treatment_synonyms = {
            "metformin": "metformin OR glucophage OR biguanide",
            "chemotherapy": "chemotherapy OR paclitaxel OR doxorubicin OR cyclophosphamide OR carboplatin OR docetaxel",
            "anti-amyloid": "anti-amyloid OR aducanumab OR lecanemab OR donanemab"
        }
        
        # Apply synonyms
        query_cond = condition_synonyms.get(condition_terms.lower(), condition_terms)
        query_intr = treatment_synonyms.get(treatment_terms.lower(), treatment_terms) if treatment_terms else None
        
        # Encode Essie syntax queries
        encoded_condition = quote(query_cond, safe='()')
        encoded_treatment = quote(query_intr, safe='()') if query_intr else ""
        
        query_params = {
            "format": "json",
            "pageSize": max_results,
            "query.cond": encoded_condition,
            "fields": (
                "NCTId,BriefTitle,OverallStatus,BriefSummary,DetailedDescription,"
                "Condition,Phase,InterventionName,StudyType,EnrollmentCount"
            ),
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED"
        }
        
        if query_intr:
            query_params["query.intr"] = encoded_treatment

        print(f"API Request Parameters: {query_params}")
        print(f"Full URL: {requests.Request('GET', base_url, params=query_params).prepare().url}")

        # Retry logic
        for attempt in range(retries):
            try:
                response = requests.get(base_url, params=query_params, timeout=15)
                print(f"Response Status Code: {response.status_code}")
                print(f"Full API Response: {response.text}")

                if response.status_code != 200:
                    print(f"API request failed: {response.status_code}, {response.text}")
                    if attempt < retries - 1:
                        sleep(2 ** attempt)
                        continue
                    return None

                data = response.json()
                studies = data.get('studies', [])
                print(f"Number of studies found: {len(studies)}")

                if not studies and attempt < retries - 1:
                    # Broaden query: try free-text search across all fields
                    query_params.pop("query.intr", None)  # Remove intervention
                    query_params.pop("query.cond", None)
                    query_params["query.term"] = encoded_condition + (f" {encoded_treatment}" if encoded_treatment else "")
                    print(f"Retrying with broader terms: {query_params}")
                    continue

                if not studies:
                    print("No trials found for query")
                    return None

                formatted_trials = []
                for study in studies:
                    try:
                        protocol = study.get('protocolSection', {})
                        identification = protocol.get('identificationModule', {})
                        description = protocol.get('descriptionModule', {})
                        status = protocol.get('statusModule', {})
                        phase = protocol.get('phaseModule', {})
                        interventions = protocol.get('armsInterventionsModule', {}).get('interventions', [])
                        design = protocol.get('designModule', {})
                        conditions = protocol.get('conditionsModule', {})

                        trial_description = (
                            description.get('briefSummary', '') or 
                            description.get('detailedDescription', 'No description available')
                        )

                        formatted_trial = {
                            'nct_id': identification.get('nctId', 'N/A'),
                            'title': identification.get('briefTitle', 'Untitled'),
                            'status': status.get('overallStatus', 'Unknown'),
                            'description': trial_description,
                            'phase': phase.get('phases', ['Not specified'])[0] if phase.get('phases') else 'Not specified',
                            'interventions': [i.get('name', 'Not specified') for i in interventions],
                            'study_type': design.get('studyType', 'Not specified'),
                            'conditions': conditions.get('conditions', ['Not specified']),
                            'enrollment': design.get('enrollmentInfo', {}).get('count', 'Not specified')
                        }

                        # Prioritize ongoing trials
                        if formatted_trial['status'] in ['RECRUITING', 'ENROLLING_BY_INVITATION']:
                            formatted_trials.insert(0, formatted_trial)
                        else:
                            formatted_trials.append(formatted_trial)

                    except Exception as e:
                        print(f"Error processing trial: {str(e)}")
                        continue

                return formatted_trials[:max_results] if formatted_trials else None

            except requests.Timeout:
                print(f"Attempt {attempt + 1}: ClinicalTrials API request timed out")
                if attempt < retries - 1:
                    sleep(2 ** attempt)
                    continue
                return None

        return None

    except Exception as e:
        print(f"Unexpected error in clinical trials search: {str(e)}")
        return None

def test_clinical_trials_queries():
    """
    Test function with dynamic Essie syntax queries
    """
    test_cases = [
        ("diabetes", "metformin"),
        ("breast cancer", "chemotherapy"),
        ("Alzheimer’s Disease", "anti-amyloid"),
        ("hypertension", None)
    ]

    results = {}
    for condition, treatment in test_cases:
        print(f"\nTesting query - Condition: {condition}, Treatment: {treatment}")
        trials = search_clinical_trials(condition, treatment)
        results[f"{condition}-{treatment or 'none'}"] = trials
        
        if trials:
            print(f"Found {len(trials)} trials")
        else:
            print("No trials found")

    return results