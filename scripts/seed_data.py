"""
种子数据脚本

用于填充测试数据
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import async_session_factory, init_db
from app.models import PaperEntity, SearchRun


SAMPLE_PAPERS = [
    {
        "title": "Attention Is All You Need",
        "authors": [
            {"name": "Ashish Vaswani", "affiliation": "Google Brain"},
            {"name": "Noam Shazeer", "affiliation": "Google Brain"},
            {"name": "Niki Parmar", "affiliation": "Google Brain"},
        ],
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.",
        "year": 2017,
        "venue": "NeurIPS",
        "doi": "10.48550/arXiv.1706.03762",
        "citation_count": 90000,
        "source": "semantic_scholar",
        "is_open_access": True,
        "fields_of_study": ["Computer Science"],
        "keywords": ["transformer", "attention", "neural machine translation"],
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": [
            {"name": "Jacob Devlin", "affiliation": "Google AI Language"},
            {"name": "Ming-Wei Chang", "affiliation": "Google AI Language"},
            {"name": "Kenton Lee", "affiliation": "Google AI Language"},
        ],
        "abstract": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.",
        "year": 2019,
        "venue": "NAACL",
        "doi": "10.18653/v1/N19-1423",
        "citation_count": 75000,
        "source": "semantic_scholar",
        "is_open_access": True,
        "fields_of_study": ["Computer Science"],
        "keywords": ["BERT", "pre-training", "language model", "NLP"],
    },
    {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": [
            {"name": "Kaiming He", "affiliation": "Microsoft Research"},
            {"name": "Xiangyu Zhang", "affiliation": "Microsoft Research"},
            {"name": "Shaoqing Ren", "affiliation": "Microsoft Research"},
        ],
        "abstract": "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions.",
        "year": 2016,
        "venue": "CVPR",
        "doi": "10.1109/CVPR.2016.90",
        "citation_count": 160000,
        "source": "semantic_scholar",
        "is_open_access": True,
        "fields_of_study": ["Computer Science"],
        "keywords": ["residual learning", "deep learning", "image recognition", "CNN"],
    },
]


async def seed_papers():
    """填充论文数据"""
    async with async_session_factory() as session:
        for paper_data in SAMPLE_PAPERS:
            paper = PaperEntity(**paper_data)
            session.add(paper)

        await session.commit()
        print(f"Added {len(SAMPLE_PAPERS)} papers")


async def main():
    """主函数"""
    print("Initializing database...")
    await init_db()

    print("Seeding papers...")
    await seed_papers()

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
