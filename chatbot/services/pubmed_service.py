import requests
from xml.etree import ElementTree

def search_pubmed(query, api_key, max_results=10):
    """
    Search PubMed using the E-utilities API and return results.

    Parameters:
        query (str): The search query (e.g., "GLP-1 receptor agonists CKD HF CVD").
        api_key (str): Your NCBI API key.
        max_results (int): Maximum number of results to fetch.

    Returns:
        list: A list of dictionaries with PubMed IDs, titles, and abstracts.
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # Step 1: Search for articles using `esearch`
    search_url = f"{base_url}esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        # "api_key": api_key,
        "retmode": "json"
    }
    search_response = requests.get(search_url, params=search_params)
    search_response.raise_for_status()
    search_data = search_response.json()
    
    # Extract PubMed IDs (PMIDs)
    pmids = search_data.get("esearchresult", {}).get("idlist", [])
    
    if not pmids:
        return []
    
    # Step 2: Fetch details for the articles using `efetch`
    fetch_url = f"{base_url}efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        # "api_key": api_key
    }
    fetch_response = requests.get(fetch_url, params=fetch_params)
    fetch_response.raise_for_status()
    
    # Parse XML response
    root = ElementTree.fromstring(fetch_response.content)
    articles = []
    
    for article in root.findall(".//PubmedArticle"):
        title = article.find(".//ArticleTitle").text
        abstract = article.find(".//Abstract/AbstractText")
        abstract_text = abstract.text if abstract is not None else "No abstract available."
        pmid = article.find(".//PMID").text
        
        articles.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract_text
        })
    return articles

# # Example Usage
# api_key = "your_ncbi_api_key_here"  # Replace with your NCBI API key
# query = "GLP-1 receptor agonists AND CKD AND HF AND CVD"
# print("Calling")
# results = search_pubmed(query, api_key)

# for article in results:
#     print(f"PMID: {article['pmid']}")
#     print(f"Title: {article['title']}")
#     print(f"Abstract: {article['abstract']}")
#     print("="*80)
