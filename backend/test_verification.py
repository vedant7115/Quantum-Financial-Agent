# test_verification.py
# Verification script to test that all backend services and agents function end-to-end.
# Run this within the backend directory: python test_verification.py

import sys
import os
import io

# Ensure UTF-8 output encoding across all operating system terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add current backend directory and load environment variables
backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))
load_dotenv(os.path.join(backend_dir, "..", ".env"))

print("Python path configured. Testing imports...")

try:
    from services import stock_service, news_service, research_engine
    from agents import technical_agent, fundamental_agent, sentiment_agent, master_agent
    print("Success: All modules imported cleanly.")
except Exception as e:
    print(f"Error during imports: {str(e)}")
    sys.exit(1)

def run_test(symbol):
    """Runs the v2 pipeline (data -> evidence engine -> agents -> master brief) for one symbol."""
    print(f"\n--- Testing Symbol: {symbol} ---")
    try:
        resolved = stock_service.resolve_symbol(symbol)
        print(f"1. Resolved Ticker: {resolved}")

        stock_data = stock_service.get_stock_data(resolved)
        print(f"2. Stock Data: Price: {stock_data['price']}, Change: {stock_data['change_pct']}%, "
              f"Currency: {stock_data.get('currency')}")

        news_data = news_service.get_news(resolved, stock_data.get("name", ""))
        print(f"3. News Headlines: {news_data['total_articles']} articles from {news_data['source']}")
        for a in news_data.get("articles", [])[:2]:
            print(f"   - [{a.get('sentiment')}] {a.get('title')}")

        research = research_engine.build(resolved, stock_data, news_data.get("articles", []))
        print(f"4. Evidence engine: composite {research['composite']}/100, bias {research['bias']}, "
              f"confidence {research['confidence']}%, risk {research['risk']}, conflicted {research['conflicted']}")
        print(f"   - Pillars: " + ", ".join(f"{p['label']} {p['score']}" for p in research["scorecard"]))
        print(f"   - Coverage: {research['coverage']}")

        tech_res = technical_agent.analyze(stock_data, research)
        print(f"5. Technical Agent: {tech_res['trend']} (score {tech_res['score']}, strength {tech_res['trend_strength']})")

        fund_res = fundamental_agent.analyze(stock_data, research)
        print(f"6. Fundamental Agent: {fund_res['fundamental']} (score {fund_res['score']}, "
              f"P/E {fund_res['metrics']['pe_ratio']})")

        sent_res = sentiment_agent.analyze(news_data)
        print(f"7. Sentiment Agent: {sent_res['sentiment']} (confidence {sent_res['confidence']}%)")

        master_res = master_agent.analyze(tech_res, fund_res, sent_res, research, request_id="manual-check")
        llm = master_res.pop("llm")
        print(f"8. Master brief: bias {master_res['market_bias']}, confidence {master_res['confidence']}%, "
              f"outcome {llm['outcome']}, model {llm['model']}, prompt {llm['prompt_version']}, "
              f"tokens {llm['usage']['total_tokens']}")
        if llm["rejections"]:
            print(f"   - Rejections: {llm['rejections']}")
        print(f"   - Summary: {master_res['summary'][:150]}...")

        print(f"\nSUCCESS: End-to-end verification completed for {symbol}.")
        return True
    except Exception as e:
        print(f"FAILURE: Exception encountered during test execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    results = [run_test("AAPL"), run_test("INFY")]
    sys.exit(0 if all(results) else 1)
