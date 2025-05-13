import requests
from typing import List, Dict
from urllib.parse import quote

class ProteinAtlasService:
    def __init__(self):
        self.base_url = "https://www.proteinatlas.org"
        self.search_api_endpoint = "/api/search_download.php"
        self.timeout = 10

    def search_protein_atlas(self, query: str, max_results: int = 3, ensembl_id: str = None) -> List[Dict]:
        """
        Search the Human Protein Atlas for protein data by query or Ensembl ID.
        Args:
            query: Protein name or keyword (e.g., 'amyloid-beta', 'tau protein').
            max_results: Maximum number of results to return.
            ensembl_id: Optional Ensembl ID (e.g., 'ENSG00000142192') for direct lookup.
        Returns:
            List of dictionaries with protein data (name, gene, expression, pathology).
        """
        try:
            results = []
            if ensembl_id:
                # Query individual entry by Ensembl ID (e.g., https://www.proteinatlas.org/ENSG00000142192.json)
                url = f"{self.base_url}/{ensembl_id}.json"
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                parsed_data = self._parse_protein_data(data)
                if self._is_ad_relevant(parsed_data):
                    results.append(parsed_data)
            else:
                # Query by protein name/keyword using search_download.php
                encoded_query = quote(query)
                columns = "g,gs,eg,t_RNA_cerebral_cortex,di,up,scl"  # Relevant columns for AD
                url = f"{self.base_url}{self.search_api_endpoint}?search={encoded_query}&format=json&columns={columns}&compress=no"
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                for item in data[:max_results]:
                    parsed_data = self._parse_protein_data(item)
                    if self._is_ad_relevant(parsed_data):
                        results.append(parsed_data)

            return results[:max_results]

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"Bad request to Protein Atlas API: {e}")
            elif e.response.status_code == 500:
                print(f"Server error from Protein Atlas API: {e}")
            else:
                print(f"HTTP error querying Protein Atlas API: {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error querying Protein Atlas API: {e}")
            return []
        except ValueError as e:
            print(f"Error parsing Protein Atlas response: {e}")
            return []

    def _parse_protein_data(self, data: Dict) -> Dict:
        """
        Parse HPA API response to extract relevant protein data.
        Args:
            data: Raw API response data (JSON).
        Returns:
            Dictionary with formatted protein data.
        """
        try:
            return {
                'protein_name': data.get('Gene', 'Unknown'),  # Gene name as proxy
                'gene': data.get('Gene', 'Unknown'),
                'ensembl_id': data.get('Ensembl', 'Unknown'),
                'tissue_expression': data.get('t_RNA_cerebral_cortex', 'Not available'),  # Brain expression
                'pathology': data.get('di', 'Not available'),  # Disease involvement
                'subcellular_location': data.get('scl', 'Not available'),
                'uniprot_id': data.get('up', 'Not available')
            }
        except Exception as e:
            print(f"Error parsing protein data: {e}")
            return {}

    def _is_ad_relevant(self, data: Dict) -> bool:
        """
        Filter results for AD relevance (e.g., amyloid-beta, tau).
        Args:
            data: Parsed protein data.
        Returns:
            True if relevant to AD, False otherwise.
        """
        ad_keywords = ['amyloid', 'tau', 'APP', 'PSEN1', 'PSEN2', 'APOE', 'Alzheimer']
        protein_name = data.get('protein_name', '').lower()
        gene = data.get('gene', '').lower()
        pathology = data.get('pathology', '').lower()
        return any(keyword.lower() in (protein_name + gene + pathology) for keyword in ad_keywords)