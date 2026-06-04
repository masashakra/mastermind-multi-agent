#!/usr/bin/env python3
"""
Message-Reply Semantic Analysis — All Messages
================================================
Covers ALL A2A messages in the log (not just assumed pairs).

For each message:
  - Label it: FIRE_AND_FORGET or TRIGGERS_RESPONSE
  - Find the actual temporal response (next send from the receiver)
  - Compute cosine similarity between message content and response content
  - Report honestly which messages got relevant responses and which didn't

Usage:
  python3 analyze_message_pairs.py
  python3 analyze_message_pairs.py --log logs/MM_001_round_table_deepseek_messages.log
  python3 analyze_message_pairs.py --out logs/MM_001_semantic_analysis.json
"""

import json
import sys
import glob
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ── Message classification ─────────────────────────────────────────────────────
# FIRE_AND_FORGET: sent but no reply expected (broadcast constraint updates)
# TRIGGERS_RESPONSE: sender hands off work; receiver produces next message in chain

FIRE_AND_FORGET = {"receive_constraints"}
TRIGGERS_RESPONSE = {"strategy", "propose", "validate"}

SIMILARITY_THRESHOLDS = {"HIGH": 0.80, "MEDIUM": 0.55}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_log(path):
    with open(path) as f:
        return json.load(f)

def payload_to_text(payload: dict) -> str:
    """Flatten a payload dict into a single text string for embedding."""
    parts = []
    for key in ["analysis", "strategy", "phase", "reasoning",
                "impossible_colors", "confirmed_colors", "locked_positions",
                "misplaced_colors", "colors_to_use", "colors_to_avoid",
                "positions_to_test", "proposed_guess", "constraint_check"]:
        val = payload.get(key)
        if val:
            parts.append(f"{key}: {str(val)[:300]}")
    if not parts:
        parts.append(str(payload)[:300])
    return " | ".join(parts)

def extract_messages(entries):
    """Extract all A2A send events in chronological order."""
    msgs = []
    for e in entries:
        if e.get("event_type") != "a2a_send":
            continue
        sender   = e.get("sender_id","").split("_")[0].lower()
        receiver = e.get("receiver_id","").split("_")[0].lower()
        action   = e.get("action","")
        payload  = e.get("payload", {})

        # Classify
        if action in FIRE_AND_FORGET:
            msg_type = "FIRE_AND_FORGET"
        elif action in TRIGGERS_RESPONSE:
            msg_type = "TRIGGERS_RESPONSE"
        else:
            msg_type = "UNKNOWN"

        msgs.append({
            "timestamp":    e.get("timestamp", 0),
            "datetime":     e.get("datetime_str",""),
            "message_id":   e.get("message_id","")[:8],
            "sender":       sender,
            "receiver":     receiver,
            "action":       action,
            "msg_type":     msg_type,
            "payload":      payload,
            "text":         payload_to_text(payload),
            # From logger if available
            "expects_reply": e.get("expects_reply", msg_type == "TRIGGERS_RESPONSE"),
        })
    return msgs

def assign_rounds(entries, msgs):
    """Assign each message to a round using routing events as markers."""
    routing_times = [
        e["timestamp"] for e in entries
        if e.get("event_type") == "routing"
    ]
    for m in msgs:
        m["round"] = sum(1 for rt in routing_times if rt <= m["timestamp"])
    return msgs

def find_response(msg, all_msgs):
    """
    Find the temporal response to a message.

    For TRIGGERS_RESPONSE messages: the response is the next message
    sent BY the receiver, AFTER this message's timestamp.

    For FIRE_AND_FORGET: no response expected — return None.
    """
    if msg["msg_type"] == "FIRE_AND_FORGET":
        return None

    receiver = msg["receiver"]
    t0       = msg["timestamp"]
    rnd      = msg["round"]

    # Find next message FROM the receiver AFTER this timestamp (same round)
    candidates = [
        m for m in all_msgs
        if m["sender"] == receiver
        and m["timestamp"] > t0
        and m["round"] == rnd
    ]
    return candidates[0] if candidates else None


