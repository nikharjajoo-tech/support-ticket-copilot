"""Reproduces how the 50-ticket golden set was sampled from the Bitext dataset.

Writes data/golden_set_unlabelled.csv. It never touches golden_set.csv, which holds the
hand-labelled priorities (see docs/decision-log.md D2-D3).
Usage: .venv/bin/python data/build_golden_set.py   (needs requirements-dev.txt)
"""
import math
from pathlib import Path

import pandas as pd
from datasets import load_dataset

CATEGORIES = ["ACCOUNT", "INVOICE", "PAYMENT", "REFUND", "SUBSCRIPTION", "CANCEL", "CONTACT", "FEEDBACK"]
PER_CATEGORY = {c: 6 for c in CATEGORIES} | {"ACCOUNT": 7, "PAYMENT": 7}  # 50 total

df = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset", split="train").to_pandas()
# SaaS-relevant categories only; drop messages with unfilled {{placeholders}}
df = df[df.category.isin(CATEGORIES) & ~df.instruction.str.contains(r"\{\{")]

parts = []
for category, n in PER_CATEGORY.items():
    sub = df[df.category == category]
    k = math.ceil(n / sub.intent.nunique())  # spread the sample across intents
    parts.append(sub.groupby("intent").sample(n=k, random_state=42).sample(n, random_state=42))

gold = pd.concat(parts).sample(frac=1, random_state=7).reset_index(drop=True)
gold.insert(0, "ticket_id", [f"T{i + 1:03d}" for i in range(len(gold))])
gold = gold.rename(columns={"instruction": "message", "category": "true_category", "intent": "true_intent"})
# Bitext's SUBSCRIPTION category is entirely newsletter sign-ups (decision-log D2)
gold["true_category"] = gold.true_category.replace({"SUBSCRIPTION": "NEWSLETTER"})
out = Path(__file__).parent / "golden_set_unlabelled.csv"
gold[["ticket_id", "message", "true_category", "true_intent"]].to_csv(out, index=False)
print(f"wrote {len(gold)} tickets to {out}")
