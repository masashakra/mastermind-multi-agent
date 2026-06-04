#!/usr/bin/env python3
"""
Message-Reply Semantic Analysis — All Messages, All Paradigms
==============================================================
Works for both Round-Table and Boss-Worker logs.

Reply matching strategy (in priority order):
  1. Exact match via reply_to_id in a2a_receive entries  (Boss-Worker)
  2. Temporal match: next a2a_send from the receiver     (Round-Table)

Usage:
  python3 analyze_message_pairs.py --log logs/MM_001_boss_worker_deepseek_messages.log
  python3 analyze_message_pairs.py --log logs/MM_001_round_table_deepseek_messages.log
"""

import json, sys, glob, argparse
from pathlib import Path
from datetime import datetime

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

FIRE_AND_FORGET    = {"receive_constraints"}
SIMILARITY_HIGH    = 0.80
SIMILARITY_MEDIUM  = 0.55


# ── Helpers ────────────────────────────────────────────────────────────────────

def payload_to_text(payload: dict) -> str:
    parts = []
    for key in ["analysis","strategy","phase","reasoning",
                "impossible_colors","confirmed_colors","locked_positions",
                "misplaced_colors","colors_to_use","colors_to_avoid",
                "positions_to_test","proposed_guess","constraint_check",
                "last_guess","feedback","guess_history"]:
        val = payload.get(key)
        if val:
            parts.append(f"{key}: {str(val)[:250]}")
    return " | ".join(parts) if parts else str(payload)[:250]


def load_log(path):
    with open(path) as f:
        return json.load(f)


# ── Extract sends AND receives ─────────────────────────────────────────────────

def extract_sends(entries):
    msgs = []
    for e in entries:
        if e.get("event_type") != "a2a_send":
            continue
        action  = e.get("action","")
        payload = e.get("payload", {})
        msgs.append({
            "timestamp":     e.get("timestamp", 0),
            "datetime":      e.get("datetime_str",""),
            "message_id":    e.get("message_id",""),
            "sender":        e.get("sender_id","").split("_")[0].lower(),
            "receiver":      e.get("receiver_id","").split("_")[0].lower(),
            "action":        action,
            "payload":       payload,
            "text":          payload_to_text(payload),
            "is_question":   e.get("is_question", False),
            "expects_reply": e.get("expects_reply", action not in FIRE_AND_FORGET),
            "msg_type":      "FIRE_AND_FORGET" if action in FIRE_AND_FORGET else "TRIGGERS_RESPONSE",
        })
    return msgs


def extract_receives(entries):
    """Build a dict of reply_to_id → receive entry (for Boss-Worker style)."""
    receives = {}
    for e in entries:
        if e.get("event_type") != "a2a_receive":
            continue
        reply_to = e.get("reply_to_id","")
        if reply_to:
            receives[reply_to] = {
                "timestamp":   e.get("timestamp", 0),
                "datetime":    e.get("datetime_str",""),
                "message_id":  e.get("message_id","")[:8],
                "sender":      e.get("sender_id","").split("_")[0].lower(),
                "receiver":    e.get("receiver_id","").split("_")[0].lower(),
                "action":      e.get("action",""),
                "payload":     e.get("payload", {}),
                "text":        payload_to_text(e.get("payload", {})),
                "is_reply":    True,
                "reply_to_id": reply_to[:8],
                "source":      "a2a_receive",
            }
    return receives


# ── Round assignment ────────────────────────────────────────────────────────────

