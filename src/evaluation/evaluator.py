import time
from typing import List, Dict, Any
from src.evaluation.benchmark_data import BENCHMARK_CASES
from src.retrieval.hybrid_retriever import HybridRetriever
from src.reasoning.openrouter_client import OpenRouterClient

class BenchmarkEvaluator:
    """Automated benchmark evaluator for CounterChain against the 5 landmark exploit cases."""
    def __init__(self, retriever: HybridRetriever, client: OpenRouterClient):
        self.retriever = retriever
        self.client = client

    def evaluate_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Run single benchmark case and measure retrieval accuracy and verdict match."""
        start_time = time.time()
        
        # 1. Hybrid Retrieval
        retrieved_chunks = self.retriever.retrieve(
            query=case["query"],
            top_k=5,
            protocol_filter=None
        )
        
        # Check if target protocol document was retrieved in Top-5
        target_proto = case["protocol"].lower()
        retrieval_success = any(
            target_proto.split()[0] in c.get("protocol", "").lower() 
            for c in retrieved_chunks
        )

        # 2. Counterfactual Reasoning Call
        try:
            response = self.client.analyze_counterfactual(
                query=case["query"],
                retrieved_chunks=retrieved_chunks,
                protocol_hint=case["protocol"]
            )
            model_verdict = response.verdict.value
            confidence_score = response.confidence_score
            executive_summary = response.executive_summary
            divergence_point = response.divergence_point
            recommended_code_patch = response.recommended_code_patch
            residual_risks = response.residual_risks
            gt_verdict = case["ground_truth_verdict"]
            verdict_match = (model_verdict == gt_verdict)
        except Exception as e:
            model_verdict = "API_ERROR"
            confidence_score = 0.0
            executive_summary = f"API Error: {str(e)}"
            divergence_point = "N/A"
            recommended_code_patch = "// Error executing OpenRouter API call"
            residual_risks = [str(e)]
            gt_verdict = case["ground_truth_verdict"]
            verdict_match = False

        latency = round(time.time() - start_time, 2)

        return {
            "case_id": case["id"],
            "protocol": case["protocol"],
            "ground_truth_verdict": gt_verdict,
            "model_verdict": model_verdict,
            "verdict_match": verdict_match,
            "retrieval_success": retrieval_success,
            "confidence_score": confidence_score,
            "latency_seconds": latency,
            "executive_summary": executive_summary,
            "divergence_point": divergence_point,
            "recommended_code_patch": recommended_code_patch,
            "residual_risks": residual_risks
        }

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all 5 benchmark cases and compute aggregate accuracy metrics."""
        results = []
        matches = 0
        retrieval_hits = 0

        for case in BENCHMARK_CASES:
            res = self.evaluate_case(case)
            results.append(res)
            if res["verdict_match"]:
                matches += 1
            if res["retrieval_success"]:
                retrieval_hits += 1

        total = len(BENCHMARK_CASES)
        accuracy = (matches / total) * 100 if total > 0 else 0
        retrieval_rate = (retrieval_hits / total) * 100 if total > 0 else 0

        return {
            "total_cases": total,
            "verdict_accuracy_pct": round(accuracy, 1),
            "retrieval_precision_pct": round(retrieval_rate, 1),
            "cases_evaluated": results
        }
