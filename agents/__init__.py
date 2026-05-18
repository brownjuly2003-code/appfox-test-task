"""LangGraph-based supervisor pipeline.

Альтернатива flat-pipeline в run.py. Здесь супервайзер принимает adaptive решения:
- yield_guard: если после clean выживает <30% запросов → расширить modifiers и re-collect (1 попытка)
- size_guard: если после cluster получается <3 кластеров → ослабить distance_threshold (1 попытка)

См. agents/graph.py для схемы и agents/cli.py для запуска.
"""
