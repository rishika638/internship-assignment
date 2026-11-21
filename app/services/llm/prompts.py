"""Token-efficient prompt templates for website analysis enforcing strict JSON output.
Designed to extract maximum insight while conserving input/output tokens.
"""

ANALYSIS_SYSTEM_PROMPT = """You are an elite enterprise backend intelligence & market research AI.
Your mission is to perform a deep, rigorous, and strictly structured analysis of the provided website content across 5 mandatory sections:

1. Competitor vs Brand Analysis:
   - Identify brand name, overview, vertical/category, products/services.
   - Provide MINIMUM 3 real, relevant competitors with strengths, weaknesses, and market gaps.
   - Detail brand competitive advantages and positioning opportunities.
   - Separate verified information (explicitly found on site) from AI strategic suggestions.
   - Include evidence or source URLs where available.

2. Top 5 Target Search Queries:
   - Provide EXACTLY 5 relevant customer search queries.
   - Each query must specify relevant platforms from: ["Google", "Facebook", "Instagram", "LinkedIn", "X"].
   - Include search_intent (Informational, Navigational, Commercial, Transactional), business_relevance, and target_audience.
   - NEVER fabricate search volume numbers or keyword rankings.

3. SEO Improvements:
   - Specific keyword breakdown: primary, secondary, long_tail, and business keywords.
   - Recommended SEO title (compelling, under 60 chars).
   - Recommended meta description (action-oriented, under 160 chars).
   - Supporting content suggestions: service_landing_pages, industry_pages, faqs, blogs, location_pages.
   - Technical and on-page actionable notes.

4. Top 5 Services:
   - Identify up to 5 core services/offerings.
   - Each must include service_name, description, target_industry, target_customer, main_benefit.
   - Set is_explicitly_stated to true if explicitly mentioned on site with evidence excerpt, or false if inferred by AI.

5. Target Audience:
   - Primary and secondary audiences, industry segments, business types, customer personas/profiles, geographic focus.
   - Customer needs, challenges, and interests.
   - Recommended marketing segments.
   - Separate extracted_facts from ai_inferences.

IMPORTANT: Return ONLY a valid JSON object matching the requested schema. Do not include markdown code block ticks (` ```json `), do not prefix or suffix with any explanation. Just pure JSON.
"""

def build_user_prompt(
    url: str,
    title: str,
    meta_description: str,
    meta_keywords: list,
    headings: dict,
    body_text: str,
    schema_org: list,
    open_graph: dict
) -> str:
    h1s = ", ".join(headings.get("h1", [])) or "None"
    h2s = ", ".join(headings.get("h2", [])[:8]) or "None"
    kw = ", ".join(meta_keywords) if meta_keywords else "None"
    og_title = open_graph.get("og:title", "")
    og_desc = open_graph.get("og:description", "")

    return f"""Target URL: {url}
Title Tag: {title}
Meta Description: {meta_description}
Meta Keywords: {kw}
Open Graph Title: {og_title}
Open Graph Description: {og_desc}
Main Headings (H1): {h1s}
Sub Headings (H2): {h2s}

Website Extracted Content:
{body_text}

JSON Schema structure required:
{{
  "competitor_analysis": {{
    "brand_name": "...",
    "brand_overview": "...",
    "category": "...",
    "products_and_services": ["..."],
    "competitors": [
      {{
        "name": "...",
        "overview": "...",
        "strengths": ["..."],
        "weaknesses": ["..."],
        "market_gaps": ["..."],
        "source_url": "...",
        "is_verified": false
      }}
    ],
    "brand_competitive_advantages": ["..."],
    "market_positioning_opportunities": ["..."],
    "verified_information": ["..."],
    "ai_generated_suggestions": ["..."]
  }},
  "target_search_queries": {{
    "queries": [
      {{
        "query": "...",
        "relevant_platforms": ["Google", "LinkedIn"],
        "search_intent": "Commercial",
        "business_relevance": "...",
        "target_audience": "..."
      }}
    ]
  }},
  "seo_improvements": {{
    "keywords": {{
      "primary_keywords": ["..."],
      "secondary_keywords": ["..."],
      "long_tail_keywords": ["..."],
      "business_keywords": ["..."]
    }},
    "recommended_title": "...",
    "recommended_meta_description": "...",
    "supporting_content_suggestions": {{
      "service_landing_pages": ["..."],
      "industry_pages": ["..."],
      "faqs": ["..."],
      "blogs": ["..."],
      "location_pages": ["..."]
    }},
    "technical_and_onpage_notes": ["..."]
  }},
  "top_services": {{
    "services": [
      {{
        "service_name": "...",
        "description": "...",
        "target_industry": "...",
        "target_customer": "...",
        "main_benefit": "...",
        "is_explicitly_stated": true,
        "evidence_or_source": "..."
      }}
    ]
  }},
  "target_audience": {{
    "primary_audience": "...",
    "secondary_audience": "...",
    "industry_segments": ["..."],
    "business_types": ["..."],
    "customer_profiles": ["..."],
    "geographic_focus": "...",
    "customer_needs": ["..."],
    "customer_challenges": ["..."],
    "customer_interests": ["..."],
    "recommended_marketing_segments": ["..."],
    "extracted_facts": ["..."],
    "ai_inferences": ["..."]
  }}
}}
"""
