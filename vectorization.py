import re
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from api_requests import api_request

def split_text_with_overlap(text, chunk_size=2048, overlap_size=512):
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks, current_chunk = [], ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = " ".join(current_chunk.split()[-overlap_size:] + [sentence])
        else:
            current_chunk += " " + sentence if current_chunk else sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def vectorize_text(text, iam_token):
    url_embedding = 'https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding'
    headers_embedding = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }

    embeddings = []
    chunks = split_text_with_overlap(text)
    for part in chunks:
        if part.strip():
            data_embedding = {
                "modelUri": "emb://b1gjp5vama10h4due384/text-search-doc/latest",
                "text": part
            }
            logging.info("Данные для векторизации: %s", data_embedding)

            result = api_request(url_embedding, headers_embedding, data_embedding)
            if result and 'embedding' in result:
                embeddings.append((result['embedding'], part))
    return embeddings

def vectorize_query(query, iam_token):
    url_embedding = 'https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding'
    headers_embedding = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }

    data_embedding = {
        "modelUri": "emb://b1gjp5vama10h4due384/text-search-doc/latest",
        "text": query
    }

    result = api_request(url_embedding, headers_embedding, data_embedding)
    return result.get('embedding') if result and 'embedding' in result else None

def find_best_match(query_embedding, embeddings):
    similarities = [
        (cosine_similarity([query_embedding], [embedding])[0][0], text)
        for embedding, text in embeddings
    ]
    similarities.sort(reverse=True, key=lambda x: x[0])
    return similarities[0][1] if similarities else "Нет подходящего ответа."