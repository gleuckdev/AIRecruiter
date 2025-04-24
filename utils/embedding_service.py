# utils/embedding_service.py
import json
import logging
import hashlib
import numpy as np
from utils.job_analyzer import generate_embedding
from utils.matching_engine import calculate_embedding_similarity
from models import db, JobToken, Job

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def store_embedding(vector):
    """Convert embedding vector to JSON string for storage"""
    try:
        if isinstance(vector, np.ndarray):
            return json.dumps(vector.tolist())
        return json.dumps(vector)
    except Exception as e:
        logger.error(f"Failed to store embedding: {str(e)}")
        return json.dumps([])

def load_embedding(vector_str):
    """Load embedding vector from JSON string"""
    try:
        if not vector_str:
            return []
        return np.array(json.loads(vector_str))
    except Exception as e:
        logger.error(f"Failed to load embedding: {str(e)}")
        return np.array([])

def clean_text(text):
    """Normalize text for consistent token generation"""
    if not text:
        return ""
    return text.lower().strip()

def generate_token_hash(title, location):
    """Generate a unique hash for job token based on title and location"""
    normalized_text = f"{clean_text(title)}_{clean_text(location)}"
    return hashlib.sha256(normalized_text.encode()).hexdigest()

def find_or_create_job_token(title, location, description):
    """Find an existing job token or create a new one"""
    try:
        # Get similarity threshold for job token matching
        SIMILARITY_THRESHOLD = 0.7  # Lower threshold to catch more similar jobs
        
        logger.debug(f"Finding token for job: {title} in {location}")
        
        # Generate embedding for the current job description
        job_embedding = generate_embedding(description)
        logger.debug(f"Generated embedding for job description")
        
        # First check for exact match based on token hash
        token_hash = generate_token_hash(title, location)
        token = JobToken.query.filter_by(token_hash=token_hash).first()
        
        if token:
            # Found exact match, update job count
            logger.debug(f"Found exact token match: {token.id} - {token.base_title}")
            token.job_count += 1
            db.session.commit()
            return token
        
        # If no exact match, look for similar jobs based on embedding
        # Get all job tokens
        job_tokens = JobToken.query.all()
        logger.debug(f"No exact match found. Checking {len(job_tokens)} existing tokens for similarity")
        
        best_match = None
        best_similarity = 0
        
        # Check for location match first (city is important for job relevance)
        location_matches = []
        norm_location = clean_text(location)
        
        for t in job_tokens:
            if clean_text(t.base_location) == norm_location:
                location_matches.append(t)
        
        # If we have location matches, check only those for embeddings similarity
        # Otherwise check all tokens
        tokens_to_check = location_matches if location_matches else job_tokens
        logger.debug(f"Found {len(tokens_to_check)} tokens to check for location: {norm_location}")
        
        for t in tokens_to_check:
            token_embedding = load_embedding(t.description_vector)
            similarity = calculate_embedding_similarity(job_embedding, token_embedding)
            logger.debug(f"Token {t.id} ({t.base_title}) similarity: {similarity:.4f}")
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = t
        
        # If we found a similar job above the threshold, use that token
        if best_match and best_similarity >= SIMILARITY_THRESHOLD:
            logger.debug(f"Found similar job token with similarity: {best_similarity:.4f} - ID: {best_match.id}, Title: {best_match.base_title}")
            best_match.job_count += 1
            db.session.commit()
            return best_match
        
        # Otherwise create a new token
        logger.debug(f"No similar tokens found above threshold {SIMILARITY_THRESHOLD}, creating new token")
        new_token = JobToken(
            token_hash=token_hash,
            base_title=clean_text(title),
            base_location=clean_text(location),
            description_vector=store_embedding(job_embedding),
            job_count=1
        )
        
        db.session.add(new_token)
        db.session.commit()
        logger.debug(f"Created new token with ID: {new_token.id}")
        return new_token
        
    except Exception as e:
        logger.error(f"Error creating job token: {str(e)}")
        db.session.rollback()
        return None

def find_similar_jobs(description, threshold=0.7, limit=5):
    """Find similar jobs based on description embedding similarity"""
    try:
        # Generate embedding for the new description
        new_embedding = generate_embedding(description)
        
        # Get all job tokens
        job_tokens = JobToken.query.all()
        
        similar_tokens = []
        
        for token in job_tokens:
            token_embedding = load_embedding(token.description_vector)
            similarity = calculate_embedding_similarity(new_embedding, token_embedding)
            
            # Add to similar tokens even with a lower threshold
            if similarity >= threshold:
                similar_tokens.append({
                    'token': token,
                    'similarity': similarity
                })
        
        # Sort by similarity
        similar_tokens.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Get the top matches
        return similar_tokens[:limit]
        
    except Exception as e:
        logger.error(f"Error finding similar jobs: {str(e)}")
        return []

def get_job_token_insights(location=None, title=None):
    """Get insights about job tokens, optionally filtered by location or title"""
    try:
        query = JobToken.query
        
        if location:
            query = query.filter_by(base_location=clean_text(location))
        if title:
            query = query.filter(JobToken.base_title.ilike(f"%{clean_text(title)}%"))
        
        results = []
        for token in query.all():
            # Get all jobs for this token
            jobs = Job.query.filter_by(token_id=token.id).all()
            
            results.append({
                'title': token.base_title,
                'location': token.base_location,
                'total_jobs': token.job_count,
                'unique_recruiters': len(set(job.recruiter_id for job in jobs)),
                'token_id': token.id,
                'created_at': token.created_at
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting job token insights: {str(e)}")
        return []