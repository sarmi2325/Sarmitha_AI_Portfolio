# This file is now deprecated - functionality moved to smart_ai.py
# Keeping for backward compatibility

def retrieve(query, top_k=5):
    """Legacy function - redirects to smart_ai system."""
    try:
        from smart_ai import SmartAIPortfolio
        ai_system = SmartAIPortfolio()
        return ai_system._semantic_retrieve(query, top_k)
    except Exception as e:
        print(f"⚠️ Legacy retrieve failed: {e}")
        return []
