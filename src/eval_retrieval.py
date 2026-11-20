"""Tuần 9-10: đánh giá truy hồi trên bộ câu hỏi mẫu, xuất bảng kết quả Top-k.

Câu trong phạm vi có đáp án (Điều, Khoản); câu ngoài phạm vi có đáp án None.
Chạy không áp ngưỡng để xem khoảng cách thật, từ đó chọn MAX_DISTANCE trong retriever.py.
"""
import csv
import os

from ingest import PROCESSED_DIR, embed_batch
from retriever import TOP_K, retrieve

QUESTIONS = [
    ("Người lái xe máy có bắt buộc đội mũ bảo hiểm không?", (33, "2")),
    ("Độ tuổi tối thiểu để được lái xe mô tô hạng A1 là bao nhiêu?", (59, "1")),
    ("Đã uống rượu bia thì có được lái xe không?", (9, "2")),
    ("Lái xe có được cầm điện thoại khi xe đang chạy không?", (9, "6")),
    ("Giấy phép lái xe bị trừ điểm thì khi nào được phục hồi?", (58, "2")),
    ("Khi nào phải chuyển từ đèn pha sang đèn cốt?", (20, "2")),
    ("Có được bấm còi vào ban đêm trong khu dân cư không?", (21, "2")),
    ("Trẻ em có được ngồi cùng hàng ghế với người lái ô tô không?", (10, "3")),
    ("Niên hạn sử dụng của xe được tính như thế nào?", (40, "1")),
    ("Người đi bộ phải đi ở phần đường nào?", (30, "1")),
    ("Muốn nhập vào làn đường cao tốc phải làm gì?", (25, "1")),
    ("Khoản 2 Điều 9 quy định gì?", (9, "2")),
    ("Vượt đèn đỏ bị phạt bao nhiêu tiền?", None),  # mức phạt nằm ở nghị định, không có trong luật
    ("Thủ tục đăng ký kết hôn cần những giấy tờ gì?", None),
    ("Thuế thu nhập cá nhân được tính như thế nào?", None),
    ("Cách nấu phở bò ngon?", None),
]


def main():
    vectors = embed_batch([q for q, _ in QUESTIONS], task_type="RETRIEVAL_QUERY")  # 1 lần gọi API
    rows, ranks, top1_in, top1_out = [], [], [], []
    for (q, expected), vec in zip(QUESTIONS, vectors):
        hits = retrieve(q, top_k=TOP_K, max_distance=None, vector=vec)
        found = [(h["metadata"]["dieu"], h["metadata"]["khoan"]) for h in hits]
        rank = found.index(expected) + 1 if expected in found else None
        d1 = hits[0]["distance"]
        if expected:
            ranks.append(rank)
            top1_in.append(d1)
        else:
            top1_out.append(d1)
        rows.append({
            "cau_hoi": q,
            "dap_an": f"Khoản {expected[1]} Điều {expected[0]}" if expected else "(ngoài phạm vi)",
            "hang_dung": rank or "-",
            "top1": hits[0]["metadata"]["citation"],
            "khoang_cach_top1": f"{d1:.3f}",
            "top_k": "; ".join(f"{h['metadata']['citation']} ({h['distance']:.3f})" for h in hits),
        })
        print(f"{'✓' if rank == 1 else (rank or '✗')!s:>2} {d1:.3f}  {rows[-1]['top1']:<22} {q}")

    n = len(ranks)
    for k in (1, 3, 5):
        print(f"Hit@{k}: {sum(1 for r in ranks if r and r <= k)}/{n}")
    print(f"Khoảng cách Top-1, câu trong phạm vi: {min(top1_in):.3f} – {max(top1_in):.3f}")
    print(f"Khoảng cách Top-1, câu ngoài phạm vi: {min(top1_out):.3f} – {max(top1_out):.3f}")

    out = os.path.join(PROCESSED_DIR, "retrieval_eval.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig để Excel đọc đúng tiếng Việt
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print("Đã lưu bảng kết quả:", out)


if __name__ == "__main__":
    main()
