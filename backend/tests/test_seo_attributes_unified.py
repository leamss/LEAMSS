import pytest
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import get_current_user
from routers.seo_ssg import render_occupation_html


@pytest.mark.asyncio
async def test_seo_attributes_unified_update_and_sync():
    """Verify that updating SEO attributes in occupation master persists to MongoDB,
    synchronizes to public-atlas SEO block, sales endpoint, and SSG rendered HTML.
    """
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Find an existing occupation
        doc = await db["occupation_master"].find_one({"country_code": "AU", "status": "verified"})
        if not doc:
            doc = await db["occupation_master"].find_one({"country_code": "AU"})
        assert doc is not None, "At least one AU occupation must exist"

        occ_id = str(doc.get("occupation_id") or doc.get("_id"))
        code = str(doc.get("code"))

        # Custom SEO attributes payload
        seo_payload = {
            "meta_title": f"Custom SEO Title for {code} | LEAMSS Certified",
            "meta_description": f"Custom meta description for {code} explaining visa criteria, skill assessment, and state quotas.",
            "focus_keyword": f"{doc.get('title')} Australia PR",
            "keywords": f"{code}, {doc.get('title')}, migrate to Australia, ANZSCO PR",
            "canonical_url": f"https://leamss.com/atlas/au/{code}",
            "meta_robots": "index, follow, max-image-preview:large, max-snippet:-1",
            "og_title": f"Social OG Title for {code}",
            "og_description": f"Social OG Description for {code} migration guide.",
            "og_image": "https://leamss.com/images/seo-banner-custom.png",
            "og_locale": "en_AU",
            "twitter_card": "summary_large_image",
            "twitter_title": f"Twitter Card Title {code}",
            "twitter_description": f"Twitter Card Description {code}",
            "twitter_image": "https://leamss.com/images/seo-banner-custom.png",
            "schema_type": "Occupation",
            "custom_json_ld": '{"@type": "SpecialAnnouncement", "name": "Priority Processing Available"}',
        }

        # 1. Update occupation via PUT /api/occupation-master/{id}
        put_res = await client.put(
            f"/api/occupation-master/{occ_id}",
            json={
                "title": doc.get("title"),
                "status": "verified",
                "seo_meta": seo_payload,
            },
        )
        assert put_res.status_code == 200, f"PUT failed: {put_res.text}"
        updated_occ = put_res.json()
        assert updated_occ.get("seo_meta") is not None
        assert updated_occ["seo_meta"]["meta_title"] == seo_payload["meta_title"]
        assert updated_occ["seo_meta"]["focus_keyword"] == seo_payload["focus_keyword"]

        # 2. Verify MongoDB storage
        db_doc = await db["occupation_master"].find_one({"code": code, "country_code": "AU"})
        assert db_doc is not None
        assert db_doc.get("seo_meta") is not None
        assert db_doc["seo_meta"]["meta_title"] == seo_payload["meta_title"]
        assert db_doc["seo_meta"]["meta_description"] == seo_payload["meta_description"]
        assert db_doc["seo_meta"]["meta_robots"] == seo_payload["meta_robots"]

        # 3. Verify Public Atlas GET /api/public-atlas/au/{code}
        atlas_res = await client.get(f"/api/public-atlas/au/{code}")
        assert atlas_res.status_code == 200, f"Public Atlas failed: {atlas_res.text}"
        atlas_data = atlas_res.json()
        seo_block = atlas_data.get("seo")
        assert seo_block is not None, "SEO block must be present in public atlas response"
        assert seo_block["page_title"] == seo_payload["meta_title"]
        assert seo_block["meta_description"] == seo_payload["meta_description"]
        assert seo_block["keywords"] == seo_payload["keywords"]
        assert seo_block["canonical_url"] == seo_payload["canonical_url"]
        assert seo_block["meta_robots"] == seo_payload["meta_robots"]
        assert seo_block["og_title"] == seo_payload["og_title"]
        assert seo_block["og_description"] == seo_payload["og_description"]
        assert seo_block["og_image"] == seo_payload["og_image"]
        assert seo_block["og_locale"] == "en_AU"
        assert seo_block["twitter_card"] == "summary_large_image"
        assert seo_block["twitter_title"] == seo_payload["twitter_title"]
        assert seo_block["twitter_description"] == seo_payload["twitter_description"]
        assert seo_block["twitter_image"] == seo_payload["twitter_image"]

        # Verify custom JSON-LD injection in graph
        json_ld_graph = seo_block.get("json_ld", {}).get("@graph", [])
        has_custom_announcement = any(node.get("@type") == "SpecialAnnouncement" for node in json_ld_graph)
        assert has_custom_announcement, "Custom JSON-LD node must be injected into Schema.org @graph"

        # 4. Verify Sales endpoint GET /api/sales/occupations/au/{code}
        sales_res = await client.get(f"/api/sales/occupations/au/{code}")
        assert sales_res.status_code == 200, f"Sales endpoint failed: {sales_res.text}"
        sales_data = sales_res.json()
        assert sales_data.get("seo_meta") is not None
        assert sales_data["seo_meta"]["meta_title"] == seo_payload["meta_title"]

        # 5. Verify SSG HTML rendering reflects custom SEO
        html = await render_occupation_html("AU", code)
        assert html is not None, "SSG HTML must be rendered"
        assert seo_payload["meta_title"] in html
        assert seo_payload["meta_description"] in html
        assert f'<meta name="robots" content="{seo_payload["meta_robots"]}"' in html
        assert f'content="{seo_payload["og_title"]}"' in html
        assert f'content="{seo_payload["og_image"]}"' in html
