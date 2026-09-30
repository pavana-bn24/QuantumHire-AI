"""End-to-end diagnostic sweep for the resume pipeline.

Run from backend/: .venv/Scripts/python scripts/diag_e2e.py
"""

from __future__ import annotations

import uuid

import fitz
import httpx

BASE = "http://127.0.0.1:8000"
RESULTS: list[str] = []


def check(label: str, expected: int, resp: httpx.Response, contains: str | None = None) -> None:
    actual = resp.status_code
    ok = actual == expected
    snippet = resp.text[:160].replace("\n", " ")
    if contains:
        ok = ok and contains in resp.text
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {label}: expected {expected}, got {actual}  {snippet}")


def make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=10)
    payload = doc.tobytes()
    doc.close()
    return payload


def unique_resume() -> bytes:
    token = uuid.uuid4().hex[:8]
    return make_pdf(
        f"Test Candidate {token}\n"
        f"test.{token}@example.com | +1 555 000 1111\n\n"
        "SKILLS\nPython, FastAPI, React, MongoDB\n\n"
        "EXPERIENCE\n"
        "Engineer at Acme Corp\n2020 - 2024\n"
        "Built REST APIs with FastAPI and React dashboards.\n"
    )



def main() -> None:
    with httpx.Client(base_url=BASE, timeout=60.0, trust_env=False) as client:
        check("health", 200, client.get("/api/health"))
        check("roles", 200, client.get("/api/roles"))
        check("candidates list", 200, client.get("/api/candidates", params={"limit": 5}))
        check("dashboard/summary", 200, client.get("/api/dashboard/summary"))

        files = {"file": ("resume.pdf", unique_resume(), "application/pdf")}
        r = client.post("/api/candidates/upload", files=files)
        check("valid upload 201", 201, r)
        if r.status_code == 201:
            body = r.json()
            cid = body["candidate_id"]
            prof = body["extracted_profile"]
            RESULTS.append(
                f"INFO  profile: name={prof.get('name')} skills={prof.get('skills')} "
                f"exp={len(prof.get('work_experience') or [])} "
                f"provider={body['extraction']['provider']}"
            )

            d = client.get(f"/api/candidates/{cid}")
            check("detail 200", 200, d)
            if d.status_code == 200:
                dj = d.json()
                RESULTS.append(
                    f"INFO  detail: resume_text_len={len(dj.get('resume_text') or '')} "
                    f"reviewed={dj.get('profile_reviewed')} has_profile={bool(dj.get('extracted_profile'))}"
                )

            r2 = client.post("/api/candidates/upload", files=files)
            check("duplicate upload 409", 409, r2, "already exists")

            # Contract (frontend ProfileForm): every profile field flat + reviewed.
            put = client.put(
                f"/api/candidates/{cid}/profile",
                json={**prof, "reviewed": True},
            )
            check("approve 200", 200, put)
            if put.status_code == 200:
                RESULTS.append(f"INFO  approved={put.json().get('profile_reviewed')}")

            nested = client.put(
                f"/api/candidates/{cid}/profile",
                json={"extracted_profile": {"name": 123}, "reviewed": False},
            )
            check("nested PUT 422", 422, nested, "flat at the top level")

            unknown = client.put(
                f"/api/candidates/{cid}/profile",
                json={"full_name": "Typo", "reviewed": False},
            )
            check("unknown field PUT 422", 422, unknown, "full_name")

            wrong_type = client.put(
                f"/api/candidates/{cid}/profile",
                json={**prof, "name": 123, "reviewed": False},
            )
            check("wrong type PUT 422", 422, wrong_type, "name")

            miss = client.put(
                "/api/candidates/deadbeefdeadbeefdeadbeef/profile",
                json={**prof, "reviewed": False},
            )
            check("PUT unknown 404", 404, miss)

            clash_email = f"clash.{uuid.uuid4().hex[:8]}@example.com"
            created = client.post(
                "/api/candidates", json={"name": "Clash Target", "email": clash_email}
            )
            check("manual create 201", 201, created)
            c = client.put(
                f"/api/candidates/{cid}/profile",
                json={**prof, "email": clash_email, "reviewed": False},
            )
            check("PUT email clash 409", 409, c, "already belongs to another candidate")

            dup_create = client.post(
                "/api/candidates",
                json={"name": "Dup Person", "email": f"  {clash_email.upper()}  "},
            )
            check("create email clash 409", 409, dup_create, "already exists")

            check("GET unknown 404", 404, client.get("/api/candidates/deadbeefdeadbeefdeadbeef"))

        r = client.post(
            "/api/candidates/upload",
            files={"file": ("resume.txt", b"plain text", "text/plain")},
        )
        check("txt extension 415", 415, r, "not supported")

        r = client.post(
            "/api/candidates/upload",
            files={"file": ("resume.pdf", b"this is not a pdf", "application/pdf")},
        )
        check("fake pdf bytes 415", 415, r)

        big = b"%PDF-1.4\n" + b"0" * (11 * 1024 * 1024)  # documented limit is 10 MB
        r = client.post(
            "/api/candidates/upload",
            files={"file": ("big.pdf", big, "application/pdf")},
        )
        check("oversize 413", 413, r, "exceeds the 10 MB limit")

        r = client.post(
            "/api/candidates/upload",
            files={"file": ("bad.pdf", b"%PDF-1.4 truncated garbage", "application/pdf")},
        )
        check("corrupt pdf 422", 422, r, "corrupted")

        r = client.post(
            "/api/candidates/upload",
            files={"file": ("blank.pdf", make_pdf(""), "application/pdf")},
        )
        check("blank pdf 422", 422, r)

        r = client.post(
            "/api/candidates/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        check("empty file 400", 400, r)  # documented: empty check runs before MIME check

        r = client.post("/api/candidates/upload", data={"stage": "New"})
        check("missing file 422", 422, r)

        r = client.post(
            "/api/candidates/upload",
            files={"file": ("resume.pdf", unique_resume(), "application/pdf")},
            data={"stage": "Bogus Stage"},
        )
        check("unknown stage 422", 422, r)

        r = client.post(
            "/api/candidates/upload",
            files={"file": ("resume.pdf", unique_resume(), "application/pdf")},
            data={"role_id": "111111111111111111111111"},
        )
        check("unknown role 404", 404, r, "Role")

        r = client.get("/api/candidates/not-an-objectid")
        check("invalid id 404", 404, r)

        roles = client.get("/api/roles").json()
        items = roles if isinstance(roles, list) else roles.get("items", [])
        if items:
            check("role detail 200", 200, client.get(f"/api/roles/{items[0]['id']}"))

    print("\n".join(RESULTS))
    fails = [x for x in RESULTS if x.startswith("FAIL")]
    print(f"\n{len(RESULTS) - len(fails)} passed, {len(fails)} failed")


if __name__ == "__main__":
    main()
