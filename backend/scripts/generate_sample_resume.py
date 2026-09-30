"""Generate a text-based sample resume PDF for manual testing / demos.

Usage (from the backend directory):

    .venv\\Scripts\\python.exe scripts\\generate_sample_resume.py
    .venv\\Scripts\\python.exe scripts\\generate_sample_resume.py --output C:\\temp\\cv.pdf

The output is a normal, text-based PDF (no OCR needed) so it exercises the whole
upload -> extract -> review pipeline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz

SAMPLE_LINES = [
    "Aarav Sharma",
    "Bengaluru, India | aarav.sharma@example.com | +91 98765 43210",
    "",
    "SUMMARY",
    "AI-focused full-stack developer with 4 years of experience building React front",
    "ends and FastAPI services, including a retrieval augmented generation assistant.",
    "",
    "SKILLS",
    "Communication, leadership, mentoring, code review, agile, problem solving",
    "",
    "TECHNOLOGIES",
    "Python, FastAPI, React, TypeScript, JavaScript, MongoDB, PostgreSQL, SQL,",
    "REST, RAG, LLM, LangChain, OpenAI API, prompt engineering, Docker",
    "",
    "EXPERIENCE",
    "Senior Software Engineer at Nimbus Labs",
    "2021 - Present",
    "Built a RAG assistant over internal documentation using LangChain and OpenAI API.",
    "Developed React dashboards backed by a FastAPI service and MongoDB.",
    "Reduced API latency by 40% by refactoring the service layer and adding caching.",
    "",
    "Software Engineer at Blue Orbit",
    "2019 - 2021",
    "Implemented REST APIs in Python and automated deployments with GitHub Actions.",
    "Migrated the reporting module to PostgreSQL and improved query performance.",
    "",
    "PROJECTS",
    "Project: QuantumHire - resume parsing service built with FastAPI and PyMuPDF.",
    "Project: Agent Playground - tool calling demo with an LLM planner and Python tools.",
    "",
    "EDUCATION",
    "B.Tech in Computer Science, IIT Madras, 2015 - 2019",
    "",
    "ACHIEVEMENTS",
    "Won the internal AI hackathon in 2023 for an automated screening prototype.",
    "Certified AWS Cloud Practitioner, 2022.",
]

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "sample_data" / "sample_resume.pdf"


def build_resume(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)

    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 800), "\n".join(SAMPLE_LINES), fontsize=10)
    document.save(output)
    document.close()

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a sample resume PDF.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the PDF (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    path = build_resume(args.output)
    print(f"Wrote sample resume: {path}")


if __name__ == "__main__":
    main()
