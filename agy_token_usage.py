"""Token usage of one Antigravity CLI (agy) conversation, summed over all its LLM calls.

agy stores every conversation as a SQLite file in ~/.gemini/antigravity-cli/conversations/<id>.db.
Table gen_metadata has one protobuf blob per LLM call; the usage block (field 1.4) holds:
    1.4.2   input tokens, not cached
    1.4.5   input tokens read from the prompt cache
    1.4.3   output tokens (= 1.4.9 thinking + 1.4.10 response / tool calls)
There is no published schema: this mapping was inferred from the data (output = thinking +
response holds exactly in every call; cached input appears once the context is cached and the
uncached input drops at the same call). Field 1.21 is the model's display name.

    python agy_token_usage.py ~/.gemini/antigravity-cli/conversations/<id>.db
    python agy_token_usage.py <db> --run-id harness_... --csv token_usage.csv   (append one row)
"""
import argparse
import csv
import os
import sqlite3

FIELDS = {"1.4.2": "input_uncached", "1.4.5": "input_cached", "1.4.3": "output",
          "1.4.9": "output_thinking", "1.4.10": "output_response"}


def _varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if not x & 0x80:
            return r, i


def _parse(b, depth=0, path=""):
    """Schema-less protobuf walk: list of (field path, int or str). None if b is not a message."""
    i, out = 0, []
    try:
        while i < len(b):
            key, i = _varint(b, i)
            field, wire = key >> 3, key & 7
            if field == 0:
                return None
            if wire == 0:
                v, i = _varint(b, i)
                out.append((path + str(field), v))
            elif wire == 1:
                i += 8
            elif wire == 5:
                i += 4
            elif wire == 2:
                n, i = _varint(b, i)
                sub = b[i:i + n]
                i += n
                inner = _parse(sub, depth + 1, path + str(field) + ".") if depth < 6 else None
                if inner:
                    out += inner
                else:
                    try:
                        out.append((path + str(field), sub.decode()))
                    except UnicodeDecodeError:
                        pass
            else:
                return None
        return out
    except (IndexError, ValueError):
        return None


def usage(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = con.execute("select data from gen_metadata order by idx").fetchall()
    con.close()
    total = {name: 0 for name in FIELDS.values()}
    models = set()
    for (blob,) in rows:
        seen = set()
        for path, value in _parse(blob) or []:
            if path in FIELDS and isinstance(value, int) and path not in seen:
                total[FIELDS[path]] += value
                seen.add(path)
            elif path == "1.21" and isinstance(value, str):
                models.add(value)
    total["input_total"] = total["input_uncached"] + total["input_cached"]
    total["total"] = total["input_total"] + total["output"]
    total["llm_calls"] = len(rows)
    total["model"] = ", ".join(sorted(models))
    total["conversation"] = os.path.basename(db_path).removesuffix(".db")
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("db")
    p.add_argument("--run-id", default="")
    p.add_argument("--csv", help="append one row to this CSV")
    a = p.parse_args()
    u = usage(a.db)
    print(f"{a.run_id or u['conversation']}: {u['llm_calls']} LLM calls ({u['model']}) | "
          f"input {u['input_total']:,} ({u['input_cached']:,} cached) | "
          f"output {u['output']:,} ({u['output_thinking']:,} thinking) | total {u['total']:,}")
    if a.csv:
        cols = ["run_id", "conversation", "model", "llm_calls", "input_uncached", "input_cached",
                "input_total", "output", "output_thinking", "output_response", "total"]
        new = not os.path.exists(a.csv)
        with open(a.csv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerow({"run_id": a.run_id, **u})


if __name__ == "__main__":
    main()
