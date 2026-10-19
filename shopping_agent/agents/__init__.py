# -*- coding: utf-8 -*-
"""shopping_agent/agents/__init__.py"""
from shopping_agent.agents.similar_agent import SimilarRecAgent
from shopping_agent.agents.compare_agent import SkuCompAgent
from shopping_agent.agents.shopping_agent import SearchRecommendAgent
from shopping_agent.agents.repurchase_agent import RepurchaseAgent
from shopping_agent.agents.matching_agent import MatchingAgent
from shopping_agent.agents.bundle_agent import BundleAgent
from shopping_agent.agents.order_agent import OrderAgent

__all__ = [
    "SimilarRecAgent", "SkuCompAgent", "SearchRecommendAgent",
    "RepurchaseAgent", "MatchingAgent", "BundleAgent", "OrderAgent",
]
