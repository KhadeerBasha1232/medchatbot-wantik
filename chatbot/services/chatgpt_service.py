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
                                "description": "Keywords like 'Alzheimer’s Disease', 'AD', 'dementia', 'preclinical AD'"
                            },
                            "treatment_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Treatments like 'amyloid', 'tau', 'donepezil'"
                            },
                            "gene_symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Genes like 'APOE4', 'PSEN1', 'APP'"
                            },
                            "variant_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Variant IDs like 'rs429358'"
                            },
                            "phenotype_terms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Phenotypes like 'cognitive decline', 'memory loss'"
                            },
                            "protein_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Proteins like 'amyloid-beta', 'tau protein'"
                            },
                            "sequence_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Sequences like 'APOE', 'PSEN1'"
                            },
                            "species": {
                                "type": "string",
                                "description": "Species name, default 'homo_sapiens'",
                                "default": "homo_sapiens"
                            },
                            "need_trials": {"type": "boolean"},
                            "need_pubmed": {"type": "boolean"},
                            "need_ensembl": {
                                "type": "boolean",
                                "description": "Query Ensembl if genomic terms are present"
                            },
                            "need_uniprot": {
                                "type": "boolean",
                                "description": "Query UniProt if protein keywords are present"
                            },
                            "need_genbank": {
                                "type": "boolean",
                                "description": "Query GenBank if sequence keywords are present"
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

    def analyze_query(self, user_query, chat_history=None):
        try:
            apis_called = []
            combined_info = ""

            # Log chat_history for debugging
            print(f"Chat history received: {chat_history}")

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a specialized assistant in a medical research chatbot focused on Alzheimer’s Disease (AD). "
                        "Use previous messages in the conversation history to maintain context, avoiding redundant clarifications. "
                        "For example, if AD or preclinical AD was mentioned, assume the query relates to it unless otherwise specified. "
                        "Interpret 'preclinical AD' strictly as asymptomatic individuals with biomarker evidence (e.g., amyloid PET, plasma p-tau, APOE4), not animal or lab research. "
                        "Analyze the query to extract precise keywords for diseases (e.g., 'Alzheimer’s Disease', 'AD', 'dementia'), treatments (e.g., 'donepezil', 'anti-amyloid'), genes (e.g., 'APOE4', 'PSEN1'), variants (e.g., 'rs429358'), phenotypes (e.g., 'cognitive decline'), proteins (e.g., 'amyloid-beta', 'tau'), and sequences (e.g., 'APOE'). "
                        "Set 'need_ensembl' to true only for explicit gene_symbols, variant_ids, or phenotype_terms. Set 'need_uniprot' to true only for explicit protein_keywords. Set 'need_genbank' to true only for explicit sequence_keywords. "
                        "Prioritize relevance, ensuring keywords align with the query’s intent and context."
                    )
                }
            ]

            if chat_history:
                messages.extend(chat_history)
            else:
                messages.append({"role": "user", "content": user_query})

            # Log messages for debugging
            print(f"Messages sent to OpenAI: {messages}")

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
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

                if args.get("need_ensembl") and (
                    args.get("gene_symbols") or args.get("variant_ids") or args.get("phenotype_terms")
                ):
                    apis_called.append("Ensembl")

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

                    phenotype_results = []
                    for gene_symbol in args["gene_symbols"]:
                        phenotype_results.extend(self.ensembl_service.search_phenotype_by_gene(species, gene_symbol))
                    if phenotype_results:
                        combined_info += "## Phenotype Annotations\n\n"
                        for p in phenotype_results:
                            combined_info += f"**Gene:** {p['gene_symbol']}\n"
                            combined_info += f"**Phenotype:** {p['phenotype_description']}\n"
                            combined_info += f"**Source:** {p['source']}\n"
                            f"**Study:** {p['study']}\n\n"

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
                        "You are a medical research assistant specializing in Alzheimer’s Disease (AD). "
                        "Generate a concise, relevant, and actionable response tailored to the user's query, using provided information and conversation history. "
                        "Structure the response as follows, including only sections with relevant data:\n"
                        "1. **Overview**: Briefly summarize the query’s intent, referencing prior messages to maintain context (e.g., assume AD if previously mentioned).\n"
                        "2. **Research Findings**: Summarize PubMed results if available.\n"
                        "3. **Clinical Trials**: List trial details if available, ensuring relevance to AD for AD queries.\n"
                        "4. **Genomic Information**: Include gene, variant, or phenotype data if available.\n"
                        "5. **Protein Information**: Include UniProt data if available.\n"
                        "6. **Sequence Information**: Include GenBank data if available.\n"
                        "7. **Biomarkers**: For AD or preclinical AD queries, list amyloid PET (plaque imaging), plasma p-tau (tau pathology marker), and APOE4 (genetic risk factor).\n"
                        "8. **Relevant Trials**: For AD, include A4 (NCT02008357, anti-amyloid), DIAN-TU (NCT01760005, inherited AD), or ALZ-801 (NCT04616690, tramiprosate) if relevant.\n"
                        "9. **Summary and Recommendations**: Provide a concise synthesis with specific actions (e.g., 'Consult a neurologist for amyloid PET testing' or 'Explore A4 trial eligibility'). Avoid generic or vague statements.\n"
                        "Use bullet points and section headings. Exclude sections with no data or irrelevant information. Ensure responses are precise, avoiding filler or redundant clarifications."
                    )
                },
                {"role": "user", "content": user_query}
            ]

            if research_info and research_info.strip() != "No relevant information found.":
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