import requests
from typing import List, Dict
from urllib.parse import quote

class GeoService:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.search_endpoint = "/esearch.fcgi"
        self.summary_endpoint = "/esummary.fcgi"
        self.timeout = 10

    def search_geo(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search NCBI GEO for studies relevant to the query.
        Args:
            query: Search term (e.g., 'Alzheimer’s Disease', 'tau protein', 'MAPT').
            max_results: Maximum number of results to return.
        Returns:
            List of dictionaries with study data (accession, title, summary, sample_count).
        """
        try:
            results = []
            encoded_query = quote(f"{query} AND Homo sapiens[Organism] AND gse[EntryType]")
            search_url = f"{self.base_url}{self.search_endpoint}"
            search_params = {
                "db": "gds",
                "term": encoded_query,
                "retmax": max_results,
                "retmode": "json"
            }
            print(f"Querying GEO search: {search_url} with params: {search_params}")
            search_response = requests.get(search_url, params=search_params, timeout=self.timeout)
            search_response.raise_for_status()
            search_data = search_response.json().get('esearchresult', {})
            id_list = search_data.get('idlist', [])
            print(f"GEO search response IDs: {id_list}")

            if not id_list:
                return []

            summary_url = f"{self.base_url}{self.summary_endpoint}"
            summary_params = {
                "db": "gds",
                "id": ",".join(id_list),
                "retmode": "json"
            }
            print(f"Querying GEO summary: {summary_url} with params: {summary_params}")
            summary_response = requests.get(summary_url, params=summary_params, timeout=self.timeout)
            summary_response.raise_for_status()
            summary_data = summary_response.json().get('result', {})
            print(f"GEO summary response: {summary_data}")

            for geo_id in id_list:
                study_data = summary_data.get(geo_id, {})
                parsed_data = self._parse_study_data(study_data)
                if self._is_ad_relevant(parsed_data):
                    results.append(parsed_data)

            print(f"GEO parsed results: {results}")
            return results[:max_results]

        except requests.exceptions.HTTPError as e:
            print(f"HTTP error querying GEO API: {e} (Status: {e.response.status_code})")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error querying GEO API: {e}")
            return []
        except ValueError as e:
            print(f"Error parsing GEO response: {e}")
            return []

    def _parse_study_data(self, data: Dict) -> Dict:
        """
        Parse GEO API response to extract relevant study data.
        Args:
            data: Raw API response data (JSON).
        Returns:
            Dictionary with formatted study data.
        """
        try:
            parsed = {
                'accession': data.get('accession', 'Unknown'),
                'title': data.get('title', 'Unknown'),
                'summary': data.get('summary', 'Not available'),
                'sample_count': data.get('n_samples', 'Not available'),
                'study_type': data.get('gdstype', 'Not available')
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
        summary = data.get('summary', '').lower()
        is_relevant = any(keyword.lower() in (title + summary) for keyword in ad_keywords)
        print(f"AD relevance check: {is_relevant} for data: {data}")
        return is_relevant