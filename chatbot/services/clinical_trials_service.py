# services/clinical_trials_service.py
import requests

class ClinicalTrialsService:
    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"

    def search_trials(self, terms):
        try:
            params = {
                "format": "json",
                "query.term": " AND ".join(terms),
                "pageSize": 5,  # Limit results for relevant matches
                "fields": "NCTId,BriefTitle,DetailedDescription,Condition,Phase,OverallStatus"
            }

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get('studies'):
                return None

            # Format the trials data for ChatGPT
            formatted_trials = []
            for study in data['studies']:
                protocol = study.get('protocolSection', {})
                identification = protocol.get('identificationModule', {})
                description = protocol.get('descriptionModule', {})
                status = protocol.get('statusModule', {})

                formatted_trial = {
                    'title': identification.get('briefTitle', ''),
                    'description': description.get('detailedDescription', ''),
                    'status': status.get('overallStatus', ''),
                    'nct_id': identification.get('nctId', '')
                }
                formatted_trials.append(formatted_trial)

            return formatted_trials

        except Exception as e:
            print(f"ClinicalTrials API Error: {str(e)}")
            return None
# services/clinical_trials_service.py
import requests
import logging

logger = logging.getLogger(__name__)

def search_clinical_trials(condition_terms, treatment_terms, max_results=5):
    """
    Search ClinicalTrials.gov API using Essie expression syntax
    condition_terms: e.g., "diabetes type 2" or "(diabetes OR prediabetes) AND obesity"
    treatment_terms: e.g., "GLP-1" or "(metformin OR glucophage)"
    """
    try:
        base_url = "https://clinicaltrials.gov/api/v2/studies"
        
        # Format query parameters using Essie syntax
        query_params = {
            "format": "json",
            "pageSize": max_results,
            "query.cond": condition_terms,  # Condition query using Essie syntax
            "query.intr": treatment_terms,  # Intervention query using Essie syntax
            "fields": "NCTId,BriefTitle,OverallStatus,BriefSummary,DetailedDescription,Condition,Phase,InterventionName"
        }

        print("API Request Parameters:", query_params)
        print("Full URL:", requests.Request('GET', base_url, params=query_params).prepare().url)

        response = requests.get(base_url, params=query_params)
        print("Response Status Code:", response.status_code)

        if response.status_code == 200:
            data = response.json()
            studies = data.get('studies', [])
            print(f"Number of studies found: {len(studies)}")

            if not studies:
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

                    formatted_trial = {
                        'nct_id': identification.get('nctId', ''),
                        'title': identification.get('briefTitle', ''),
                        'status': status.get('overallStatus', ''),
                        'description': description.get('briefSummary', '') or description.get('detailedDescription', ''),
                        'phase': phase.get('phase', 'Not specified'),
                        'interventions': [i.get('name', '') for i in interventions]
                    }

                    formatted_trials.append(formatted_trial)
                    print(f"Processed trial: {formatted_trial['nct_id']}")

                except Exception as e:
                    print(f"Error processing trial: {str(e)}")
                    continue

            return formatted_trials

        else:
            print(f"API request failed: {response.status_code}")
            print("Response content:", response.text)
            return None

    except Exception as e:
        print(f"Error in clinical trials search: {str(e)}")
        return None

# Add test function to verify different query formats
def test_clinical_trials_queries():
    """
    Test function with various Essie syntax queries
    """
    test_cases = [
        # Test case 1: Simple condition and treatment
        ("diabetes", "GLP-1"),
        
        # Test case 2: Condition with OR operator
        ("(diabetes OR prediabetes)", "metformin"),
        
        # Test case 3: Complex condition and treatment
        ("(type 2 diabetes) AND obesity", "(GLP-1 OR GLP1)"),
        
        # Test case 4: Multiple conditions with AND
        ("lung cancer AND stage IV", "immunotherapy")
    ]

    results = {}
    for condition, treatment in test_cases:
        print(f"\nTesting query - Condition: {condition}, Treatment: {treatment}")
        trials = search_clinical_trials(condition, treatment)
        results[f"{condition}-{treatment}"] = trials
        
        if trials:
            print(f"Found {len(trials)} trials")
        else:
            print("No trials found")

    return results