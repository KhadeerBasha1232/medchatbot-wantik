import requests
from django.conf import settings

class EnsemblService:
    def __init__(self):
        self.base_url = "https://rest.ensembl.org"
        self.headers = {"Content-Type": "application/json"}

    def search_gene_by_symbol(self, species, symbol, max_results=3):
        """
        Search for gene information by symbol (e.g., BRCA1) in a given species.
        """
        try:
            endpoint = f"{self.base_url}/lookup/symbol/{species}/{symbol}"
            params = {"expand": 1}
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            gene_info = {
                "id": data.get("id", ""),
                "symbol": data.get("display_name", symbol),
                "description": data.get("description", "No description available"),
                "biotype": data.get("biotype", ""),
                "chromosome": data.get("seq_region_name", ""),
                "start": data.get("start", ""),
                "end": data.get("end", ""),
                "strand": "Forward" if data.get("strand", 1) == 1 else "Reverse"
            }
            print(f"[ENSEMBL] Gene info found for {symbol}: {gene_info}")
            return [gene_info]

        except requests.exceptions.RequestException as e:
            print(f"[ENSEMBL] Error in gene lookup for {symbol}: {str(e)}")
            return []

    def search_variant_consequences(self, species, variant_id, max_results=3):
        """
        Fetch variant consequences by variant ID (e.g., rs12345) in a given species.
        """
        try:
            endpoint = f"{self.base_url}/vep/{species}/id/{variant_id}"
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            consequences = []
            for item in data[:max_results]:
                for tc in item.get("transcript_consequences", [])[:max_results]:
                    consequence = {
                        "variant_id": variant_id,
                        "gene_symbol": tc.get("gene_symbol", ""),
                        "transcript_id": tc.get("transcript_id", ""),
                        "consequence_terms": tc.get("consequence_terms", []),
                        "impact": tc.get("variant_allele", "")
                    }
                    consequences.append(consequence)

            print(f"[ENSEMBL] Found {len(consequences)} consequences for variant {variant_id}")
            return consequences

        except requests.exceptions.RequestException as e:
            print(f"[ENSEMBL] Error in variant consequences for {variant_id}: {str(e)}")
            return []

    def search_phenotype_by_gene(self, species, gene_symbol, max_results=3):
        """
        Fetch phenotype annotations for a given gene in a species.
        """
        try:
            endpoint = f"{self.base_url}/phenotype/gene/{species}/{gene_symbol}"
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            phenotypes = []
            for item in data[:max_results]:
                phenotype = {
                    "gene_symbol": gene_symbol,
                    "phenotype_description": item.get("description", "No description available"),
                    "source": item.get("source", ""),
                    "study": item.get("study", "")
                }
                phenotypes.append(phenotype)

            print(f"[ENSEMBL] Phenotypes found for gene {gene_symbol}: {len(phenotypes)}")
            return phenotypes

        except requests.exceptions.RequestException as e:
            print(f"[ENSEMBL] Error in phenotype annotations for {gene_symbol}: {str(e)}")
            return []
