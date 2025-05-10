from Bio import Entrez
import os
from dotenv import load_dotenv
import warnings

load_dotenv()

class GenBankService:
    def __init__(self):
        # Configure Entrez email for NCBI API compliance (optional but recommended)
        email = os.getenv("NCBI_EMAIL")
        if not email:
            warnings.warn(
                "No NCBI_EMAIL provided in environment. NCBI requires an email for GenBank API access. "
                "Requests may fail without a valid email. Consider setting NCBI_EMAIL in your .env file."
            )
            email = None
        Entrez.email = email

    def search_genbank(self, query, max_results=10):
        """
        Search GenBank using Biopython's Entrez module and return sequence metadata.

        Parameters:
            query (str): The search query (e.g., "BRCA1 human").
            max_results (int): Maximum number of results to fetch.

        Returns:
            list: A list of dictionaries with accession numbers, definitions, and organisms.
        """
        try:
            # Search GenBank for sequence IDs
            handle = Entrez.esearch(db="nucleotide", term=query, retmax=max_results)
            search_results = Entrez.read(handle)
            handle.close()
            sequence_ids = search_results.get("IdList", [])
            if not sequence_ids:
                return []

            # Fetch sequence records
            sequences = []
            for seq_id in sequence_ids:
                try:
                    # Retrieve the sequence record in GenBank format
                    handle = Entrez.efetch(db="nucleotide", id=seq_id, rettype="gb", retmode="text")
                    from Bio import SeqIO
                    record = SeqIO.read(handle, "genbank")
                    handle.close()
                    sequences.append({
                        "accession": record.id if record.id else "N/A",
                        "definition": record.description if record.description else "No definition available",
                        "organism": record.annotations.get("organism", "N/A")
                    })
                except Exception as e:
                    print(f"Error fetching record {seq_id}: {str(e)}")
                    continue

            return sequences

        except Exception as e:
            print(f"Error searching GenBank: {str(e)}")
            return []