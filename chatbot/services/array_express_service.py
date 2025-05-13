import requests
from typing import List, Dict
from urllib.parse import quote

class ArrayExpressService:
    def __init__(self):
        self.base_url = "https://www.ebi.ac.uk/biostudies/api/v1"
        self.search_endpoint = "/search"
        self.timeout = 10

    def search_array_express(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search BioStudies/ArrayExpress for studies relevant to the query.
        Args:
            query: Search term (e.g., 'Alzheimer’s Disease', 'tau protein', 'MAPT').
            max_results: Maximum number of results to return.
        Returns:
            List of dictionaries with study data (accession, title, description, assay_count).
        """
        try:
            results = []
            encoded_query = quote(query)
            params = {
                "organism": "Homo sapiens",
                "study_type": "RNA-seq of coding RNA OR transcription profiling by array",
                "experimental_factor_value": f"{encoded_query} OR Alzheimer’s Disease",
                "size": max_results
            }
            url = f"{self.base_url}{self.search_endpoint}"
            print(f"Querying ArrayExpress: {url} with params: {params}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get('hits', [])
            print(f"ArrayExpress response: {data}")

            for item in data[:max_results]:
                parsed_data = self._parse_study_data(item)
                if self._is_ad_relevant(parsed_data):
                    results.append(parsed_data)

            print(f"ArrayExpress parsed results: {results}")
            return results[:max_results]

        except requests.exceptions.HTTPError as e:
            print(f"HTTP error querying ArrayExpress API: {e} (Status: {e.response.status_code})")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error querying ArrayExpress API: {e}")
            return []
        except ValueError as e:
            print(f"Error parsing ArrayExpress response: {e}")
            return []

    def _parse_study_data(self, data: Dict) -> Dict:
        """
        Parse BioStudies API response to extract relevant study data.
        Args:
            data: Raw API response data (JSON).
        Returns:
            Dictionary with formatted study data.
        """
        try:
            parsed = {
                'accession': data.get('accession', 'Unknown'),
                'title': data.get('title', 'Unknown'),
                'description': data.get('description', 'Not available'),
                'assay_count': data.get('assay_count', 'Not available'),
                'study_type': data.get('study_type', 'Not available'),
                'organism': data.get('organism', 'Not available')
            }
            print(f"Parsed study data: {parsed}")
            return parsed
        except Exception as e:
            print(f"Error parsing study data: {e}")
            return {}

    def _is_ad_relevant(self, data: Dict) -> bool:
        """
        Filter results for AD relevance (e.g., Alzheimer’s Disease, tau, amyloid).
        Args:
            data: Parsed study data.
        Returns:
            True if relevant to AD, False otherwise.
        """
        ad_keywords = ['alzheimer', 'tau', 'amyloid', 'APP', 'MAPT', 'PSEN1', 'PSEN2', 'APOE']
        title = data.get('title', '').lower()
        description = data.get('description', '').lower()
        is_relevant = any(keyword.lower() in (title + description) for keyword in ad_keywords)
        print(f"AD relevance check: {is_relevant} for data: {data}")
        return is_relevant