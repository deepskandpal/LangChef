"""A small retrieval-augmented app with known ground truth, used to test LangChef itself.

Everything here is deterministic and offline. The point is not to build a good
RAG system — it is to have one whose failures we planted ourselves, so we can
ask whether LangChef detects them, and at what sample size.
"""