def assign_rounds(entries, msgs):
    """
    Assign messages to rounds.
    Round-Table: uses routing events as round markers.
    Boss-Worker: groups every N sends (4 per round: analyze→strategy→propose→validate).
    """
    routing_times = [e["timestamp"] for e in entries if e.get("event_type") == "routing"]

    if routing_times:
        # Round-Table style
        for m in msgs:
            m["round"] = sum(1 for rt in routing_times if rt <= m["timestamp"])
    else:
        # Boss-Worker style — group by sequential sets of 4
        for i, m in enumerate(msgs):
            m["round"] = (i // 4) + 1

    return msgs


# ── Find reply for each message ────────────────────────────────────────────────

def find_reply(msg, all_sends, all_receives):
    """
    Priority 1: exact match via reply_to_id in a2a_receive entries.
    Priority 2: temporal — next send from the receiver in same round.
    """
    if msg["msg_type"] == "FIRE_AND_FORGET":
        return None, "FIRE_AND_FORGET"

    # Priority 1: explicit reply link (Boss-Worker)
    full_id = msg["message_id"]
    if full_id in all_receives:
        r = all_receives[full_id]
        return r, "exact_reply_link"

    # Priority 2: temporal next send from receiver (Round-Table)
    receiver = msg["receiver"]
    t0       = msg["timestamp"]
    rnd      = msg["round"]
    candidates = [
        m for m in all_sends
        if m["sender"] == receiver
        and m["timestamp"] > t0
        and m["round"] == rnd
    ]
    if candidates:
        return candidates[0], "temporal_next_send"

    return None, "NO_REPLY_FOUND"


# ── Semantic similarity ────────────────────────────────────────────────────────

def compute(msgs, all_sends, all_receives, model):
    results = []
    for msg in msgs:
        reply, method = find_reply(msg, all_sends, all_receives)

        base = {
            "round":        msg["round"],
            "message_id":   msg["message_id"][:8],
            "sender":       msg["sender"],
            "receiver":     msg["receiver"],
            "action":       msg["action"],
            "msg_type":     msg["msg_type"],
            "is_question":  msg["is_question"],
            "expects_reply": msg["expects_reply"],
            "timestamp":    msg["datetime"],
            "content":      msg["text"],
        }

        if msg["msg_type"] == "FIRE_AND_FORGET":
            results.append({**base,
                "reply": None, "reply_method": method,
                "similarity_score": None, "similarity_label": "FIRE_AND_FORGET",
            })
            continue

        if reply is None:
            results.append({**base,
                "reply": None, "reply_method": method,
                "similarity_score": None, "similarity_label": "NO_REPLY_FOUND",
            })
            continue

        req_text  = msg["text"]
        resp_text = reply["text"]

        if not req_text.strip() or not resp_text.strip():
            score, label = 0.0, "EMPTY"
        else:
            emb   = model.encode([req_text, resp_text])
            score = float(cosine_similarity([emb[0]], [emb[1]])[0][0])
            if   score >= SIMILARITY_HIGH:   label = "HIGH"
            elif score >= SIMILARITY_MEDIUM: label = "MEDIUM"
            else:                            label = "LOW"

        results.append({**base,
            "reply": {
                "sender":     reply["sender"],
                "action":     reply["action"],
                "message_id": reply["message_id"],
                "content":    reply["text"],
                "source":     reply.get("source","a2a_send"),
            },
            "reply_method":     method,
            "similarity_score": round(score, 4),
            "similarity_label": label,
        })
    return results


# ── Summary ────────────────────────────────────────────────────────────────────

def summarise(results):
    total    = len(results)
    ff       = [r for r in results if r["similarity_label"] == "FIRE_AND_FORGET"]
    triggers = [r for r in results if r["msg_type"] == "TRIGGERS_RESPONSE"]
    got      = [r for r in triggers if r.get("reply")]
    scored   = [r for r in triggers if r.get("similarity_score") is not None]
    scores   = [r["similarity_score"] for r in scored]
    labels   = [r["similarity_label"] for r in scored]

    by_action = {}
    for r in results:
        a = r["action"]
        if a not in by_action:
            by_action[a] = {"total":0,"got_reply":0,"scores":[]}
        by_action[a]["total"] += 1
        if r.get("reply"): by_action[a]["got_reply"] += 1
        if r.get("similarity_score") is not None:
            by_action[a]["scores"].append(r["similarity_score"])
    for a in by_action:
        s = by_action[a]["scores"]
        by_action[a]["avg_similarity"] = round(sum(s)/len(s),4) if s else None
        del by_action[a]["scores"]

    return {
        "total_messages":    total,
        "fire_and_forget":   len(ff),
        "triggers_response": len(triggers),
        "got_reply":         len(got),
        "no_reply":          len(triggers) - len(got),
        "reply_rate_pct":    round(len(got)/len(triggers)*100,1) if triggers else 0,
        "avg_similarity":    round(sum(scores)/len(scores),4) if scores else None,
        "min_similarity":    round(min(scores),4) if scores else None,
        "max_similarity":    round(max(scores),4) if scores else None,
        "distribution":      {
            "HIGH":   labels.count("HIGH"),
            "MEDIUM": labels.count("MEDIUM"),
            "LOW":    labels.count("LOW"),
        },
        "by_action": by_action,
    }


# ── Print ──────────────────────────────────────────────────────────────────────

ICONS = {"HIGH":"🟢","MEDIUM":"🟡","LOW":"🔴",
         "FIRE_AND_FORGET":"🔵","NO_REPLY_FOUND":"⚫","EMPTY":"⚪"}

def print_report(results, summary):
    print("\n" + "="*72)
    print("  MESSAGE-REPLY SEMANTIC ANALYSIS")
    print("="*72)
    print(f"\n  Total messages    : {summary['total_messages']}")
    print(f"  Fire-and-forget   : {summary['fire_and_forget']}  (no reply expected)")
    print(f"  Triggers-response : {summary['triggers_response']}")
    print(f"    Got reply        : {summary['got_reply']}  ({summary['reply_rate_pct']}%)")
    print(f"    No reply         : {summary['no_reply']}")
    print(f"  Avg similarity    : {summary['avg_similarity']}")
    d = summary["distribution"]
    print(f"\n  Distribution:")
    print(f"    🟢 HIGH   (≥{SIMILARITY_HIGH}) : {d['HIGH']}")
    print(f"    🟡 MEDIUM (≥{SIMILARITY_MEDIUM}) : {d['MEDIUM']}")
    print(f"    🔴 LOW    (<{SIMILARITY_MEDIUM}) : {d['LOW']}")
    print(f"\n  By action:")
    for action, stats in summary["by_action"].items():
        icon = "🔵" if action in FIRE_AND_FORGET else "📨"
        print(f"    {icon} {action:<25} {stats['got_reply']}/{stats['total']}  "
              f"avg_sim={stats['avg_similarity']}")

    print(f"\n{'─'*72}")
    current_round = None
    for r in results:
        if r["round"] != current_round:
            current_round = r["round"]
            print(f"\n  ── Round {current_round} ──")

        label  = r["similarity_label"]
        icon   = ICONS.get(label,"❓")
        score  = r.get("similarity_score")
        method = r.get("reply_method","")
        score_str = f"{score:.3f} [{label}]" if score is not None else label

        print(f"\n    {r['sender'].upper():<12} ──► {r['receiver'].upper():<12} [{r['action']}]  {icon} {score_str}")
        if method not in ("FIRE_AND_FORGET","NO_REPLY_FOUND"):
            print(f"      match via : {method}")
        print(f"      sent  : {r['content'][:120]}...")
        if r.get("reply"):
            print(f"      reply : {r['reply']['content'][:120]}...")
        else:
            print(f"      reply : {label}")

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
        candidates = sorted(glob.glob("logs/MM_*_messages.log"))
        if not candidates: print("No log files found."); sys.exit(1)
        log_path = candidates[-1]

    print(f"Loading: {log_path}")
    log     = load_log(log_path)
    entries = log["puzzle_run_log"]["entries"]

    sends    = extract_sends(entries)
    receives = extract_receives(entries)
    sends    = assign_rounds(entries, sends)

    ff_count  = sum(1 for m in sends if m["msg_type"]=="FIRE_AND_FORGET")
    tr_count  = sum(1 for m in sends if m["msg_type"]=="TRIGGERS_RESPONSE")
    rec_count = len(receives)
    print(f"Messages: {len(sends)} sends  ({ff_count} fire-and-forget, {tr_count} triggers-response)")
    print(f"Replies:  {rec_count} explicit a2a_receive entries")

    print("Loading sentence transformer (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    results = compute(sends, sends, receives, model)
    summary = summarise(results)
    print_report(results, summary)

    output = {
        "meta": {
            "log_file":    log_path,
            "analyzed_at": datetime.now().isoformat(),
            "model":       "all-MiniLM-L6-v2",
            "reply_matching": (
                "Priority 1: exact reply_to_id link in a2a_receive entries. "
                "Priority 2: temporal next send from receiver in same round."
            ),
        },
        "summary": summary,
        "results": results,
    }

    out_path = args.out or log_path.replace(".log","_semantic_analysis.json")
    with open(out_path,"w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Saved: {out_path}")


if __name__ == "__main__":
    main()
