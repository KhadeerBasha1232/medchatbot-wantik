import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from chatbot.services.pubmed_service import search_pubmed
from chatbot.services.clinical_trials_service import search_clinical_trials
from chatbot.services.ensembl_service import EnsemblService
from chatbot.services.uniprot_service import UniProtService
from chatbot.services.genbank_service import GenBankService
from chatbot.services.protein_atlas_service import ProteinAtlasService
from chatbot.services.array_express_service import ArrayExpressService
from chatbot.services.geo_service import GeoService

load_dotenv()

class ChatGPTService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("CHATGPT_API_KEY"))
        self.ensembl_service = EnsemblService()
        self.uniprot_service = UniProtService()
        self.genbank_service = GenBankService()
        self.protein_atlas_service = ProteinAtlasService()
        self.array_express_service = ArrayExpressService()
        self.geo_service = GeoService()

        self.analyze_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_research_and_trials",
                    "description": "Get research papers, clinical trials, genomic, protein, sequence, and study data if keywords found in query",
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
                                "description": "Genes like 'APOE4', 'PSEN1', 'APP', 'MAPT'"
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
                                "description": "Proteins like 'amyloid-beta', 'tau protein', 'p-tau'"
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
                            },
                            "need_protein_atlas": {
                                "type": "boolean",
                                "description": "Query Protein Atlas if protein keywords or gene symbols are present"
                            },
                            "need_array_express": {
                                "type": "boolean",
                                "description": "Query ArrayExpress if protein keywords, gene symbols, or AD queries are present"
                            },
                            "need_geo": {
                                "type": "boolean",
                                "description": "Query GEO if protein keywords, gene symbols, or AD queries are present"
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
                            "need_genbank",
                            "need_protein_atlas",
                            "need_array_express",
                            "need_geo"
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
                        "Analyze the query to extract precise keywords for diseases (e.g., 'Alzheimer’s Disease', 'AD', 'dementia'), treatments (e.g., 'donepezil', 'anti-amyloid'), genes (e.g., 'APOE4', 'PSEN1', 'APP', 'MAPT'), variants (e.g., 'rs429358'), phenotypes (e.g., 'cognitive decline'), proteins (e.g., 'amyloid-beta', 'tau protein', 'p-tau'), and sequences (e.g., 'APOE'). "
                        "For queries mentioning 'tau protein', include 'MAPT' in gene_symbols and 'tau protein', 'p-tau' in protein_keywords. "
                        "For queries mentioning 'biomarkers' or 'protein' in AD context, include 'amyloid-beta', 'tau protein', 'p-tau' in protein_keywords and 'APP', 'MAPT', 'APOE4' in gene_symbols. "
                        "Set 'need_ensembl' to true for gene_symbols, variant_ids, or phenotype_terms. "
                        "Set 'need_uniprot' to true for protein_keywords. "
                        "Set 'need_genbank' to true for sequence_keywords. "
                        "Set 'need_protein_atlas' to true for protein_keywords, gene_symbols, or AD queries mentioning 'biomarkers' or 'protein'. "
                        "Set 'need_array_express' to true for protein_keywords, gene_symbols, or AD queries mentioning 'biomarkers', 'protein', or 'studies'. "
                        "Set 'need_geo' to true for protein_keywords, gene_symbols, or AD queries mentioning 'biomarkers', 'protein', or 'studies'. "
                        "Set 'need_trials' to true for AD or preclinical AD queries to include relevant trials (e.g., A4, DIAN-TU). "
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
                    print(f"PubMed results: {pubmed_results}")

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
                    print(f"Clinical Trials results: {trials_results}")

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
                    print(f"Ensembl gene results: {gene_results}")

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
                    print(f"Ensembl variant results: {variant_results}")

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
                    print(f"Ensembl phenotype results: {phenotype_results}")

                if args.get("need_uniprot") and args.get("protein_keywords"):
                    apis_called.append("UniProt")
                    uniprot_query = f"{protein_terms} AND {species}"
                    uniprot_results = self.uniprot_service.search_uniprot(uniprot_query, max_results=3)
                    # TODO: Implement AD relevance filtering in UniProtService
                    if uniprot_results:
                        combined_info += "## Protein Information (UniProt)\n\n"
                        for protein in uniprot_results:
                            combined_info += f"**Accession:** {protein['accession']}\n"
                            combined_info += f"**Protein Name:** {protein['protein_name']}\n"
                            combined_info += f"**Organism:** {protein['organism']}\n\n"
                    print(f"UniProt results: {uniprot_results}")

                if args.get("need_protein_atlas") and (args.get("protein_keywords") or args.get("gene_symbols")):
                    apis_called.append("Protein Atlas")
                    protein_atlas_results = []
                    if args.get("gene_symbols"):
                        for symbol in args["gene_symbols"]:
                            ensembl_results = self.ensembl_service.search_gene_by_symbol(species, symbol)
                            for gene in ensembl_results:
                                ensembl_id = gene.get('id')
                                results = self.protein_atlas_service.search_protein_atlas("", max_results=1, ensembl_id=ensembl_id)
                                protein_atlas_results.extend(results)
                    if args.get("protein_keywords") and not protein_atlas_results:
                        protein_query = f"{protein_terms} AND {species}"
                        results = self.protein_atlas_service.search_protein_atlas(protein_query, max_results=3)
                        protein_atlas_results.extend(results)
                    if protein_atlas_results:
                        combined_info += "## Protein Information (HPA)\n\n"
                        for protein in protein_atlas_results:
                            combined_info += f"**Gene:** {protein['gene']}\n"
                            combined_info += f"**Ensembl ID:** {protein['ensembl_id']}\n"
                            combined_info += f"**Tissue Expression (Cerebral Cortex):** {protein['tissue_expression']}\n"
                            combined_info += f"**Pathology:** {protein['pathology']}\n"
                            combined_info += f"**Subcellular Location:** {protein['subcellular_location']}\n\n"
                    print(f"Protein Atlas results: {protein_atlas_results}")

                if args.get("need_array_express") and (args.get("protein_keywords") or args.get("gene_symbols") or "biomarkers" in user_query.lower()):
                    apis_called.append("ArrayExpress")
                    array_express_results = []
                    if args.get("protein_keywords"):
                        for protein in args["protein_keywords"]:
                            results = self.array_express_service.search_array_express(protein, max_results=2)
                            array_express_results.extend(results)
                    if args.get("gene_symbols"):
                        for symbol in args["gene_symbols"]:
                            results = self.array_express_service.search_array_express(symbol, max_results=2)
                            array_express_results.extend(results)
                    if not array_express_results and "Alzheimer’s Disease" in condition_terms:
                        results = self.array_express_service.search_array_express("Alzheimer’s Disease", max_results=3)
                        array_express_results.extend(results)
                    if array_express_results:
                        combined_info += "## Study Information (ArrayExpress)\n\n"
                        for study in array_express_results:
                            combined_info += f"**Accession:** {study['accession']}\n"
                            combined_info += f"**Title:** {study['title']}\n"
                            combined_info += f"**Description:** {study['description']}\n"
                            combined_info += f"**Assay Count:** {study['assay_count']}\n"
                            combined_info += f"**Study Type:** {study['study_type']}\n\n"
                    print(f"ArrayExpress results: {array_express_results}")

                if args.get("need_geo") and (args.get("protein_keywords") or args.get("gene_symbols") or "biomarkers" in user_query.lower()):
                    apis_called.append("GEO")
                    geo_results = []
                    if args.get("protein_keywords"):
                        for protein in args["protein_keywords"]:
                            results = self.geo_service.search_geo(protein, max_results=2)
                            geo_results.extend(results)
                    if args.get("gene_symbols"):
                        for symbol in args["gene_symbols"]:
                            results = self.geo_service.search_geo(symbol, max_results=2)
                            geo_results.extend(results)
                    if not geo_results and "Alzheimer’s Disease" in condition_terms:
                        results = self.geo_service.search_geo("Alzheimer’s Disease", max_results=3)
                        geo_results.extend(results)
                    if geo_results:
                        combined_info += "## Study Information (GEO)\n\n"
                        for study in geo_results:
                            combined_info += f"**Accession:** {study['accession']}\n"
                            combined_info += f"**Title:** {study['title']}\n"
                            combined_info += f"**Summary:** {study['summary']}\n"
                            combined_info += f"**Sample Count:** {study['sample_count']}\n"
                            combined_info += f"**Study Type:** {study['study_type']}\n\n"
                    print(f"GEO results: {geo_results}")

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
                    print(f"GenBank results: {genbank_results}")

                print(f"\n=== APIs Called: {', '.join(apis_called)} ===\n")
                print(combined_info)

                # Update chat history
                if chat_history is None:
                    chat_history = []
                chat_history.append({"role": "user", "content": user_query})
                response_text = ""
                if combined_info:
                    response_text = self.generate_response(user_query, combined_info)
                else:
                    response_text = self.generate_response(user_query, "No relevant information found.")
                chat_history.append({"role": "assistant", "content": response_text})

                return response_text

            response_text = self.generate_response(user_query)
            if chat_history is None:
                chat_history = []
            chat_history.append({"role": "user", "content": user_query})
            chat_history.append({"role": "assistant", "content": response_text})

            return response_text

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
                        "1. **Overview**: Briefly summarize the query’s intent, referencing prior messages to maintain context (e.g., assume AD if previously mentioned). For tau protein queries, note its role in forming neurofibrillary tangles in AD.\n"
                        "2. **Research Findings**: Summarize PubMed results if available, focusing on AD relevance.\n"
                        "3. **Clinical Trials**: List trial details if available, ensuring relevance to AD (e.g., A4, DIAN-TU, ALZ-801).\n"
                        "4. **Genomic Information**: Include gene, variant, or phenotype data if available.\n"
                        "5. **Protein Information**: Prioritize Human Protein Atlas (HPA) data if available, followed by UniProt data. Include details like tissue expression (e.g., cerebral cortex), pathology, and subcellular location for HPA.\n"
                        "6. **Study Information**: Include ArrayExpress and GEO data if available, detailing study accession, title, description/summary, assay/sample count, and study type.\n"
                        "7. **Sequence Information**: Include GenBank data if available.\n"
                        "8. **Biomarkers**: For AD or preclinical AD queries, list amyloid PET (plaque imaging), plasma p-tau (tau pathology marker), and APOE4 (genetic risk factor).\n"
                        "9. **Relevant Trials**: For AD, include A4 (NCT02008357, anti-amyloid), DIAN-TU (NCT01760005, inherited AD), or ALZ-801 (NCT04616690, tramiprosate) if relevant.\n"
                        "10. **Summary and Recommendations**: Provide a concise synthesis with specific actions (e.g., 'Consult a neurologist for amyloid PET testing' or 'Explore A4 trial eligibility'). Avoid generic or vague statements.\n"
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