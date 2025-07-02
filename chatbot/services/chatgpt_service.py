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
import urllib.parse
import logging
import re

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                    "name": "get_clinical_trials",
                    "description": "Search for clinical trials based on disease and treatment keywords",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "disease_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Disease terms like 'diabetes', 'breast cancer', 'Parkinson’s Disease'"
                            },
                            "treatment_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Treatment terms like 'insulin', 'chemotherapy', 'deep brain stimulation'"
                            },
                            "need_trials": {
                                "type": "boolean",
                                "description": "Whether to query clinical trials"
                            }
                        },
                        "required": ["disease_keywords", "treatment_keywords", "need_trials"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_research_and_trials",
                    "description": "Retrieve research papers, clinical trials, genomic, protein, sequence, and study data based on query keywords",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "disease_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Keywords like 'Alzheimer’s Disease', 'Parkinson’s Disease', 'breast cancer'"
                            },
                            "treatment_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Treatments like 'insulin', 'anti-amyloid', 'dopamine replacement'"
                            },
                            "gene_symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Genes like 'APOE4', 'LRRK2', 'BRCA1'"
                            },
                            "variant_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Variant IDs like 'rs429358', 'rs113488022'"
                            },
                            "phenotype_terms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Phenotypes like 'cognitive decline', 'motor dysfunction'"
                            },
                            "protein_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Proteins like 'amyloid-beta', 'alpha-synuclein', 'insulin'"
                            },
                            "sequence_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Sequences like 'APOE', 'LRRK2', 'BRAF'"
                            },
                            "species": {
                                "type": "string",
                                "description": "Species name, default 'homo_sapiens'",
                                "default": "homo_sapiens"
                            },
                            "need_trials": {"type": "boolean"},
                            "need_pubmed": {"type": "boolean"},
                            "need_ensembl": {"type": "boolean"},
                            "need_uniprot": {"type": "boolean"},
                            "need_genbank": {"type": "boolean"},
                            "need_protein_atlas": {"type": "boolean"},
                            "need_array_express": {"type": "boolean"},
                            "need_geo": {"type": "boolean"}
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

    def count_tokens(self, text):
        """Rough token estimation: ~4 chars = 1 token"""
        return len(text) // 4
    
    def trim_chat_history(self, chat_history, max_tokens=2000):
        """Keep chat history under token limit"""
        if not chat_history:
            return chat_history
            
        total_tokens = 0
        trimmed_history = []
        
        # Process messages in reverse order to keep most recent ones
        for message in reversed(chat_history):
            msg_tokens = self.count_tokens(message.get('content', ''))
            if total_tokens + msg_tokens > max_tokens:
                break
            trimmed_history.insert(0, message)
            total_tokens += msg_tokens
        
        logger.info(f"Trimmed chat history from {len(chat_history)} to {len(trimmed_history)} messages, using {total_tokens} tokens")
        return trimmed_history

    def truncate_content(self, content, max_length=500):
        """Truncate long content with ellipsis"""
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content

    def normalize_query_terms(self, term):
        """Normalize query terms for API compatibility."""
        term = term.lower()
        term = re.sub(r'’s', 's', term)  # Convert "Alzheimer’s" to "Alzheimers"
        term = re.sub(r'[^\w\s]', ' ', term)  # Remove special characters
        term = re.sub(r'\s+', ' ', term).strip()  # Normalize spaces
        # Map common terms to API-friendly versions
        term_map = {
            "alzheimers disease": "alzheimer disease",
            "parkinsons disease": "parkinson disease",
            "preclinical ad": "alzheimer disease preclinical"
        }
        return term_map.get(term, term)

    def analyze_query(self, user_query, chat_history=None):
        try:
            apis_called = []
            combined_info = ""
            references = []

            logger.info(f"Processing query: {user_query}")
            logger.info(f"Chat history: {chat_history}")

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert medical query analyzer. Extract comprehensive keywords and set appropriate API flags:\n"
                        "**Extract Keywords**: disease_keywords (conditions, syndromes), treatment_keywords (therapies, drugs, interventions), "
                        "gene_symbols (APOE, BRCA1), variant_ids (rs numbers), phenotype_terms (symptoms, outcomes), "
                        "protein_keywords (enzymes, biomarkers), sequence_keywords (DNA/RNA sequences), species (default: homo_sapiens)\n"
                        "**Set API Flags**: need_trials (clinical studies), need_pubmed (research literature), need_ensembl (genomics), "
                        "need_uniprot (proteins), need_genbank (sequences), need_protein_atlas, need_array_express, need_geo\n"
                        "**Tools**: Use 'get_clinical_trials' for trial-only queries, 'get_research_and_trials' for comprehensive searches\n"
                        "**Context**: Analyze chat history for follow-up questions - inherit relevant keywords from previous exchanges"
                    )
                }
            ]

            if chat_history:
                chat_history = self.trim_chat_history(chat_history, max_tokens=1500)  # Conservative limit for analyze_query
                messages.extend(chat_history)
            messages.append({"role": "user", "content": user_query})

            logger.debug(f"Messages sent to OpenAI: {messages}")

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=self.analyze_tools,
                temperature=0.7
            )

            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                logger.info(f"Tool call: {tool_name}, Arguments: {args}")

                # Initialize common terms
                condition_terms = " OR ".join([self.normalize_query_terms(k) for k in args["disease_keywords"]]) if args["disease_keywords"] else ""
                treatment_terms = " OR ".join(args["treatment_keywords"]) if args["treatment_keywords"] else ""

                # Initialize tool-specific terms
                protein_terms = ""
                sequence_terms = ""
                species = "homo_sapiens"  # Default species
                if tool_name == "get_research_and_trials":
                    protein_terms = " OR ".join(args["protein_keywords"]) if args.get("protein_keywords") else ""
                    sequence_terms = " OR ".join(args["sequence_keywords"]) if args.get("sequence_keywords") else ""
                    species = args.get("species", "homo_sapiens")

                if tool_name == "get_clinical_trials" and args.get("need_trials"):
                    try:
                        apis_called.append("Clinical Trials")
                        trials_results = search_clinical_trials(condition_terms, treatment_terms, max_results=3)
                        if trials_results:
                            combined_info += "## Clinical Trials\n\n"
                            for trial in trials_results:
                                combined_info += f"**Title:** {trial['title']}\n"
                                combined_info += f"**Status:** {trial['status']}\n"
                                combined_info += f"**Phase:** {trial.get('phase', 'Not specified')}\n"
                                combined_info += f"**Interventions:** {', '.join(trial.get('interventions', ['Not specified']))}\n"
                                combined_info += f"**Description:** {self.truncate_content(trial.get('description', 'No description available'), 300)}\n"
                                combined_info += f"**NCT ID:** {trial['nct_id']}\n\n"
                                references.append(f"Clinical Trial: {trial['title']} (NCT{trial['nct_id']}), [https://clinicaltrials.gov/study/{trial['nct_id']}](https://clinicaltrials.gov/study/{trial['nct_id']})")
                        else:
                            combined_info += "## Clinical Trials\n\nNo results found from ClinicalTrials.gov.\n\n"
                        logger.info(f"Clinical Trials results: {trials_results}")
                    except Exception as e:
                        logger.error(f"Clinical Trials API failed: {str(e)}")
                        combined_info += "## Clinical Trials\n\nNo results found. Try searching [ClinicalTrials.gov](https://clinicaltrials.gov).\n\n"
                        references.append(f"ClinicalTrials.gov Search: {condition_terms} {treatment_terms}, [https://clinicaltrials.gov/search?term={urllib.parse.quote(condition_terms + ' ' + treatment_terms)}](https://clinicaltrials.gov/search?term={urllib.parse.quote(condition_terms + ' ' + treatment_terms)})")

                elif tool_name == "get_research_and_trials":
                    if args.get("need_pubmed"):
                        try:
                            apis_called.append("PubMed")
                            search_query = f"{treatment_terms} {condition_terms}".strip()
                            pubmed_results = search_pubmed(search_query, api_key=os.getenv("PUBMED_API_KEY", ""), max_results=2)
                            if pubmed_results:
                                combined_info += "## Research Papers\n\n"
                                for paper in pubmed_results:
                                    combined_info += f"**Title:** {paper['title']}\n"
                                    combined_info += f"**Abstract:** {self.truncate_content(paper['abstract'], 400)}\n"
                                    combined_info += f"**PMID:** {paper['pmid']}\n\n"
                                    references.append(f"PubMed: {paper['title']} (PMID: {paper['pmid']}), [https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']})")
                            else:
                                combined_info += "## Research Papers\n\nNo results found from PubMed.\n\n"
                            logger.info(f"PubMed results: {pubmed_results}")
                        except Exception as e:
                            logger.error(f"PubMed API failed: {str(e)}")
                            combined_info += "## Research Papers\n\nNo results found. Try searching [PubMed](https://pubmed.ncbi.nlm.nih.gov).\n\n"
                            references.append(f"PubMed Search: {condition_terms} {treatment_terms}, [https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(search_query)}](https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(search_query)})")

                    if args.get("need_trials"):
                        try:
                            apis_called.append("Clinical Trials")
                            trials_results = search_clinical_trials(condition_terms, treatment_terms, max_results=3)
                            if trials_results:
                                combined_info += "## Clinical Trials\n\n"
                                for trial in trials_results:
                                    combined_info += f"**Title:** {trial['title']}\n"
                                    combined_info += f"**Status:** {trial['status']}\n"
                                    combined_info += f"**Phase:** {trial.get('phase', 'Not specified')}\n"
                                    combined_info += f"**Interventions:** {', '.join(trial.get('interventions', ['Not specified']))}\n"
                                    combined_info += f"**Description:** {self.truncate_content(trial.get('description', 'No description available'), 300)}\n"
                                    combined_info += f"**NCT ID:** {trial['nct_id']}\n\n"
                                    references.append(f"Clinical Trial: {trial['title']} (NCT{trial['nct_id']}), [https://clinicaltrials.gov/study/{trial['nct_id']}](https://clinicaltrials.gov/study/{trial['nct_id']})")
                            else:
                                combined_info += "## Clinical Trials\n\nNo results found from ClinicalTrials.gov.\n\n"
                            logger.info(f"Clinical Trials results: {trials_results}")
                        except Exception as e:
                            logger.error(f"Clinical Trials API failed: {str(e)}")
                            combined_info += "## Clinical Trials\n\nNo results found. Try searching [ClinicalTrials.gov](https://clinicaltrials.gov).\n\n"
                            references.append(f"ClinicalTrials.gov Search: {condition_terms} {treatment_terms}, [https://clinicaltrials.gov/search?term={urllib.parse.quote(condition_terms + ' ' + treatment_terms)}](https://clinicaltrials.gov/search?term={urllib.parse.quote(condition_terms + ' ' + treatment_terms)})")

                    if args.get("need_ensembl") and (args.get("gene_symbols") or args.get("variant_ids") or args.get("phenotype_terms")):
                        try:
                            apis_called.append("Ensembl")
                            gene_results = []
                            for symbol in args["gene_symbols"]:
                                gene_results.extend(self.ensembl_service.search_gene_by_symbol(species, symbol))
                            if gene_results:
                                combined_info += "## Genomic Information\n\n"
                                for gene in gene_results:
                                    combined_info += f"**Gene:** {gene['symbol']} ({gene['id']})\n"
                                    combined_info += f"**Description:** {gene['description']}\n"
                                    combined_info += f"**Biotype:** {gene['biotype']}\n"
                                    combined_info += f"**Location:** {gene['chromosome']}:{gene['start']}-{gene['end']} ({gene['strand']})\n\n"
                                    references.append(f"Ensembl: {gene['symbol']} ({gene['id']}), [https://ensembl.org/Homo_sapiens/Gene/Summary?g={gene['id']}](https://ensembl.org/Homo_sapiens/Gene/Summary?g={gene['id']})")
                            logger.info(f"Ensembl gene results: {gene_results}")

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
                                    references.append(f"Ensembl Variant: {variant['variant_id']}, [https://ensembl.org/Homo_sapiens/Variation/Explore?v={variant['variant_id']}]https://ensembl.org/Homo_sapiens/Variation/Explore?v={variant['variant_id']})")
                            logger.info(f"Ensembl variant results: {variant_results}")

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
                                    references.append(f"Ensembl Phenotype: {p['gene_symbol']} - {p['phenotype_description']}, [{p['source']}]({p['source']})")
                            logger.info(f"Ensembl phenotype results: {phenotype_results}")
                        except Exception as e:
                            logger.error(f"Ensembl API failed: {str(e)}")
                            combined_info += "## Genomic Information\n\nNo results found. Try searching [Ensembl](https://ensembl.org).\n\n"
                            references.append(f"Ensembl Search: {args['gene_symbols'][0] if args.get('gene_symbols') else condition_terms}, [https://ensembl.org](https://ensembl.org)")

                    if args.get("need_uniprot") and args.get("protein_keywords"):
                        try:
                            apis_called.append("UniProt")
                            uniprot_query = f"{protein_terms} {species}".strip()
                            uniprot_results = self.uniprot_service.search_uniprot(uniprot_query, max_results=3)
                            if uniprot_results:
                                combined_info += "## Protein Information (UniProt)\n\n"
                                for protein in uniprot_results:
                                    combined_info += f"**Accession:** {protein['accession']}\n"
                                    combined_info += f"**Protein Name:** {protein['protein_name']}\n"
                                    combined_info += f"**Organism:** {protein['organism']}\n"
                                    combined_info += f"**Function:** {protein.get('function', 'Not specified')}\n\n"
                                    references.append(f"UniProt: {protein['protein_name']} ({protein['accession']}), [https://uniprot.org/uniprot/{protein['accession']}](https://uniprot.org/uniprot/{protein['accession']})")
                            logger.info(f"UniProt results: {uniprot_results}")
                        except Exception as e:
                            logger.error(f"UniProt API failed: {str(e)}")
                            combined_info += "## Protein Information (UniProt)\n\nNo results found. Try searching [UniProt](https://uniprot.org).\n\n"
                            references.append(f"UniProt Search: {protein_terms}, [https://uniprot.org](https://uniprot.org)")

                    if args.get("need_protein_atlas") and (args.get("protein_keywords") or args.get("gene_symbols")):
                        try:
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
                                protein_query = f"{protein_terms} {species}".strip()
                                results = self.protein_atlas_service.search_protein_atlas(protein_query, max_results=3)
                                protein_atlas_results.extend(results)
                            if protein_atlas_results:
                                combined_info += "## Protein Information (HPA)\n\n"
                                for protein in protein_atlas_results:
                                    combined_info += f"**Gene:** {protein['gene']}\n"
                                    combined_info += f"**Ensembl ID:** {protein['ensembl_id']}\n"
                                    combined_info += f"**Tissue Expression:** {protein['tissue_expression']}\n"
                                    combined_info += f"**Pathology:** {protein['pathology']}\n"
                                    combined_info += f"**Subcellular Location:** {protein['subcellular_location']}\n\n"
                                    references.append(f"Protein Atlas: {protein['gene']} ({protein['ensembl_id']}), [https://proteinatlas.org/{protein['ensembl_id']}](https://proteinatlas.org/{protein['ensembl_id']})")
                            logger.info(f"Protein Atlas results: {protein_atlas_results}")
                        except Exception as e:
                            logger.error(f"Protein Atlas API failed: {str(e)}")
                            combined_info += "## Protein Information (HPA)\n\nNo results found. Try searching [Protein Atlas](https://proteinatlas.org).\n\n"
                            references.append(f"Protein Atlas Search: {protein_terms or args['gene_symbols'][0] if args.get('gene_symbols') else condition_terms}, [https://proteinatlas.org](https://proteinatlas.org)")

                    if args.get("need_array_express") and (args.get("protein_keywords") or args.get("gene_symbols") or "biomarkers" in user_query.lower() or "studies" in user_query.lower()):
                        try:
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
                            if not array_express_results:
                                results = self.array_express_service.search_array_express(condition_terms, max_results=3)
                                array_express_results.extend(results)
                            if array_express_results:
                                combined_info += "## Study Information (ArrayExpress)\n\n"
                                for study in array_express_results:
                                    combined_info += f"**Accession:** {study['accession']}\n"
                                    combined_info += f"**Title:** {study['title']}\n"
                                    combined_info += f"**Description:** {study['description']}\n"
                                    combined_info += f"**Assay Count:** {study['assay_count']}\n"
                                    combined_info += f"**Study Type:** {study['study_type']}\n\n"
                                    references.append(f"ArrayExpress: {study['title']} ({study['accession']}), [https://ebi.ac.uk/arrayexpress/experiments/{study['accession']}](https://ebi.ac.uk/arrayexpress/experiments/{study['accession']})")
                            logger.info(f"ArrayExpress results: {array_express_results}")
                        except Exception as e:
                            logger.error(f"ArrayExpress API failed: {str(e)}")
                            combined_info += "## Study Information (ArrayExpress)\n\nNo results found. Try searching [ArrayExpress](https://ebi.ac.uk/arrayexpress).\n\n"
                            references.append(f"ArrayExpress Search: {condition_terms}, [https://ebi.ac.uk/arrayexpress](https://ebi.ac.uk/arrayexpress)")

                    if args.get("need_geo") and (args.get("protein_keywords") or args.get("gene_symbols") or "biomarkers" in user_query.lower() or "studies" in user_query.lower()):
                        try:
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
                            if not geo_results:
                                results = self.geo_service.search_geo(condition_terms, max_results=3)
                                geo_results.extend(results)
                            if geo_results:
                                combined_info += "## Study Information (GEO)\n\n"
                                for study in geo_results:
                                    combined_info += f"**Accession:** {study['accession']}\n"
                                    combined_info += f"**Title:** {study['title']}\n"
                                    combined_info += f"**Summary:** {study['summary']}\n"
                                    combined_info += f"**Sample Count:** {study['sample_count']}\n"
                                    combined_info += f"**Study Type:** {study['study_type']}\n\n"
                                    references.append(f"GEO: {study['title']} ({study['accession']}), [https://ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={study['accession']}](https://ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={study['accession']})")
                            logger.info(f"GEO results: {geo_results}")
                        except Exception as e:
                            logger.error(f"GEO API failed: {str(e)}")
                            combined_info += "## Study Information (GEO)\n\nNo results found. Try searching [GEO](https://ncbi.nlm.nih.gov/geo).\n\n"
                            references.append(f"GEO Search: {condition_terms}, [https://ncbi.nlm.nih.gov/geo](https://ncbi.nlm.nih.gov/geo)")

                    if args.get("need_genbank") and args.get("sequence_keywords"):
                        try:
                            apis_called.append("GenBank")
                            genbank_query = f"{sequence_terms} {species}".strip()
                            genbank_results = self.genbank_service.search_genbank(genbank_query, max_results=3)
                            if genbank_results:
                                combined_info += "## Sequence Information\n\n"
                                for sequence in genbank_results:
                                    combined_info += f"**Accession:** {sequence['accession']}\n"
                                    combined_info += f"**Definition:** {sequence['definition']}\n"
                                    combined_info += f"**Organism:** {sequence['organism']}\n\n"
                                    references.append(f"GenBank: {sequence['definition']} ({sequence['accession']}), [https://ncbi.nlm.nih.gov/nuccore/{sequence['accession']}](https://ncbi.nlm.nih.gov/nuccore/{sequence['accession']})")
                            logger.info(f"GenBank results: {genbank_results}")
                        except Exception as e:
                            logger.error(f"GenBank API failed: {str(e)}")
                            combined_info += "## Sequence Information\n\nNo results found. Try searching [GenBank](https://ncbi.nlm.nih.gov/genbank).\n\n"
                            references.append(f"GenBank Search: {sequence_terms}, [https://ncbi.nlm.nih.gov/genbank](https://ncbi.nlm.nih.gov/genbank)")

                logger.info(f"APIs Called: {', '.join(apis_called)}")
                logger.info(f"Combined Info:\n{combined_info}")

                if not combined_info.strip() or combined_info.strip() == "No relevant information found.":
                    logger.info("No API data found, falling back to model knowledge.")
                    response_text = self.generate_response(user_query, use_model_knowledge=True, chat_history=chat_history)
                else:
                    response_text = self.generate_response(user_query, combined_info, references, chat_history=chat_history)

                if chat_history is None:
                    chat_history = []
                chat_history.append({"role": "user", "content": user_query})
                chat_history.append({"role": "assistant", "content": response_text})

                return response_text

            logger.info("No tool calls, using model knowledge.")
            response_text = self.generate_response(user_query, use_model_knowledge=True, chat_history=chat_history)
            if chat_history is None:
                chat_history = []
            chat_history.append({"role": "user", "content": user_query})
            chat_history.append({"role": "assistant", "content": response_text})

            return response_text

        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}")
            return f"An error occurred while processing the query: {str(e)}"
    def generate_response(self, user_query, research_info=None, references=None, use_model_knowledge=False, chat_history=None):
        try:
            logger.info(f"Generating response for query: {user_query}")
            logger.info(f"Research info: {research_info}")
            logger.info(f"References: {references}")
            logger.info(f"Use model knowledge: {use_model_knowledge} - {user_query}")
            logger.info(f"Chat history length: {len(chat_history) if chat_history else 0}")

            messages = [
    {
        "role": "system",
        "content": (
            "You are an expert medical research assistant with comprehensive knowledge across all medical domains. "
            "Provide evidence-based, clinically relevant responses that are:\n"
            "• **Precise & Accurate**: Use current medical evidence, cite specific studies, include statistical data (p-values, effect sizes, confidence intervals)\n"
            "• **Contextually Aware**: Reference previous conversation history, resolve medical abbreviations contextually (e.g., 'AD' = Alzheimer's Disease in neurology contexts)\n"
            "• **Audience-Adapted**: Tailor complexity based on user's apparent expertise level - technical for researchers, accessible for patients\n"
            "• **Structured & Actionable**: Organize with clear sections (Overview, Key Findings, Clinical Trials, Genomic Data, Clinical Implications), include practical recommendations\n"
            "• **Comprehensive**: Cover all relevant aspects - epidemiology, pathophysiology, diagnostics, therapeutics, prognosis\n"
            "• **Current & Validated**: Prioritize recent research, meta-analyses, clinical guidelines, and landmark studies\n"
            "Always include a References section with proper citations. For follow-up questions, build upon previous context."
        )
    }
    # ORIGINAL LONG SYSTEM PROMPT (preserved for reference):
    # {
    #     "role": "system",
    #     "content": (
    #         "You are an expert medical research assistant with access to comprehensive biomedical databases and research resources. "
    #         "Your role is to analyze medical queries and provide evidence-based, clinically relevant responses using the most current research data.\n\n"
    #         "## Response Quality Standards:\n"
    #         "• **Evidence-Based**: Always prioritize peer-reviewed research, clinical trials, and established medical guidelines\n"
    #         "• **Precision & Accuracy**: Include specific statistical data (p-values, effect sizes, confidence intervals) when available\n"
    #         "• **Clinical Relevance**: Focus on actionable insights that have direct implications for patient care or research\n"
    #         "• **Current & Comprehensive**: Synthesize information from multiple sources including recent publications, ongoing trials, and established knowledge\n"
    #         "• **Contextual Awareness**: Consider the user's background and tailor the complexity appropriately\n\n"
    #         "## Information Integration:\n"
    #         "When research data is provided:\n"
    #         "1. **Synthesize** findings from multiple databases (PubMed, Clinical Trials, Genomic databases)\n"
    #         "2. **Cross-reference** different types of evidence (molecular, clinical, epidemiological)\n"
    #         "3. **Identify** knowledge gaps and areas requiring further research\n"
    #         "4. **Contextualize** findings within the broader medical landscape\n"
    #         "5. **Highlight** contradictory evidence and explain potential reasons\n\n"
    #         "## Response Structure:\n"
    #         "Organize responses with clear sections:\n"
    #         "• **Overview**: Brief summary of the condition/topic\n"
    #         "• **Current Research**: Key findings from recent studies\n"
    #         "• **Clinical Trials**: Ongoing or completed trials with outcomes\n"
    #         "• **Molecular/Genetic Insights**: Relevant genomic and proteomic data\n"
    #         "• **Clinical Implications**: Practical applications for diagnosis, treatment, or management\n"
    #         "• **Future Directions**: Emerging research areas and potential developments\n"
    #         "• **References**: Properly formatted citations with links\n\n"
    #         "## Medical Abbreviation Context:\n"
    #         "Resolve abbreviations based on medical context:\n"
    #         "• AD: Alzheimer's Disease (neurology), Atopic Dermatitis (dermatology), Autosomal Dominant (genetics)\n"
    #         "• MS: Multiple Sclerosis (neurology), Mitral Stenosis (cardiology), Mass Spectrometry (research)\n"
    #         "• PD: Parkinson's Disease (neurology), Peritoneal Dialysis (nephrology)\n"
    #         "• Always clarify when ambiguity exists\n\n"
    #         "## Communication Style:\n"
    #         "• **Professional yet accessible**: Use medical terminology appropriately while ensuring clarity\n"
    #         "• **Balanced perspective**: Present both benefits and limitations of treatments/interventions\n"
    #         "• **Patient-centered**: Consider patient experience and quality of life factors\n"
    #         "• **Ethical considerations**: Acknowledge limitations, contraindications, and safety concerns\n\n"
    #         "Always conclude with properly formatted references and suggest additional resources when appropriate."
    #     )
    # }
]

            # Add chat history for context
            if chat_history:
                chat_history = self.trim_chat_history(chat_history, max_tokens=2000)  # More generous for response generation
                messages.extend(chat_history)
            
            messages.append({"role": "user", "content": user_query})

            if research_info and research_info.strip() != "No relevant information found." and not use_model_knowledge:
                messages.append({"role": "user", "content": f"Information retrieved from APIs:\n\n{research_info}"})
            elif use_model_knowledge:
                messages.append({"role": "user", "content": "No API data available. Use your internal knowledge to provide a comprehensive response."})

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )

            response_text = response.choices[0].message.content

            # Append references in Markdown if provided
            if references and not use_model_knowledge:
                response_text += "\n\n## References\n\n"
                for ref in references:
                    response_text += f"- {ref}\n"
            elif use_model_knowledge:
                # Add fallback references for search
                search_terms = urllib.parse.quote(user_query)
                response_text += "\n\n## References\n\n"
                response_text += f"- Based on general medical knowledge.\n"
                response_text += f"- [PubMed Search: {user_query}](https://pubmed.ncbi.nlm.nih.gov/?term={search_terms})\n"
                response_text += f"- [ClinicalTrials.gov Search: {user_query}](https://clinicaltrials.gov/search?term={search_terms})\n"

            return response_text

        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            raise Exception(f"Response generation failed: {str(e)}")