"""Convert the supplied attestation DOCX without external dependencies."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SUBJECTS = [
    ("sport_fiziologiyasi", "Sport fiziologiyasi", 0, 400),
    ("soglom_turmush", "Sog'lom turmush tarzi", 2007, 400),
    ("milliy_oyinlar", "Milliy va harakatli o'yinlar", 4385, 400),
    ("sport_inshootlari", "Sport inshootlari", 5167, 400),
    ("gimnastika", "Gimnastika", 7131, 400),
    ("yengil_atletika", "Yengil atletika", 9097, 400),
    ("suzish", "Suzish", 9903, 400),
    ("kurash", "Kurash", 11869, 400),
    ("voleybol", "Voleybol", 12675, 300),
    ("gandbol", "Gandbol", 13280, 400),
    ("basketbol", "Basketbol", 13686, 400),
    ("futbol", "Futbol", 15652, 400),
    ("shaxmat", "Shaxmat", 16457, 200),
]


def paragraphs(path):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    result = []
    for paragraph in root.findall(".//w:p", NS):
        parts = []
        for node in paragraph.iter():
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "t":
                parts.append(node.text or "")
            elif tag in ("br", "tab"):
                parts.append("\n" if tag == "br" else " ")
        result.append("".join(parts).strip())
    return result


def convert(source, destination):
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != "e8e3efc73131169ec884ed0c5ea13d2701da69a86f8fa4fefd38219136138f05":
        raise ValueError("This converter uses paragraph boundaries for the supplied attestation document only.")
    lines = paragraphs(source)
    destination.mkdir(exist_ok=True)
    report = {"source": source.name, "sha256": source_hash, "subjects": []}
    for position, (slug, title, start, expected) in enumerate(SUBJECTS):
        end = SUBJECTS[position + 1][2] if position + 1 < len(SUBJECTS) else len(lines)
        questions, text, options, source_number, source_paragraph = [], [], {}, None, None
        def flush():
            nonlocal text, options, source_number, source_paragraph
            if text or options:
                if not text or set(options) not in ({"A", "B"}, {"A", "B", "C"}, set("ABCD")) or not all(options.values()):
                    raise ValueError(f"Malformed question: {slug}, paragraph {source_paragraph}: {text}, {options}")
                questions.append({"id": len(questions) + 1, "source_number": source_number,
                                  "source_paragraph": source_paragraph, "text": "\n".join(text),
                                  "options": options, "correct_answer": "A", "answer_source": "document_declared_A"})
            text, options, source_number, source_paragraph = [], {}, None, None
        for offset in range(start + 1, end):
            line = lines[offset].split("Shaxmat fanidan attestatsiya testlari")[0].strip()
            if not line:
                continue
            if re.match(r"^(I{1,3}\.|Ushbu |Umumiy |\(Har bir|\(Barcha|\(31 dan)", line):
                flush()
                continue
            number = re.match(r"^(\d+)\.\s*(.*)", line, re.S)
            if number:
                flush()
                source_number = int(number[1])
                source_paragraph = offset
                line = number[2]
            elif options and not re.match(r"^[ABCD]\)", line):
                flush()
            parts = re.split(r"(?<![A-Z])([ABCD])\)\s*", line)
            if parts[0].strip():
                if source_paragraph is None:
                    source_paragraph = offset
                text.append(parts[0].strip())
            for i in range(1, len(parts), 2):
                if parts[i] in options:
                    raise ValueError(f"Duplicate option: {slug}, {offset}")
                options[parts[i]] = parts[i + 1].strip()
        flush()
        duplicates = sum(n - 1 for n in collections.Counter(q["text"] for q in questions).values())
        report["subjects"].append({"id": slug, "title": title, "declared_count": expected,
                                    "extracted_count": len(questions), "duplicate_question_texts": duplicates,
                                    "incomplete_options": [{"id": q["id"], "source_number": q["source_number"], "options": len(q["options"])} for q in questions if q["source_number"] and q["source_number"] > 20 and len(q["options"]) < 4],
                                    "option_counts": dict(collections.Counter(len(q["options"]) for q in questions))})
        data = {"title": title, "language": "uz-Latn", "source_file": source.name, "questions": questions}
        (destination / f"{slug}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["total"] = sum(s["extracted_count"] for s in report["subjects"])
    (destination.parent / "conversion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    report = convert(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(report, ensure_ascii=True, indent=2))
