import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
from datetime import datetime, UTC
from src.config import SUBJECTS, DATA_DIR

def parse_arxiv_feed(feed_xml):
    """
    Parse an arXiv Atom XML feed into a list of dictionaries.

    Parameters:
        feed_xml (str): Raw XML string from the arXiv API.

    Returns:
        list[dict]: Parsed papers with metadata.
    """
    root = ET.fromstring(feed_xml)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    papers = []

    for entry in root.findall("atom:entry", ns):
        paper = {}

        paper["id"] = entry.find("atom:id", ns).text if entry.find("atom:id", ns) is not None else None
        paper["title"] = entry.find("atom:title", ns).text.strip() if entry.find("atom:title", ns) is not None else None
        paper["summary"] = entry.find("atom:summary", ns).text.strip() if entry.find("atom:summary", ns) is not None else None
        paper["published"] = entry.find("atom:published", ns).text if entry.find("atom:published", ns) is not None else None
        paper["updated"] = entry.find("atom:updated", ns).text if entry.find("atom:updated", ns) is not None else None

        # authors (list)
        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns)
            if name is not None:
                authors.append(name.text)
        paper["authors"] = authors

        # PDF URL (link with type="application/pdf")
        pdf_url = None
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href")
        paper["pdf_url"] = pdf_url

        papers.append(paper)

    return papers

def get_recent_csse_papers(category:str, max_results=100, start=0):
    """
    Fetch recent arXiv cs.SE papers as an Atom XML string.
    
    Parameters:
        max_results (int): Number of results to return.
        start (int): Starting index for pagination.
        
    Returns:
        str: Raw Atom XML feed from arXiv.
    """
    base_url = "http://export.arxiv.org/api/query?"

    params = {
        "search_query": f"cat:{category}",
        "start": start,
        "max_results": max_results,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending"
    }

    url = base_url + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


if __name__ == "__main__":
    for subject in SUBJECTS:
        feed = get_recent_csse_papers(subject)
        parsed = parse_arxiv_feed(feed)

        if not parsed:
            print(subject, "→ No papers found")
            continue

        # --- Determine the most recent date from the feed ---
        first_date = parsed[0]["updated"][:10]   # YYYY-MM-DD

        # --- Filter papers by this date ---
        filtered = [
            p for p in parsed
            if p["updated"] and p["updated"].startswith(first_date)
        ]

        # --- Write JSONL file named by date ---
        jsonl_filename = DATA_DIR / f"{subject}.{first_date}.jsonl"
        with open(jsonl_filename, "w", encoding="utf-8") as f:
            for item in filtered:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        print(f"Saved {len(filtered)} papers to {jsonl_filename}")

        # --- If date is today, also write today.jsonl ---
        today_str = datetime.now(UTC)
        if first_date == today_str:
            with open(f"{str(DATA_DIR)}/today.jsonl", "w", encoding="utf-8") as f:
                for item in filtered:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

            print(f"Saved {len(filtered)} papers to today.jsonl")

        # Continue loop instead of break