# ── Semantic similarity ────────────────────────────────────────────────────────

def compute_all(msgs, model):
    results = []
    for msg in msgs:
        response = find_response(msg, msgs)
        base = {
            "round":       msg["round"],
            "message_id":  msg["message_id"],
            "sender":      msg["sender"],
            "receiver":    msg["receiver"],
            "action":      msg["action"],
            "msg_type":    msg["msg_type"],
            "timestamp":   msg["datetime"],
            "content":     msg["text"],
            "expects_reply": msg["expects_reply"],
        }

        if msg["msg_type"] == "FIRE_AND_FORGET":
            results.append({**base,
                "response": None,
                "similarity_score": None,
                "similarity_label": "FIRE_AND_FORGET",
                "note": "Broadcast — no reply expected by design",
            })
            continue

        if response is None:
            results.append({**base,
                "response": None,
                "similarity_score": None,
                "similarity_label": "NO_RESPONSE_FOUND",
                "note": "Expected a response but none found in log (e.g. Validator reports to Orchestrator outside A2A log)",
            })
            continue

        req_text  = msg["text"]
        resp_text = response["text"]

        if not req_text.strip() or not resp_text.strip():
            score, label = 0.0, "EMPTY"
        else:
            emb   = model.encode([req_text, resp_text])
            score = float(cosine_similarity([emb[0]], [emb[1]])[0][0])
            if score >= SIMILARITY_THRESHOLDS["HIGH"]:   label = "HIGH"
            elif score >= SIMILARITY_THRESHOLDS["MEDIUM"]: label = "MEDIUM"
            else:                                          label = "LOW"

        results.append({**base,
            "response": {
                "sender":     response["sender"],
                "receiver":   response["receiver"],
                "action":     response["action"],
                "message_id": response["message_id"],
                "timestamp":  response["datetime"],
                "content":    response["text"],
            },
            "similarity_score": round(score, 4),
            "similarity_label": label,
            "note": "Temporal response from receiver",
        })

    return results


# ── Summary ────────────────────────────────────────────────────────────────────

def summarise(results):
    total       = len(results)
    ff          = [r for r in results if r["similarity_label"] == "FIRE_AND_FORGET"]
    triggers    = [r for r in results if r["msg_type"] == "TRIGGERS_RESPONSE"]
    got_resp    = [r for r in triggers if r.get("response")]
    no_resp     = [r for r in triggers if not r.get("response")]
    scored      = [r for r in triggers if r.get("similarity_score") is not None]
    scores      = [r["similarity_score"] for r in scored]
    labels      = [r["similarity_label"] for r in scored]

    by_action = {}
    for r in results:
        a = r["action"]
        if a not in by_action:
            by_action[a] = {"total":0,"got_response":0,"scores":[]}
        by_action[a]["total"] += 1
        if r.get("response"):
            by_action[a]["got_response"] += 1
        if r.get("similarity_score") is not None:
            by_action[a]["scores"].append(r["similarity_score"])
    for a in by_action:
        s = by_action[a]["scores"]
        by_action[a]["avg_similarity"] = round(sum(s)/len(s),4) if s else None
        del by_action[a]["scores"]

    return {
        "total_messages":          total,
        "fire_and_forget":         len(ff),
        "triggers_response":       len(triggers),
        "got_response":            len(got_resp),
        "no_response_found":       len(no_resp),
        "response_rate_pct":       round(len(got_resp)/len(triggers)*100,1) if triggers else 0,
        "avg_similarity":          round(sum(scores)/len(scores),4) if scores else None,
        "min_similarity":          round(min(scores),4) if scores else None,
        "max_similarity":          round(max(scores),4) if scores else None,
        "similarity_distribution": {
            "HIGH":   labels.count("HIGH"),
            "MEDIUM": labels.count("MEDIUM"),
            "LOW":    labels.count("LOW"),
        },
        "by_action": by_action,
    }


# ── Print ──────────────────────────────────────────────────────────────────────

