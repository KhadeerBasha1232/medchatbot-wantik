import requests

class UniProtService:
    def __init__(self):
        self.base_url = "https://rest.uniprot.org/uniprotkb/search"

    def search_uniprot(self, query, max_results=10):
        """
        Search UniProtKB using the UniProt API and return results.

        Parameters:
            query (str): The search query (e.g., "kinase human").
            max_results (int): Maximum number of results to fetch.

        Returns:
            list: A list of dictionaries with UniProt IDs, protein names, and descriptions.
        """
        params = {
            "query": query,
            "size": max_results,
            "format": "json"
        }
        
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            return []
        
        entries = []
        for entry in results:
            accession = entry.get("primaryAccession", "N/A")
            protein_name = entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "N/A")
            organism = entry.get("organism", {}).get("scientificName", "N/A")
            
            entries.append({
                "accession": accession,
                "protein_name": protein_name,
                "organism": organism
            })
        
        return entries