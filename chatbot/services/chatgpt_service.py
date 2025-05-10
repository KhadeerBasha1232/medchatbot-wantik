import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from chatbot.services.pubmed_service import search_pubmed
from chatbot.services.clinical_trials_service import search_clinical_trials
from chatbot.services.ensembl_service import EnsemblService
from chatbot.services.uniprot_service import UniProtService
from chatbot.services.genbank_service import GenBankService

load_dotenv()

class ChatGPTService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("CHATGPT_API_KEY"))
        self.ensembl_service = EnsemblService()
        self.uniprot_service = UniProtService()
        self.genbank_service = GenBankService()

        self.analyze_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_research_and_trials",
                    "description": "Get research papers, clinical trials, genomic, protein, and sequence data if keywords found in query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "disease_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "keywords related to disease like CKD AND HF"
                            },
                            "treatment_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "keywords related to treatment like GLP-1 receptor"
                            },
                            "gene_symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Gene symbols like BRCA1 or TP53"
                            },
                            "variant_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Variant IDs like rs12345"
                            },
                            "phenotype_terms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Phenotype terms like breast cancer"
                            },
                            "protein_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Protein-related keywords like kinase or receptor"
                            },
                            "sequence_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Sequence-related keywords like BRCA1 or mRNA"
                            },
                            "species": {
                                "type": "string",
                                "description": "Species name for genomic/protein/sequence data, default is homo_sapiens",
                                "default": "homo_sapiens"
                            },
                            "need_trials": {"type": "boolean"},
                            "need_pubmed": {"type": "boolean"},
                            "need_ensembl": {
                                "type": "boolean",
                                "description": "Whether to query Ensembl if genomic terms are present"
                            },
                            "need_uniprot": {
                                "type": "boolean",
                                "description": "Whether to query UniProt if protein keywords are present"
                            },
                            "need_genbank": {
                                "type": "boolean",
                                "description": "Whether to query GenBank if sequence keywords are present"
                            }
                        },
                        "required": [
                            "disease_keywords",
                            "treatment_keywords",
                            "gene_symbols",
                            "variant_ids",
                            "phenotype_terms",
                            "protein_keywords",
                            "sequence_keywords",
                            "species",
                            "need_trials",
                            "need_pubmed",
                            "need_ensembl",
                            "need_uniprot",
                            "need_genbank"
                        ]
                    }
                }
            }
        ]

    def analyze_query(self, user_query):
        try:
            apis_called = []
            combined_info = ""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You're a specialized assistant in a medical research chatbot. "
                            "Analyze the query and extract disease keywords, treatment keywords, gene symbols, "
                            "variant IDs, phenotype terms, protein keywords, and sequence keywords. Only set 'need_ensembl' to true if "
                            "gene_symbols, variant_ids, or phenotype_terms are explicitly present. Only set 'need_uniprot' "
                            "to true if protein_keywords are explicitly present. Only set 'need_genbank' to true if sequence_keywords are present."
                        )
                    },
                    {"role": "user", "content": user_query}
                ],
                tools=self.analyze_tools
            )

            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                args = json.loads(tool_call.function.arguments)
                print(f"Tool call arguments: {args}")
                condition_terms = " AND ".join(args["disease_keywords"])
                treatment_terms = " AND ".join(args["treatment_keywords"])
                protein_terms = " AND ".join(args["protein_keywords"])
                sequence_terms = " AND ".join(args["sequence_keywords"])
                species = args.get("species", "homo_sapiens")

                # PubMed search
                if args.get("need_pubmed"):
                    apis_called.append("PubMed")
                    search_query = f"{treatment_terms} AND {condition_terms}"
                    pubmed_results = search_pubmed(search_query, api_key="", max_results=3)
                    if pubmed_results:
                        combined_info += "## Research Papers\n\n"
                        for paper in pubmed_results:
                            combined_info += f"**Title:** {paper['title']}\n"
                            combined_info += f"**Abstract:** {paper['abstract']}\n"
                            combined_info += f"**PMID:** {paper['pmid']}\n\n"

                # Clinical Trials search
                if args.get("need_trials"):
                    apis_called.append("Clinical Trials")
                    trials_results = search_clinical_trials(condition_terms, treatment_terms, max_results=3)
                    if trials_results:
                        combined_info += "## Clinical Trials\n\n"
                        for trial in trials_results:
                            combined_info += f"**Title:** {trial['title']}\n"
                            combined_info += f"**Status:** {trial['status']}\n"
                            combined_info += f"**Phase:** {trial.get('phase', 'Not specified')}\n"
                            combined_info += f"**Interventions:** {', '.join(trial.get('interventions', ['Not specified']))}\n"
                            combined_info += f"**Description:** {trial.get('description', 'No description available')}\n"
                            combined_info += f"**NCT ID:** {trial['nct_id']}\n\n"

                # Ensembl genomic data
                if args.get("need_ensembl") and (
                    args.get("gene_symbols") or args.get("variant_ids") or args.get("phenotype_terms")
                ):
                    apis_called.append("Ensembl")

                    # Gene info
                    gene_results = []
                    for symbol in args["gene_symbols"]:
                        gene_results.extend(self.ensembl_service.search_gene_by_symbol(species, symbol))
                    if gene_results:
                        combined_info += "## Gene Information\n\n"
                        for gene in gene_results:
                            combined_info += f"**Gene:** {gene['symbol']} ({gene['id']})\n"
                            combined_info += f"**Description:** {gene['description']}\n"
                            combined_info += f"**Biotype:** {gene['biotype']}\n"
                            combined_info += f"**Location:** {gene['chromosome']}:{gene['start']}-{gene['end']} ({gene['strand']})\n\n"

                    # Variant consequences
                    variant_results = []
                    for variant_id in args["variant_ids"]:
                        variant_results.extend(self.ensembl_service.search_variant_consequences(species, variant_id))
                    if variant_results:
                        combined_info += "## Variant Consequences\n\n"
                        for variant in variant_results:
                            combined_info += f"**Variant:** {variant['variant_id']}\n"
                            combined_info += f"**Gene:** {variant['gene_symbol']}\n"
                            combined_info += f"**Transcript:** {variant['transcript_id']}\n"
                            combined_info += f"**Consequences:** {', '.join(variant['consequence_terms'])}\n"
                            combined_info += f"**Impact:** {variant['impact']}\n\n"

                    # Phenotype annotations
                    phenotype_results = []
                    for gene_symbol in args["gene_symbols"]:
                        phenotype_results.extend(self.ensembl_service.search_phenotype_by_gene(species, gene_symbol))
                    if phenotype_results:
                        combined_info += "## Phenotype Annotations\n\n"
                        for p in phenotype_results:
                            combined_info += f"**Gene:** {p['gene_symbol']}\n"
                            combined_info += f"**Phenotype:** {p['phenotype_description']}\n"
                            combined_info += f"**Source:** {p['source']}\n"
                            combined_info += f"**Study:** {p['study']}\n\n"

                # UniProt protein data
                if args.get("need_uniprot") and args.get("protein_keywords"):
                    apis_called.append("UniProt")
                    uniprot_query = f"{protein_terms} AND {species}"
                    uniprot_results = self.uniprot_service.search_uniprot(uniprot_query, max_results=3)
                    if uniprot_results:
                        combined_info += "## Protein Information\n\n"
                        for protein in uniprot_results:
                            combined_info += f"**Accession:** {protein['accession']}\n"
                            combined_info += f"**Protein Name:** {protein['protein_name']}\n"
                            combined_info += f"**Organism:** {protein['organism']}\n\n"

                # GenBank sequence data
                if args.get("need_genbank") and args.get("sequence_keywords"):
                    apis_called.append("GenBank")
                    genbank_query = f"{sequence_terms} AND {species}"
                    genbank_results = self.genbank_service.search_genbank(genbank_query, max_results=3)
                    if genbank_results:
                        combined_info += "## Sequence Information\n\n"
                        for sequence in genbank_results:
                            combined_info += f"**Accession:** {sequence['accession']}\n"
                            combined_info += f"**Definition:** {sequence['definition']}\n"
                            combined_info += f"**Organism:** {sequence['organism']}\n\n"

                print(f"\n=== APIs Called: {', '.join(apis_called)} ===\n")
                print(combined_info)

                if combined_info:
                    return self.generate_response(user_query, combined_info)
                else:
                    return self.generate_response(user_query, "No relevant information found.")

            return self.generate_response(user_query)

        except Exception as e:
            return f"An error occurred while processing the query: {str(e)}"

    def generate_response(self, user_query, research_info=None):
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a professional medical assistant. Present information in a clear structure:\n"
                        "1. Overview of the query\n"
                        "2. Research findings (if available)\n"
                        "3. Clinical trial information (if available)\n"
                        "4. Genomic information (if available, including gene details, variants, and phenotypes)\n"
                        "5. Protein information (if available, including UniProt data)\n"
                        "6. Sequence information (if available, including GenBank data)\n"
                        "7. Summary and recommendations\n"
                        "Use bullet points and section headings."
                    )
                },
                {"role": "user", "content": user_query}
            ]

            if research_info:
                messages.append({"role": "user", "content": f"Information retrieved:\n\n{research_info}"})

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Response generation failed: {str(e)}")