ICONS = {"HIGH":"🟢","MEDIUM":"🟡","LOW":"🔴",
         "FIRE_AND_FORGET":"🔵","NO_RESPONSE_FOUND":"⚫","EMPTY":"⚪"}

def print_report(results, summary):
    print("\n" + "="*72)
    print("  ALL MESSAGES — SEMANTIC ANALYSIS")
    print("="*72)
    print(f"\n  Total messages          : {summary['total_messages']}")
    print(f"  Fire-and-forget (no reply expected) : {summary['fire_and_forget']}")
    print(f"  Triggers-response       : {summary['triggers_response']}")
    print(f"    Got response          : {summary['got_response']}  ({summary['response_rate_pct']}%)")
    print(f"    No response in log    : {summary['no_response_found']}")
    print(f"  Avg similarity (scored) : {summary['avg_similarity']}")
    dist = summary["similarity_distribution"]
    print(f"\n  Similarity distribution (triggers only):")
    print(f"    🟢 HIGH   (≥0.80) : {dist['HIGH']}")
    print(f"    🟡 MEDIUM (≥0.55) : {dist['MEDIUM']}")
    print(f"    🔴 LOW    (<0.55) : {dist['LOW']}")
    print(f"\n  By action:")
    for action, stats in summary["by_action"].items():
        icon = "🔵" if action == "receive_constraints" else "📨"
        print(f"    {icon} {action:<25} {stats['got_response']}/{stats['total']} responses  "
              f"avg_sim={stats['avg_similarity']}")

    print(f"\n{'─'*72}")
    print("  ROUND-BY-ROUND — ALL MESSAGES")
    print(f"{'─'*72}")

    current_round = None
    for r in results:
        if r["round"] != current_round:
            current_round = r["round"]
            print(f"\n  ── Round {current_round} ──")

        label = r["similarity_label"]
        icon  = ICONS.get(label, "❓")
        score_str = f"{r['similarity_score']:.3f} [{label}]" if r.get("similarity_score") is not None else label

        print(f"\n    {r['sender'].upper():<12} ──► {r['receiver'].upper():<12} [{r['action']}]  {icon} {score_str}")
        print(f"      sent : {r['content'][:100]}...")
        if r.get("response"):
            resp = r["response"]
            print(f"      recv : {resp['content'][:100]}...")
        else:
            print(f"      recv : {r['note']}")

    print("\n" + "="*72)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if args.log:
        log_path = args.log
    else:
        candidates = sorted(glob.glob("logs/MM_*_round_table_deepseek_messages.log"))
        if not candidates:
            print("No log files found."); sys.exit(1)
        log_path = candidates[-1]

    print(f"Loading: {log_path}")
    log     = load_log(log_path)
    entries = log["puzzle_run_log"]["entries"]

    msgs = extract_messages(entries)
    msgs = assign_rounds(entries, msgs)
    print(f"Messages: {len(msgs)} total  "
          f"({sum(1 for m in msgs if m['msg_type']=='FIRE_AND_FORGET')} fire-and-forget, "
          f"{sum(1 for m in msgs if m['msg_type']=='TRIGGERS_RESPONSE')} triggers-response)")

    print("Loading sentence transformer...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    results = compute_all(msgs, model)
    summary = summarise(results)
    print_report(results, summary)

    output = {
        "meta": {
            "log_file":    log_path,
            "analyzed_at": datetime.now().isoformat(),
            "model":       "all-MiniLM-L6-v2",
            "thresholds":  SIMILARITY_THRESHOLDS,
            "methodology": (
                "FIRE_AND_FORGET messages (receive_constraints) have no reply expected. "
                "TRIGGERS_RESPONSE messages (strategy/propose/validate) — response is "
                "the next message sent by the receiver within the same round."
            ),
        },
        "summary": summary,
        "results": results,
    }

    out_path = args.out or log_path.replace(".log", "_semantic_analysis.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Saved: {out_path}")


if __name__ == "__main__":
    main()
