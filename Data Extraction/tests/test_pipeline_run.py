
import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

print("Step 1: Imports")
try:
    from src.layout_parser import LayoutParser
    print("   -> LayoutParser Imported")
    from src.context_classifier import ContextClassifier
    print("   -> ContextClassifier Imported")
    from src.dili_extractor import DILIExtractor
    print("   -> DILIExtractor Imported")
    from src.validator import Validator
    print("   -> Validator Imported")
    from src.paragraph_extractor import ParagraphExtractor
    print("   -> ParagraphExtractor Imported")
    from src.logic.graph_builder import GraphBuilder
    print("   -> GraphBuilder Imported")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 2: Initialization")
try:
    print("   -> Init LayoutParser...")
    lp = LayoutParser()
    print("   -> Init ContextClassifier...")
    cc = ContextClassifier()
    print("   -> Init DILIExtractor...")
    de = DILIExtractor()
    print("   -> Init Validator...")
    v = Validator()
    print("   -> Init ParagraphExtractor...")
    pe = ParagraphExtractor()
    print("   -> Init GraphBuilder...")
    gb = GraphBuilder()
    print("INITIALIZATION COMPLETE")
except Exception as e:
    print(f"INIT ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
