"""
模拟论文数据

包含 10 篇不同领域的论文，用于测试。
"""

import uuid
from typing import List

from app.schemas.paper import Paper


def generate_mock_papers() -> List[Paper]:
    """生成 10 篇不同领域的模拟论文"""
    papers_data = [
        {
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.",
            "year": 2017,
            "venue": "NeurIPS",
            "citation_count": 120000,
            "doi": "10.48550/arXiv.1706.03762",
            "source": "semantic_scholar",
            "fields_of_study": ["Computer Science"],
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee"],
            "abstract": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers.",
            "year": 2019,
            "venue": "NAACL",
            "citation_count": 80000,
            "doi": "10.18653/v1/N19-1423",
            "source": "semantic_scholar",
            "fields_of_study": ["Computer Science"],
        },
        {
            "title": "Deep Residual Learning for Image Recognition",
            "authors": ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren"],
            "abstract": "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously.",
            "year": 2016,
            "venue": "CVPR",
            "citation_count": 180000,
            "doi": "10.1109/CVPR.2016.90",
            "source": "openalex",
            "fields_of_study": ["Computer Science"],
        },
        {
            "title": "Generative Adversarial Nets",
            "authors": ["Ian Goodfellow", "Jean Pouget-Abadie", "Mehdi Mirza"],
            "abstract": "We propose a new framework for estimating generative models via an adversarial process, in which we simultaneously train two models.",
            "year": 2014,
            "venue": "NeurIPS",
            "citation_count": 60000,
            "doi": "10.48550/arXiv.1406.2661",
            "source": "crossref",
            "fields_of_study": ["Computer Science", "Mathematics"],
        },
        {
            "title": "CRISPR-Cas9: A Revolutionary Tool for Genome Editing",
            "authors": ["Jennifer Doudna", "Emmanuelle Charpentier"],
            "abstract": "CRISPR-Cas9 is a revolutionary genome editing tool that allows researchers to precisely alter DNA sequences and modify gene function.",
            "year": 2014,
            "venue": "Science",
            "citation_count": 15000,
            "doi": "10.1126/science.1258096",
            "source": "semantic_scholar",
            "fields_of_study": ["Biology", "Medicine"],
        },
        {
            "title": "Climate Change 2023: Synthesis Report",
            "authors": ["IPCC"],
            "abstract": "This report synthesizes the key findings of the Sixth Assessment Report on climate change, including observed changes, impacts, and future projections.",
            "year": 2023,
            "venue": "IPCC",
            "citation_count": 500,
            "doi": "10.59327/IPCC/AR6-9789291691647",
            "source": "openalex",
            "fields_of_study": ["Environmental Science"],
        },
        {
            "title": "Quantum Computing: An Overview",
            "authors": ["John Preskill"],
            "abstract": "We provide an introduction to quantum computing, including the basic principles of quantum mechanics, quantum gates, and quantum algorithms.",
            "year": 2018,
            "venue": "Quantum",
            "citation_count": 3000,
            "doi": "10.22331/q-2018-08-06-79",
            "source": "crossref",
            "fields_of_study": ["Physics", "Computer Science"],
        },
        {
            "title": "The Structure of Scientific Revolutions",
            "authors": ["Thomas Kuhn"],
            "abstract": "A scientific revolution occurs when a new paradigm replaces an old one, fundamentally changing the way scientists view the world.",
            "year": 1962,
            "venue": "University of Chicago Press",
            "citation_count": 45000,
            "doi": None,
            "source": "openalex",
            "fields_of_study": ["Philosophy", "History"],
        },
        {
            "title": "Economic Growth and Income Inequality",
            "authors": ["Simon Kuznets"],
            "abstract": "This paper examines the relationship between economic growth and income inequality, proposing the Kuznets curve hypothesis.",
            "year": 1955,
            "venue": "American Economic Review",
            "citation_count": 12000,
            "doi": None,
            "source": "crossref",
            "fields_of_study": ["Economics"],
        },
        {
            "title": "GPT-4 Technical Report",
            "authors": ["OpenAI"],
            "abstract": "We report the development of GPT-4, a large-scale, multimodal model which can accept image and text inputs and produce text outputs.",
            "year": 2023,
            "venue": "OpenAI",
            "citation_count": 5000,
            "doi": "10.48550/arXiv.2303.08774",
            "source": "semantic_scholar",
            "fields_of_study": ["Computer Science"],
        },
    ]

    papers = []
    for data in papers_data:
        paper = Paper(
            id=uuid.uuid4(),
            title=data["title"],
            authors=data["authors"],
            abstract=data["abstract"],
            year=data["year"],
            venue=data["venue"],
            citation_count=data["citation_count"],
            doi=data["doi"],
            url=f"https://example.com/{uuid.uuid4().hex[:8]}",
            pdf_url=None,
            source=data["source"],
            is_open_access=False,
        )
        papers.append(paper)

    return papers
