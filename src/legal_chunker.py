import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
MAX_CHARS = 2000
LAW_NAMES = {
    "luat-ttatgt-duongbo.pdf": "Luật Trật tự, an toàn giao thông đường bộ số 36/2024/QH15",
}
RE_CHUONG = re.compile(r"^Chương\s+([IVXLC]+)\s*$")
RE_DIEU = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
RE_KHOAN = re.compile(r"^(\d+)([a-z]?)\.\s+(.*)$")
RE_DIEM = re.compile(r"^([a-zđ])\)\s+(.*)$")

def _new_khoan(no: str, text: str, page: int) -> dict:
    return {"no": no, "lead": [text], "diems": [], "pages": {page}}

def parse_structure(pages: list[dict]) -> list[dict]:
    dieus: list[dict] = []
    chuong = chuong_title = ""
    cur = None
    mode = "skip"
    last_khoan = (0, "")

    for page in pages:
        pno = page["page"]
        for line in page["lines"]:
            text, bold = line["text"], line["bold"]

            if bold and (m := RE_CHUONG.match(text)):
                chuong, chuong_title, mode, cur = f"Chương {m.group(1)}", "", "chuong_title", None
                continue
            if mode == "chuong_title" and bold and not RE_DIEU.match(text):
                chuong_title = f"{chuong_title} {text}".strip()
                continue
            if bold and (m := RE_DIEU.match(text)) and int(m.group(1)) == (cur["dieu"] if cur else (dieus[-1]["dieu"] if dieus else 0)) + 1:
                cur = {"chuong": chuong, "chuong_title": chuong_title, "dieu": int(m.group(1)),
                       "title": m.group(2).strip(), "intro": [], "khoans": [], "pages": {pno}}
                dieus.append(cur)
                mode, last_khoan = "dieu_title", (0, "")
                continue
            if mode == "dieu_title" and bold:
                cur["title"] = f"{cur['title']} {text}".strip()
                continue
            if cur is None:
                continue
            mode = "body"
            cur["pages"].add(pno)

            if (m := RE_KHOAN.match(text)) and _is_next_khoan(last_khoan, int(m.group(1)), m.group(2)):
                last_khoan = (int(m.group(1)), m.group(2))
                cur["khoans"].append(_new_khoan(m.group(1) + m.group(2), m.group(3), pno))
            elif cur["khoans"]:
                k = cur["khoans"][-1]
                k["pages"].add(pno)
                if (m := RE_DIEM.match(text)):
                    k["diems"].append({"letter": m.group(1), "lines": [m.group(2)], "pages": {pno}})
                elif k["diems"]:
                    k["diems"][-1]["lines"].append(text)
                    k["diems"][-1]["pages"].add(pno)
                else:
                    k["lead"].append(text)
            else:
                cur["intro"].append(text)
    return dieus


def _is_next_khoan(last: tuple[int, str], num: int, suffix: str) -> bool:
    if last[0] == 0:
        return num == 1 and not suffix
    return (num == last[0] + 1 and not suffix) or (num == last[0] and suffix > last[1])


def _join(lines: list[str]) -> str:
    return " ".join(lines).strip()


def build_chunks(dieus: list[dict], file_name: str) -> list[dict]:
    law = LAW_NAMES.get(file_name, file_name)
    chunks = []

    def add(d, khoan, diem, body, pages):
        ctx = f"{law} | {d['chuong']} - {d['chuong_title']} | Điều {d['dieu']}. {d['title']}"
        if khoan:
            ctx += f" | Khoản {khoan}"
        if diem:
            ctx += f" | Điểm {diem}"
        cite = f"Điều {d['dieu']}" if not khoan else f"khoản {khoan} Điều {d['dieu']}"
        if diem:
            cite = f"điểm {diem} " + cite
        chunks.append({
            "id": f"{os.path.splitext(file_name)[0]}-d{d['dieu']}-k{khoan or '0'}-{diem or '0'}",
            "text": f"{ctx}\n{body}",
            "metadata": {
                "source": file_name, "law": law,
                "chuong": d["chuong"], "chuong_title": d["chuong_title"],
                "dieu": d["dieu"], "dieu_title": d["title"],
                "khoan": khoan, "diem": diem,
                "page_start": min(pages), "page_end": max(pages),
                "citation": cite[0].upper() + cite[1:],
            },
        })

    for d in dieus:
        if d["intro"]:
            add(d, "", "", _join(d["intro"]), d["pages"] if not d["khoans"] else {min(d["pages"])})
        for k in d["khoans"]:
            lead = _join(k["lead"])
            full = "\n".join([lead] + [f"{x['letter']}) {_join(x['lines'])}" for x in k["diems"]])
            if len(full) <= MAX_CHARS or not k["diems"]:
                add(d, k["no"], "", full, k["pages"])
                continue
            # Khoản dài: gom các điểm liên tiếp, mỗi nhóm lặp lại câu dẫn của khoản
            group, size = [], len(lead)
            for x in k["diems"] + [None]:
                piece = f"{x['letter']}) {_join(x['lines'])}" if x else ""
                if group and (x is None or size + len(piece) > MAX_CHARS):
                    first, last = group[0]["letter"], group[-1]["letter"]
                    body = "\n".join([lead] + [f"{g['letter']}) {_join(g['lines'])}" for g in group])
                    add(d, k["no"], first if first == last else f"{first}-{last}", body,
                        set().union(*(g["pages"] for g in group)))
                    group, size = [], len(lead)
                if x:
                    group.append(x)
                    size += len(piece)
    return chunks


def validate(dieus: list[dict]) -> None:
    nums = [d["dieu"] for d in dieus]
    assert nums == list(range(1, len(nums) + 1)), f"Số Điều không liên tục: {nums}"
    assert all(d["title"] for d in dieus), "Có Điều thiếu tiêu đề"


def main():
    for name in sorted(os.listdir(PROCESSED_DIR)):
        if not name.endswith(".pages.json"):
            continue
        with open(os.path.join(PROCESSED_DIR, name), encoding="utf-8") as f:
            data = json.load(f)
        dieus = parse_structure(data["pages"])
        validate(dieus)
        chunks = build_chunks(dieus, data["file"])
        out = os.path.join(PROCESSED_DIR, name.replace(".pages.json", ".chunks.json"))
        with open(out, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=1)
        lens = [len(c["text"]) for c in chunks]
        print(f"{data['file']}: {len({d['chuong'] for d in dieus})} chương, {len(dieus)} điều, "
              f"{len(chunks)} chunk (dài nhất {max(lens)}, ngắn nhất {min(lens)}, TB {sum(lens)//len(lens)} ký tự)"
              f" -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
